"""Tests for SmartRouter plugin — 覆盖 select_model 与路由决策"""

import pytest
from unittest.mock import patch, AsyncMock

from smart_router.router.plugin import SmartRouter
from smart_router.config.schema import (
    Config,
    ProviderConfig,
    ModelConfig,
    ModelCapabilities,
    RoutingConfig,
    TaskConfig,
    DifficultyConfig,
    StrategyConfig,
    FallbackConfig,
)


@pytest.fixture
def sample_config():
    """创建用于测试 SmartRouter 的 Config"""
    return Config(
        providers={
            "openai": ProviderConfig(
                api_base="https://api.openai.com/v1",
                api_key="sk-test"
            )
        },
        models={
            "gpt-4o": ModelConfig(
                provider="openai",
                litellm_model="openai/gpt-4o",
                capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                supported_tasks=["chat", "coding"],
                difficulty_support=["easy", "medium", "hard"]
            ),
            "gpt-4o-mini": ModelConfig(
                provider="openai",
                litellm_model="openai/gpt-4o-mini",
                capabilities=ModelCapabilities(quality=6, cost=9, context=128000),
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
                "coding": TaskConfig(
                    name="Coding",
                    description="Code generation",
                    capability_weights={"quality": 0.7, "cost": 0.3}
                ),
            },
            difficulties={
                "easy": DifficultyConfig(description="Easy", max_tokens=2000),
                "medium": DifficultyConfig(description="Medium", max_tokens=8000),
            },
            strategies={
                "auto": StrategyConfig(description="Auto"),
                "quality": StrategyConfig(description="Quality priority"),
                "cost": StrategyConfig(description="Cost priority"),
            },
            fallback=FallbackConfig()
        )
    )


@pytest.fixture
def smart_router(sample_config):
    """创建 Mock 了 Router.__init__ 的 SmartRouter"""
    with patch('smart_router.router.plugin.Router.__init__', return_value=None):
        router = SmartRouter(config=sample_config)
    return router


class TestSmartRouterSelectModel:
    """测试 select_model 统一路由决策"""

    def test_select_model_auto_returns_valid_model(self, smart_router, sample_config):
        """select_model 对 auto 请求应返回配置中存在的模型"""
        messages = [{"role": "user", "content": "Hello"}]
        result = smart_router.select_model("auto", messages)

        assert result.model_name in sample_config.models
        assert result.score > 0

    def test_select_model_with_stage_prefix(self, smart_router):
        """model_hint 为 stage:xxx 时应直接使用对应 task_type"""
        messages = [{"role": "user", "content": "Hello"}]
        result = smart_router.select_model("stage:coding", messages)

        assert result.task_type == "coding"

    def test_select_model_with_strategy_prefix(self, smart_router, sample_config):
        """model_hint 为 strategy-xxx 时应使用对应策略"""
        messages = [{"role": "user", "content": "Hello"}]
        # strategy-quality 应选中 quality 最高的 gpt-4o
        result = smart_router.select_model("strategy-quality", messages)

        assert result.model_name == "gpt-4o"  # quality=9 > quality=6

    def test_select_model_with_cost_strategy(self, smart_router, sample_config):
        """strategy-cost 应选中 cost 最高（最便宜）的模型"""
        messages = [{"role": "user", "content": "Hello"}]
        result = smart_router.select_model("strategy-cost", messages)

        assert result.model_name == "gpt-4o-mini"  # cost=9 > cost=3

    def test_select_model_with_difficulty_marker(self, smart_router):
        """messages 中包含 difficulty marker 时应被解析"""
        messages = [{"role": "user", "content": "[difficulty:hard] 复杂问题"}]
        result = smart_router.select_model("auto", messages)

        assert result.difficulty == "hard"

    def test_select_model_with_stage_marker(self, smart_router):
        """messages 中包含 stage marker 时应被解析"""
        messages = [{"role": "user", "content": "[stage:coding] 写代码"}]
        result = smart_router.select_model("auto", messages)

        assert result.task_type == "coding"

    def test_select_model_saves_last_selected(self, smart_router):
        """select_model 应更新 last_selected_model"""
        messages = [{"role": "user", "content": "Hello"}]
        result = smart_router.select_model("auto", messages)

        assert smart_router.last_selected_model == result.model_name


    def test_select_model_context_uses_difficulty_based_tokens_not_fixed_4000(self, smart_router):
        """select_model 的 required_context 应使用难度分级 max_tokens，而非固定 +4000"""
        from smart_router.selector.v3_selector import SelectionResult

        messages = [{"role": "user", "content": "[difficulty:easy] simple"}]
        fixed_input_tokens = 500

        with patch('smart_router.router.plugin.estimate_messages_tokens', return_value=fixed_input_tokens):
            with patch.object(smart_router.selector, 'select') as mock_select:
                mock_select.return_value = SelectionResult(
                    model_name='gpt-4o', task_type='chat', difficulty='easy',
                    strategy='auto', score=0.9, reason='test'
                )
                smart_router.select_model("auto", messages)
                required_context = mock_select.call_args.kwargs['required_context']

        # easy max_tokens = 2000 (from sample_config)
        # 期望: 500 + 2000 = 2500
        # 旧代码 (固定 +4000): 500 + 4000 = 4500 ← BUG
        assert required_context == 2500, (
            f"expected required_context=2500 (input=500 + easy_max_tokens=2000), "
            f"got {required_context} (current code may be using fixed +4000)"
        )

    def test_select_model_different_difficulties_produce_different_context(self, smart_router):
        """不同难度应产生不同的 required_context"""
        from smart_router.selector.v3_selector import SelectionResult

        fixed_input = 100

        def get_context_for_difficulty(difficulty_marker):
            messages = [{"role": "user", "content": f"[difficulty:{difficulty_marker}] test"}]
            with patch('smart_router.router.plugin.estimate_messages_tokens', return_value=fixed_input):
                with patch.object(smart_router.selector, 'select') as mock_select:
                    mock_select.return_value = SelectionResult(
                        model_name='gpt-4o', task_type='chat', difficulty=difficulty_marker,
                        strategy='auto', score=0.9, reason='test'
                    )
                    smart_router.select_model("auto", messages)
                    return mock_select.call_args.kwargs['required_context']

        easy_ctx = get_context_for_difficulty("easy")
        medium_ctx = get_context_for_difficulty("medium")

        # easy max_tokens=2000, medium=8000，不同难度应有不同上下文需求
        assert easy_ctx != medium_ctx, (
            f"不同难度应产生不同的 required_context: easy={easy_ctx}, medium={medium_ctx}"
        )
        assert easy_ctx == 2100, f"expected easy=2100, got {easy_ctx}"  # 100 + 2000
        assert medium_ctx == 8100, f"expected medium=8100, got {medium_ctx}"  # 100 + 8000


class TestSmartRouterFallbacks:
    """测试 LiteLLM fallback 配置注入"""

    def test_fallbacks_passed_to_litellm_router(self):
        """SmartRouter 应将 Config 的 fallback 链转为 LiteLLM fallbacks 格式并传入 Router"""
        from smart_router.config.schema import FallbackConfig
        
        config = Config(
            providers={
                "openai": ProviderConfig(
                    api_base="https://api.openai.com/v1",
                    api_key="sk-test"
                )
            },
            models={
                "model-a": ModelConfig(
                    provider="openai",
                    litellm_model="openai/model-a",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
                "model-b": ModelConfig(
                    provider="openai",
                    litellm_model="openai/model-b",
                    capabilities=ModelCapabilities(quality=8, cost=5, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
            },
            routing=RoutingConfig(
                tasks={},
                difficulties={},
                strategies={},
                fallback=FallbackConfig(similarity_threshold=2)
            )
        )
        
        with patch('smart_router.router.plugin.Router.__init__', return_value=None) as mock_super:
            SmartRouter(config=config)
            
            call_kwargs = mock_super.call_args.kwargs
            assert "fallbacks" in call_kwargs, "fallbacks 参数应传入 Router.__init__"
            
            fallbacks = call_kwargs["fallbacks"]
            assert isinstance(fallbacks, list), "fallbacks 应为列表"
            assert len(fallbacks) > 0, "fallbacks 不应为空（存在 quality 差异 <=2 的模型）"
            
            # 验证格式: [{"model-a": ["model-b"]}]
            model_a_entry = next((f for f in fallbacks if "model-a" in f), None)
            assert model_a_entry is not None, "model-a 的 fallback 条目应存在"
            assert "model-b" in model_a_entry["model-a"], "model-a 的 fallback 链应包含 model-b"


class TestSmartRouterGracefulFallback:
    """测试无匹配模型时的优雅降级"""

    def test_select_model_fallback_when_no_match(self):
        """当没有模型支持请求的任务/难度时，应 fallback 到第一个可用模型"""
        config = Config(
            providers={
                "openai": ProviderConfig(
                    api_base="https://api.openai.com/v1",
                    api_key="sk-test"
                )
            },
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(
                        name="Chat",
                        description="Chat",
                        capability_weights={"quality": 0.5, "cost": 0.5}
                    ),
                },
                difficulties={
                    "easy": DifficultyConfig(description="Easy", max_tokens=1000),
                },
                strategies={
                    "auto": StrategyConfig(description="Auto"),
                },
                fallback=FallbackConfig()
            )
        )

        with patch('smart_router.router.plugin.Router.__init__', return_value=None):
            router = SmartRouter(config=config)

        # 请求一个完全不存在的任务类型（没有任何模型支持）
        messages = [{"role": "user", "content": "test"}]
        result = router.select_model("stage:unknown_task", messages)

        # 应该 graceful fallback，而不是抛出异常
        assert result.model_name == "gpt-4o"
        assert result.strategy == "fallback"
        assert "fallback" in result.reason.lower()

    def test_select_model_raises_when_no_models_available(self):
        """当完全没有可用模型时，应抛出 NoModelAvailableError"""
        config = Config(
            providers={
                "openai": ProviderConfig(
                    api_base="https://api.openai.com/v1",
                    api_key="sk-test"
                )
            },
            models={},
            routing=RoutingConfig(
                tasks={},
                difficulties={},
                strategies={},
                fallback=FallbackConfig()
            )
        )

        with patch('smart_router.router.plugin.Router.__init__', return_value=None):
            router = SmartRouter(config=config)

        from smart_router.selector.v3_selector import NoModelAvailableError
        with pytest.raises(NoModelAvailableError):
            router.select_model("auto", messages=[{"role": "user", "content": "test"}])


class TestSmartRouterReloadConfig:
    """测试 reload_config 运行时配置更新"""

    def test_reload_config_updates_selector(self):
        """reload_config 应更新 selector 以反映新配置"""
        from smart_router.config.schema import ProviderConfig, ModelConfig, ModelCapabilities
        from smart_router.config.schema import RoutingConfig, TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig

        config1 = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
            },
            routing=RoutingConfig(
                tasks={"chat": TaskConfig(name="Chat", description="Chat", capability_weights={"quality": 0.5, "cost": 0.5})},
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=1000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                fallback=FallbackConfig()
            )
        )

        with patch('smart_router.router.plugin.Router.__init__', return_value=None):
            router = SmartRouter(config=config1)

        # 初始配置下 gpt-4o 可用
        assert router.selector.config.models["gpt-4o"].capabilities.quality == 9

        # 新配置：更新模型能力评分
        config2 = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=5, cost=5, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                ),
            },
            routing=RoutingConfig(
                tasks={"chat": TaskConfig(name="Chat", description="Chat", capability_weights={"quality": 0.5, "cost": 0.5})},
                difficulties={"easy": DifficultyConfig(description="Easy", max_tokens=1000)},
                strategies={"auto": StrategyConfig(description="Auto")},
                fallback=FallbackConfig()
            )
        )

        router.reload_config(config2)

        # 验证 selector 已更新
        assert router.selector.config.models["gpt-4o"].capabilities.quality == 5
        assert router.sr_config is config2


class TestSmartRouterGetAvailableDeployment:
    """测试 get_available_deployment 委托给 select_model"""

    @pytest.mark.asyncio
    async def test_get_available_deployment_for_auto_delegates_to_select_model(self, smart_router):
        """model=auto 时应调用 select_model 并传入 super"""
        from smart_router.selector.v3_selector import SelectionResult
        
        with patch.object(smart_router, 'select_model') as mock_select:
            mock_select.return_value = SelectionResult(
                model_name='gpt-4o', task_type='chat', difficulty='medium',
                strategy='auto', score=0.9, reason='test'
            )
            
            with patch('smart_router.router.plugin.Router.get_available_deployment', new_callable=AsyncMock) as mock_super:
                mock_super.return_value = {"model": "gpt-4o"}
                await smart_router.get_available_deployment("auto", messages=[{"role": "user", "content": "hi"}])
                
                mock_select.assert_called_once()
                mock_super.assert_called_once()
                # 验证 super 被调用时传入选中的模型名
                call_kwargs = mock_super.call_args.kwargs
                assert call_kwargs.get('model') == 'gpt-4o'
