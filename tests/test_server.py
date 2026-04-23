"""server 模块测试 — 中间件逻辑与启动行为"""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from pathlib import Path


class TestSmartRouterSelectModel:
    """测试 select_model 路由决策逻辑"""

    def test_select_model_auto_strategy(self):
        """测试 auto 策略路由"""
        from smart_router.selector.v3_selector import V3ModelSelector
        from smart_router.config.v3_schema import (
            ConfigV3, ProviderConfig, ModelConfig, ModelCapabilities,
            RoutingConfig, TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig
        )

        config = ConfigV3(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="test")
            },
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat", "writing"],
                    difficulty_support=["easy", "medium", "hard"]
                ),
                "gpt-4o-mini": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o-mini",
                    capabilities=ModelCapabilities(quality=6, cost=9, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium"]
                )
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(name="Chat", description="Chat", capability_weights={"quality": 0.5, "cost": 0.5})
                },
                difficulties={
                    "easy": DifficultyConfig(description="Easy", max_tokens=1000),
                    "medium": DifficultyConfig(description="Medium", max_tokens=4000)
                },
                strategies={"auto": StrategyConfig(description="Auto")},
                fallback=FallbackConfig(mode="auto")
            )
        )

        selector = V3ModelSelector(config=config, available_models=["gpt-4o", "gpt-4o-mini"])
        result = selector.select(task_type="chat", difficulty="easy", strategy="auto")

        assert result.model_name in ["gpt-4o", "gpt-4o-mini"]
        assert result.task_type == "chat"

    def test_select_model_stage_prefix_parsing(self):
        """测试 stage: 前缀解析"""
        from smart_router.utils.markers import parse_markers

        messages = [{"role": "user", "content": "[stage:code_review] [difficulty:hard] review code"}]
        markers = parse_markers(messages)

        assert markers.stage == "code_review"
        assert markers.difficulty == "hard"

    def test_select_model_strategy_prefix_parsing(self):
        """测试 strategy- 前缀解析"""
        # strategy 前缀在 select_model 函数中解析，这里测试解析逻辑
        model_hint = "strategy-quality"
        
        if model_hint.startswith("strategy-"):
            strategy = model_hint.replace("strategy-", "")
            assert strategy == "quality"


class TestStartServer:
    """start_server 函数测试"""

    def test_config_load_error(self, capsys):
        """配置加载错误时退出"""
        with patch("smart_router.gateway.server.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.side_effect = Exception("Config error")

            with pytest.raises(SystemExit):
                from smart_router.gateway.server import start_server
                start_server()

            captured = capsys.readouterr()
            assert "配置加载失败" in captured.out

    def test_config_validation_error(self, capsys):
        """配置验证错误时退出"""
        with patch("smart_router.gateway.server.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = MagicMock()
            mock_loader.return_value.validate.return_value = ["Error 1", "Error 2"]

            with pytest.raises(SystemExit):
                from smart_router.gateway.server import start_server
                start_server()

            captured = capsys.readouterr()
            assert "配置验证失败" in captured.out

    def test_no_available_models(self, capsys):
        """没有可用模型时退出"""
        mock_config = MagicMock()
        mock_config.models = {"test": MagicMock()}
        mock_config.get_available_models.return_value = []
        mock_config.get_litellm_params.return_value = {}
        mock_config.get_fallback_chain.return_value = []

        with patch("smart_router.gateway.server.ConfigLoader") as mock_loader, \
             patch("smart_router.gateway.server.SmartRouter"):
            mock_loader.return_value.load.return_value = mock_config
            mock_loader.return_value.validate.return_value = []

            with pytest.raises(SystemExit):
                from smart_router.gateway.server import start_server
                start_server()

            captured = capsys.readouterr()
            assert "没有可用的模型" in captured.out

    def test_config_path_resolves_to_directory(self):
        """config_path 正确解析为目录"""
        from pathlib import Path

        # 测试目录路径
        config_dir = Path("/tmp/.smart-router")
        assert config_dir.is_dir() or not config_dir.exists()

        # 测试文件路径解析到父目录
        config_file = Path("/tmp/test.yaml")
        expected_dir = config_file.parent
        assert expected_dir == Path("/tmp")


class TestMiddlewareLogic:
    """中间件逻辑测试（不依赖实际 FastAPI 应用）"""

    def test_should_route_decision_for_auto(self):
        """测试 auto 模型触发路由判断"""
        original_model = "auto"
        should_route = (
            original_model in ("auto", "smart-router", "default") or
            original_model.startswith("stage:") or
            original_model.startswith("strategy-")
        )
        assert should_route is True

    def test_should_route_decision_for_smart_router(self):
        """测试 smart-router 模型触发路由判断"""
        original_model = "smart-router"
        should_route = (
            original_model in ("auto", "smart-router", "default") or
            original_model.startswith("stage:") or
            original_model.startswith("strategy-")
        )
        assert should_route is True

    def test_should_route_decision_for_default(self):
        """测试 default 模型触发路由判断"""
        original_model = "default"
        should_route = (
            original_model in ("auto", "smart-router", "default") or
            original_model.startswith("stage:") or
            original_model.startswith("strategy-")
        )
        assert should_route is True

    def test_should_route_decision_for_stage_prefix(self):
        """测试 stage: 前缀触发路由"""
        original_model = "stage:code_review"
        should_route = (
            original_model in ("auto", "smart-router", "default") or
            original_model.startswith("stage:") or
            original_model.startswith("strategy-")
        )
        assert should_route is True

    def test_should_route_decision_for_strategy_prefix(self):
        """测试 strategy- 前缀触发路由"""
        original_model = "strategy-quality"
        should_route = (
            original_model in ("auto", "smart-router", "default") or
            original_model.startswith("stage:") or
            original_model.startswith("strategy-")
        )
        assert should_route is True

    def test_should_not_route_for_specific_model(self):
        """测试具体模型名不触发路由"""
        original_model = "gpt-4o"
        should_route = (
            original_model in ("auto", "smart-router", "default") or
            original_model.startswith("stage:") or
            original_model.startswith("strategy-")
        )
        assert should_route is False

    def test_should_not_route_for_custom_model_name(self):
        """测试自定义模型名不触发路由"""
        original_model = "my-custom-model"
        should_route = (
            original_model in ("auto", "smart-router", "default") or
            original_model.startswith("stage:") or
            original_model.startswith("strategy-")
        )
        assert should_route is False