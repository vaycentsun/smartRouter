"""Tests for V3 Model Selector - Refactored for FormulaEvaluator"""

import pytest
import warnings
from smart_router.selector.v3_selector import V3ModelSelector, NoModelAvailableError
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
    FormulaConfig,
)


class TestV3ModelSelector:
    """Test V3 Model Selector with FormulaEvaluator"""
    
    @pytest.fixture
    def sample_config(self):
        """创建测试配置 - 包含 formula 字段"""
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
                    "cost": StrategyConfig(description="Cost"),
                },
                formula=FormulaConfig(weights={"quality": 0.5, "cost": 0.5}),
                fallback=FallbackConfig(mode="auto", similarity_threshold=2)
            )
        )
    
    def test_select_uses_formula_evaluator(self, sample_config):
        """select() 应使用 FormulaEvaluator 基于全局 formula 权重计算得分"""
        selector = V3ModelSelector(sample_config)
        
        # formula weights: quality=0.5, cost=0.5
        # gpt-4o: 9*0.5 + 3*0.5 = 4.5 + 1.5 = 6.0
        # gpt-4o-mini: 6*0.5 + 9*0.5 = 3.0 + 4.5 = 7.5
        result = selector.select("chat", "easy", "auto")
        
        assert result.strategy == "auto"
        assert result.model_name == "gpt-4o-mini"  # 更高 formula 得分
        assert result.score == 7.5
        assert "Formula score" in result.reason
    
    def test_cost_strategy_emits_deprecation_warning(self, sample_config):
        """strategy='cost' 应发出 DeprecationWarning，但返回结果 strategy='auto'"""
        selector = V3ModelSelector(sample_config)
        
        with pytest.warns(DeprecationWarning, match="strategy='cost' is deprecated"):
            result = selector.select("chat", "easy", "cost")
        
        assert result.strategy == "auto"
        # 使用 formula 评分而非纯 cost
        assert result.model_name == "gpt-4o-mini"
        assert "Formula score" in result.reason

    def test_unknown_strategy_emits_deprecation_warning(self, sample_config):
        """未知策略应发出 DeprecationWarning，不再抛出异常，返回结果 strategy='auto'"""
        selector = V3ModelSelector(sample_config)
        
        with pytest.warns(DeprecationWarning, match="strategy='unknown_strategy' is deprecated"):
            result = selector.select("chat", "easy", "unknown_strategy")
        
        assert result.strategy == "auto"
        assert result.model_name == "gpt-4o-mini"

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

    def test_select_with_quality_heavy_formula(self):
        """quality 权重较高时应选择高质量模型"""
        config = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "model-a": ModelConfig(
                    provider="openai",
                    litellm_model="openai/a",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
                "model-b": ModelConfig(
                    provider="openai",
                    litellm_model="openai/b",
                    capabilities=ModelCapabilities(quality=6, cost=8, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                )
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(
                        name="Chat",
                        description="General chat",
                        capability_weights={"quality": 0.8, "cost": 0.2}
                    )
                },
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=2000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                formula=FormulaConfig(weights={"quality": 0.8, "cost": 0.2}),
                fallback=FallbackConfig()
            )
        )

        selector = V3ModelSelector(config)
        result = selector.select("chat", "easy", "auto")

        # model-a: 9*0.8 + 3*0.2 = 7.2 + 0.6 = 7.8
        # model-b: 6*0.8 + 8*0.2 = 4.8 + 1.6 = 6.4
        assert result.model_name == "model-a"
        assert result.score == pytest.approx(7.8)
        assert "Formula score" in result.reason

    def test_select_with_cost_heavy_formula(self):
        """cost 权重较高时应选择低成本模型"""
        config = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "model-a": ModelConfig(
                    provider="openai",
                    litellm_model="openai/a",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
                "model-b": ModelConfig(
                    provider="openai",
                    litellm_model="openai/b",
                    capabilities=ModelCapabilities(quality=6, cost=9, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                )
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(
                        name="Chat",
                        description="General chat",
                        capability_weights={"quality": 0.2, "cost": 0.8}
                    )
                },
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=2000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                formula=FormulaConfig(weights={"quality": 0.2, "cost": 0.8}),
                fallback=FallbackConfig()
            )
        )

        selector = V3ModelSelector(config)
        result = selector.select("chat", "easy", "auto")

        # model-a: 9*0.2 + 3*0.8 = 1.8 + 2.4 = 4.2
        # model-b: 6*0.2 + 9*0.8 = 1.2 + 7.2 = 8.4
        assert result.model_name == "model-b"
        assert result.score == 8.4
        assert "Formula score" in result.reason

    def test_formula_score_no_normalization(self):
        """formula 权重总和不等于 1 时不应归一化，直接返回原始加权和"""
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
                        capability_weights={"quality": 0.5, "cost": 0.5}
                    )
                },
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=2000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                formula=FormulaConfig(weights={"quality": 1.0, "cost": 1.0}),  # 总和 2.0
                fallback=FallbackConfig()
            )
        )
        
        selector = V3ModelSelector(config)
        result = selector.select("chat", "easy", "auto")
        
        # score = 8*1.0 + 5*1.0 = 13.0（不归一化）
        assert result.model_name == "model-a"
        assert result.score == 13.0
        assert "Formula score" in result.reason

    def test_select_unknown_task_uses_formula(self):
        """未知任务应使用全局 formula 权重计算"""
        config = Config(
            providers={"openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")},
            models={
                "model-a": ModelConfig(
                    provider="openai",
                    litellm_model="openai/a",
                    capabilities=ModelCapabilities(quality=8, cost=5, context=128000),
                    supported_tasks=["unknown_task"],
                    difficulty_support=["easy"]
                ),
            },
            routing=RoutingConfig(
                tasks={},
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=2000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                formula=FormulaConfig(weights={"quality": 0.5, "cost": 0.5}),
                fallback=FallbackConfig()
            )
        )
        selector = V3ModelSelector(config)
        result = selector.select("unknown_task", "easy", "auto")
        # 全局 formula: quality=0.5, cost=0.5
        # model-a: 8*0.5 + 5*0.5 = 6.5
        assert result.model_name == "model-a"
        assert result.score == 6.5
        assert "Formula score" in result.reason

    def test_filter_candidates_requires_vision(self):
        """测试 _filter_candidates 正确过滤 vision 模型"""
        # 创建包含 vision 模型的配置
        config = Config(
            providers={"openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")},
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium"]
                ),
                "gpt-4o-vision": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000, vision=True),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium"]
                ),
            },
            routing=RoutingConfig(
                tasks={"chat": TaskConfig(name="Chat", description="Chat", capability_weights={"quality": 0.5, "cost": 0.5})},
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=1000), "medium": DifficultyConfig(description="Medium", max_tokens=2000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                formula=FormulaConfig(weights={"quality": 1.0, "cost": 0.0}),
                fallback=FallbackConfig()
            )
        )
        
        selector = V3ModelSelector(config)
        
        # 不需要 vision 时，两个模型都应该出现
        candidates = selector._filter_candidates("chat", "medium", requires_vision=False)
        model_names = [name for name, _ in candidates]
        assert "gpt-4o" in model_names
        assert "gpt-4o-vision" in model_names
        
        # 需要 vision 时，只有 vision=True 的模型应该出现
        candidates = selector._filter_candidates("chat", "medium", requires_vision=True)
        model_names = [name for name, _ in candidates]
        assert "gpt-4o" not in model_names
        assert "gpt-4o-vision" in model_names

    def test_select_passes_requires_vision(self):
        """测试 select 方法正确传递 requires_vision 参数"""
        # 创建包含 vision 模型的配置
        config = Config(
            providers={"openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")},
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium"]
                ),
                "gpt-4o-vision": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000, vision=True),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium"]
                ),
            },
            routing=RoutingConfig(
                tasks={"chat": TaskConfig(name="Chat", description="Chat", capability_weights={"quality": 0.5, "cost": 0.5})},
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=1000), "medium": DifficultyConfig(description="Medium", max_tokens=2000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                formula=FormulaConfig(weights={"quality": 1.0, "cost": 0.0}),
                fallback=FallbackConfig()
            )
        )
        
        selector = V3ModelSelector(config)
        
        # 需要 vision 时，应该选中 vision 模型
        result = selector.select("chat", "medium", requires_vision=True)
        assert result.model_name == "gpt-4o-vision"
        
        # 不需要 vision 时，可能选中任一模型（根据评分）
        result = selector.select("chat", "medium", requires_vision=False)
        assert result.model_name in ["gpt-4o", "gpt-4o-vision"]

    def test_select_ranked_filters_and_sorts(self, sample_config):
        """select_ranked 应返回按公式得分降序排列的完整候选列表"""
        selector = V3ModelSelector(sample_config)
        
        ranked = selector.select_ranked("chat", "easy")
        
        # 应包含所有支持 chat/easy 的模型
        model_names = [name for name, _ in ranked]
        assert "gpt-4o" in model_names
        assert "gpt-4o-mini" in model_names
        assert "cheap-bad-model" in model_names
        
        # 按 formula 得分降序排列
        # formula weights: quality=0.5, cost=0.5
        # gpt-4o: 9*0.5 + 3*0.5 = 6.0
        # gpt-4o-mini: 6*0.5 + 9*0.5 = 7.5
        # cheap-bad-model: 2*0.5 + 10*0.5 = 6.0
        scores = {name: score for name, score in ranked}
        assert scores["gpt-4o-mini"] == 7.5
        assert scores["gpt-4o"] == 6.0
        assert scores["cheap-bad-model"] == 6.0
        
        # 验证降序
        for i in range(len(ranked) - 1):
            assert ranked[i][1] >= ranked[i + 1][1]
    
    def test_select_ranked_empty_candidates(self, sample_config):
        """没有候选模型时应返回空列表"""
        selector = V3ModelSelector(sample_config)
        
        ranked = selector.select_ranked("unknown_task", "easy")
        assert ranked == []
    
    def test_select_ranked_respects_filters(self, sample_config):
        """select_ranked 应正确应用 difficulty 和 context 过滤"""
        selector = V3ModelSelector(sample_config)
        
        # hard 难度只支持 gpt-4o
        ranked = selector.select_ranked("chat", "hard")
        model_names = [name for name, _ in ranked]
        assert model_names == ["gpt-4o"]
        
        # 需要 vision 时过滤非 vision 模型
        ranked = selector.select_ranked("chat", "easy", requires_vision=True)
        model_names = [name for name, _ in ranked]
        # sample_config 中没有 vision=True 的模型
        assert model_names == []
