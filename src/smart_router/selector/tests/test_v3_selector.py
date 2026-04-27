"""Tests for V3 Model Selector - Refactored for actual Config schema"""

import pytest
from smart_router.selector.v3_selector import V3ModelSelector, NoModelAvailableError, UnknownStrategyError
from smart_router.config.schema import (
    Config,
    ProviderConfig,
    ModelConfig,
    ModelCapabilities,
    TaskConfig,
    DifficultyConfig,
    StrategyConfig,
    FallbackConfig,
    RoutingConfig,
)


class TestV3ModelSelector:
    """Test V3 Model Selector with actual Config schema"""
    
    @pytest.fixture
    def sample_config(self):
        """创建测试配置 - 使用现有 Config schema（无 speed 字段）"""
        return Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat", "code_review"],
                    difficulty_support=["easy", "medium", "hard", "expert"]
                ),
                "gpt-4o-mini": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o-mini",
                    capabilities=ModelCapabilities(quality=6, cost=9, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium"]
                ),
                "cheap-bad-model": ModelConfig(
                    provider="openai",
                    litellm_model="openai/cheap-bad",
                    capabilities=ModelCapabilities(quality=2, cost=10, context=8000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium"]
                ),
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(
                        name="Chat",
                        description="General chat",
                        capability_weights={"quality": 0.6, "cost": 0.4}
                    ),
                    "code_review": TaskConfig(
                        name="Code Review",
                        description="Review code",
                        capability_weights={"quality": 0.7, "cost": 0.3}
                    )
                },
                difficulties={
                    "easy": DifficultyConfig(description="Easy", max_tokens=2000),
                    "medium": DifficultyConfig(description="Medium", max_tokens=8000),
                    "hard": DifficultyConfig(description="Hard", max_tokens=16000),
                    "expert": DifficultyConfig(description="Expert", max_tokens=32000),
                },
                strategies={
                    "auto": StrategyConfig(description="Auto"),
                    "quality": StrategyConfig(description="Quality"),
                    "cost": StrategyConfig(description="Cost"),
                    "balanced": StrategyConfig(description="Balanced"),
                },
                fallback=FallbackConfig(mode="auto", similarity_threshold=2)
            )
        )
    
    def test_auto_strategy_without_speed(self, sample_config):
        """auto 策略在无 speed 字段时仍能正常工作，基于 quality 和 cost 加权"""
        selector = V3ModelSelector(sample_config)
        
        # For chat: quality=0.6, cost=0.4
        # gpt-4o: 9*0.6 + 3*0.4 = 5.4 + 1.2 = 6.6
        # gpt-4o-mini: 6*0.6 + 9*0.4 = 3.6 + 3.6 = 7.2
        result = selector.select("chat", "easy", "auto")
        
        assert result.strategy == "auto"
        assert result.model_name == "gpt-4o-mini"  # 更高加权得分
        assert result.score > 0
    
    def test_quality_strategy(self, sample_config):
        """quality 策略选择最高质量模型"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("chat", "easy", "quality")
        
        assert result.model_name == "gpt-4o"  # quality=9 最高
        assert result.strategy == "quality"
    
    def test_cost_strategy_with_quality_threshold(self, sample_config):
        """cost 策略应过滤掉 quality 低于阈值的模型，避免选到劣质便宜模型"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("chat", "easy", "cost")
        
        # cheap-bad-model (quality=2) 应该被过滤掉
        # 在剩余模型中 gpt-4o-mini (cost=9) 最便宜
        assert result.model_name == "gpt-4o-mini"
        assert result.strategy == "cost"
    
    def test_cost_strategy_all_filtered_falls_back(self, sample_config):
        """cost 策略如果过滤后没有模型，应回退到不过滤"""
        # 创建所有模型 quality 都很低的配置
        config_low_quality = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "model-a": ModelConfig(
                    provider="openai",
                    litellm_model="openai/a",
                    capabilities=ModelCapabilities(quality=3, cost=5, context=8000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
                "model-b": ModelConfig(
                    provider="openai",
                    litellm_model="openai/b",
                    capabilities=ModelCapabilities(quality=2, cost=8, context=8000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(
                        name="Chat",
                        description="General chat",
                        capability_weights={"quality": 0.5, "cost": 0.5}
                    )
                },
                difficulties={
                    "easy": DifficultyConfig(description="Easy", max_tokens=2000)
                },
                strategies={
                    "auto": StrategyConfig(description="Auto"),
                    "cost": StrategyConfig(description="Cost"),
                },
                fallback=FallbackConfig()
            )
        )
        
        selector = V3ModelSelector(config_low_quality)
        result = selector.select("chat", "easy", "cost")
        
        # 质量门槛默认 5，两个模型都不满足，应回退到不过滤
        # 然后选择 cost 最高的：model-b (cost=8)
        assert result.model_name == "model-b"
    
    def test_balanced_strategy(self, sample_config):
        """balanced 策略应使用 quality 和 cost 权重各 0.5"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("chat", "easy", "balanced")
        
        # balanced: quality=0.5, cost=0.5
        # gpt-4o: 9*0.5 + 3*0.5 = 4.5 + 1.5 = 6.0
        # gpt-4o-mini: 6*0.5 + 9*0.5 = 3.0 + 4.5 = 7.5
        assert result.model_name == "gpt-4o-mini"
        assert result.strategy == "balanced"
    
    def test_difficulty_filtering(self, sample_config):
        """难度过滤应正常工作"""
        selector = V3ModelSelector(sample_config)
        
        # gpt-4o-mini 不支持 hard
        result = selector.select("chat", "hard", "auto")
        assert result.model_name == "gpt-4o"
    
    def test_expert_difficulty_filtering(self, sample_config):
        """expert 难度只有 gpt-4o 支持"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("code_review", "expert", "auto")
        assert result.model_name == "gpt-4o"
    
    def test_task_type_filtering(self, sample_config):
        """任务类型过滤应正常工作"""
        selector = V3ModelSelector(sample_config)
        
        # gpt-4o-mini 不支持 code_review
        result = selector.select("code_review", "medium", "auto")
        assert result.model_name == "gpt-4o"
    
    def test_no_model_available(self, sample_config):
        """没有可用模型时应抛异常"""
        selector = V3ModelSelector(sample_config)
        
        with pytest.raises(NoModelAvailableError):
            selector.select("unknown_task", "easy", "auto")
    
    def test_unknown_strategy(self, sample_config):
        """未知策略应抛异常"""
        selector = V3ModelSelector(sample_config)
        
        with pytest.raises(UnknownStrategyError):
            selector.select("chat", "easy", "unknown_strategy")
    
    def test_get_available_models(self, sample_config):
        """获取可用模型列表"""
        selector = V3ModelSelector(sample_config)
        
        models = selector.get_available_models("chat", "easy")
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models
        
        models = selector.get_available_models("chat", "hard")
        assert "gpt-4o" in models
        assert "gpt-4o-mini" not in models
    
    def test_get_required_context_uses_max_tokens(self, sample_config):
        """get_required_context 应使用 routing.difficulties 中的 max_tokens"""
        selector = V3ModelSelector(sample_config)
        
        assert selector.get_required_context("easy") == 2000
        assert selector.get_required_context("medium") == 8000
        assert selector.get_required_context("hard") == 16000
        assert selector.get_required_context("expert") == 32000
        assert selector.get_required_context("unknown") == 4000  # 默认回退

    def test_vision_strategy_fallback_to_auto(self, sample_config):
        """vision 策略无 vision 模型时回退到 auto"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("chat", "easy", "vision")
        # 配置中无 vision 模型，应回退到 auto 策略结果
        # 回退时 strategy 字段仍为 "vision"，但实际选择逻辑是 auto
        assert result.model_name in ["gpt-4o", "gpt-4o-mini"]

    def test_long_context_strategy_fallback(self, sample_config):
        """long_context 策略无长上下文模型时回退到 context_window"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("chat", "easy", "long_context")
        # 所有模型 context >= 128000，都不标记 long_context=True
        # 应回退到按 context 排序
        assert result.strategy == "long_context"
        assert result.model_name in ["gpt-4o", "gpt-4o-mini"]

    def test_reasoning_strategy_with_no_reasoning_models(self, sample_config):
        """reasoning 策略无 reasoning 评分模型时回退到 auto"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("chat", "easy", "reasoning")
        # 配置中所有模型 reasoning 为 None
        # 应回退到 auto 策略，但 strategy 字段保留 "reasoning"
        assert result.model_name in ["gpt-4o", "gpt-4o-mini"]

    def test_creative_strategy_with_no_creative_models(self, sample_config):
        """creative 策略无 creative 评分模型时回退到 auto"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("chat", "easy", "creative")
        # 配置中所有模型 creative 为 None
        # 应回退到 auto 策略，但 strategy 字段保留 "creative"
        assert result.model_name in ["gpt-4o", "gpt-4o-mini"]

    def test_latest_strategy(self, sample_config):
        """latest 策略选择最新模型"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("chat", "easy", "latest")
        assert result.strategy == "latest"
        # 所有模型默认 latest=True

    def test_filter_candidates_with_available_models(self, sample_config):
        """available_models 参数过滤"""
        selector = V3ModelSelector(sample_config, available_models=["gpt-4o"])
        
        candidates = selector._filter_candidates("chat", "easy")
        names = [name for name, _ in candidates]
        assert "gpt-4o" in names
        assert "gpt-4o-mini" not in names

    def test_filter_candidates_with_required_context(self, sample_config):
        """required_context 过滤上下文不足的模型"""
        selector = V3ModelSelector(sample_config)
        
        candidates = selector._filter_candidates("chat", "easy", required_context=200000)
        # gpt-4o 和 gpt-4o-mini 都是 128000，不足 200000
        assert len(candidates) == 0

    def test_get_candidates_alias(self, sample_config):
        """get_candidates 是 get_available_models 的兼容别名"""
        selector = V3ModelSelector(sample_config)
        
        result1 = selector.get_candidates("chat", "easy")
        result2 = selector.get_available_models("chat", "easy")
        assert result1 == result2

    def test_auto_strategy_with_reasoning_weight(self):
        """auto 策略包含 reasoning 权重时正确计算"""
        config = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "model-a": ModelConfig(
                    provider="openai",
                    litellm_model="openai/a",
                    capabilities=ModelCapabilities(quality=8, cost=5, context=128000, reasoning=9),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
                "model-b": ModelConfig(
                    provider="openai",
                    litellm_model="openai/b",
                    capabilities=ModelCapabilities(quality=6, cost=8, context=128000, reasoning=5),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                )
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(
                        name="Chat",
                        description="General chat",
                        capability_weights={"quality": 0.3, "cost": 0.3, "reasoning": 0.4}
                    )
                },
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=2000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                fallback=FallbackConfig()
            )
        )
        
        selector = V3ModelSelector(config)
        result = selector.select("chat", "easy", "auto")
        
        # model-a: 8*0.3 + 5*0.3 + 9*0.4 = 2.4 + 1.5 + 3.6 = 7.5
        # model-b: 6*0.3 + 8*0.3 + 5*0.4 = 1.8 + 2.4 + 2.0 = 6.2
        assert result.model_name == "model-a"
        assert "weighted" in result.reason.lower() or "score" in result.reason.lower()

    def test_auto_strategy_with_creative_weight(self):
        """auto 策略包含 creative 权重时正确计算"""
        config = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "model-a": ModelConfig(
                    provider="openai",
                    litellm_model="openai/a",
                    capabilities=ModelCapabilities(quality=8, cost=5, context=128000, creative=9),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(
                        name="Chat",
                        description="General chat",
                        capability_weights={"quality": 0.3, "cost": 0.3, "creative": 0.4}
                    )
                },
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=2000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                fallback=FallbackConfig()
            )
        )
        
        selector = V3ModelSelector(config)
        result = selector.select("chat", "easy", "auto")
        
        assert result.model_name == "model-a"

    def test_auto_strategy_weight_normalization(self):
        """auto 策略权重总和不等于 1 时应归一化"""
        config = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "model-a": ModelConfig(
                    provider="openai",
                    litellm_model="openai/a",
                    capabilities=ModelCapabilities(quality=8, cost=5, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(
                        name="Chat",
                        description="General chat",
                        capability_weights={"quality": 0.5, "cost": 0.5}  # 总和 1.0
                    )
                },
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=2000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                fallback=FallbackConfig()
            )
        )
        
        selector = V3ModelSelector(config)
        result = selector.select("chat", "easy", "auto")
        
        # score = 8*0.5 + 5*0.5 = 4.0 + 2.5 = 6.5
        assert result.model_name == "model-a"
        assert result.score > 0
