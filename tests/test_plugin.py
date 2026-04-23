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
