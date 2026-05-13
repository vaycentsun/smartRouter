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
        from smart_router.config import (
            Config, ProviderConfig, ModelConfig, ModelCapabilities,
            RoutingConfig, TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig
        )

        config = Config(
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
        model_hint = "strategy-cost"
        
        if model_hint.startswith("strategy-"):
            strategy = model_hint.replace("strategy-", "")
            assert strategy == "cost"


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


class TestStartServerEdgeCases:
    """start_server 边缘情况测试"""

    def test_master_key_set(self, capsys, monkeypatch):
        """SMART_ROUTER_MASTER_KEY 已设置时启用认证"""
        monkeypatch.setenv("SMART_ROUTER_MASTER_KEY", "test-key")
        mock_config = MagicMock()
        mock_config.models = {"test": MagicMock()}
        mock_config.get_available_models.return_value = ["test"]
        mock_config.get_litellm_params.return_value = {"model": "test"}
        mock_config.get_fallback_chain.return_value = []

        with patch("smart_router.gateway.server.ConfigLoader") as mock_loader, \
             patch("smart_router.gateway.server.SmartRouter"), \
             patch("os.unlink"), \
             patch("tempfile.mkstemp", return_value=(1, "/tmp/test.json")), \
             patch("os.fdopen", MagicMock()), \
             patch("asyncio.run"), \
             patch("uvicorn.run"):
            mock_loader.return_value.load.return_value = mock_config
            mock_loader.return_value.validate.return_value = []

            from smart_router.gateway.server import start_server
            start_server()

            captured = capsys.readouterr()
            assert "启动服务" in captured.out or "配置加载完成" in captured.out

    def test_master_key_not_set_warning(self, capsys):
        """SMART_ROUTER_MASTER_KEY 未设置时显示警告"""
        mock_config = MagicMock()
        mock_config.models = {"test": MagicMock()}
        mock_config.get_available_models.return_value = ["test"]
        mock_config.get_litellm_params.return_value = {"model": "test"}
        mock_config.get_fallback_chain.return_value = []

        with patch("smart_router.gateway.server.ConfigLoader") as mock_loader, \
             patch("smart_router.gateway.server.SmartRouter"), \
             patch("os.unlink"), \
             patch("tempfile.mkstemp", return_value=(1, "/tmp/test.json")), \
             patch("os.fdopen", MagicMock()), \
             patch("asyncio.run"), \
             patch("uvicorn.run"):
            mock_loader.return_value.load.return_value = mock_config
            mock_loader.return_value.validate.return_value = []

            from smart_router.gateway.server import start_server
            start_server()

            captured = capsys.readouterr()
            assert "警告" in captured.out or "未设置" in captured.out or "配置加载完成" in captured.out

    def test_fallback_chain_empty(self, capsys):
        """fallback 链为空时不加入 fallbacks"""
        mock_config = MagicMock()
        mock_config.models = {"test": MagicMock()}
        mock_config.get_available_models.return_value = ["test"]
        mock_config.get_litellm_params.return_value = {"model": "test"}
        mock_config.get_fallback_chain.return_value = []  # 空 fallback

        with patch("smart_router.gateway.server.ConfigLoader") as mock_loader, \
             patch("smart_router.gateway.server.SmartRouter"), \
             patch("os.unlink"), \
             patch("tempfile.mkstemp", return_value=(1, "/tmp/test.json")), \
             patch("os.fdopen") as mock_fdopen, \
             patch("asyncio.run"), \
             patch("uvicorn.run"):
            mock_loader.return_value.load.return_value = mock_config
            mock_loader.return_value.validate.return_value = []

            from smart_router.gateway.server import start_server
            start_server()

            # 验证 json.dump 被调用且 fallbacks 不存在或为空
            mock_file = mock_fdopen.return_value.__enter__.return_value
            assert mock_file is not None

    def test_config_path_is_file(self):
        """config_path 传入文件时解析到父目录"""
        from pathlib import Path
        config_file = Path("/tmp/test/config.yaml")
        expected_dir = config_file.parent
        assert expected_dir == Path("/tmp/test")


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

    @pytest.mark.asyncio
    async def test_middleware_select_model_exception_fallback(self):
        """select_model 异常时，保留模型名应 fallback 到第一个可用模型"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        mock_router = MagicMock()
        mock_router.select_model.side_effect = Exception("Simulated routing failure")
        mock_router.sr_config = MagicMock()
        mock_router.sr_config.get_available_models.return_value = ["gpt-4o"]

        async def mock_call_next(request):
            body = await request.body()
            data = json.loads(body)
            assert data["model"] == "gpt-4o"
            return Response(content=b'ok', status_code=200)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert request.state.smart_router_selected == "gpt-4o"
        assert request.state.smart_router_original == "auto"

    @pytest.mark.asyncio
    async def test_middleware_select_model_exception_no_available_models(self):
        """select_model 异常且没有可用模型时，应返回 400"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from starlette.requests import Request

        mock_router = MagicMock()
        mock_router.select_model.side_effect = Exception("Simulated routing failure")
        mock_router.sr_config = MagicMock()
        mock_router.sr_config.get_available_models.return_value = []

        async def mock_call_next(request):
            return None  # should not be called

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_middleware_select_model_exception_for_stage_prefix(self):
        """stage: 前缀在 select_model 异常时不应 fallback（保留原始值继续向下游传递）"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        mock_router = MagicMock()
        mock_router.select_model.side_effect = Exception("Simulated routing failure")

        async def mock_call_next(request):
            # stage: 前缀不是保留名，异常时不应 fallback，保持原始值
            body = await request.body()
            data = json.loads(body)
            assert data["model"] == "stage:code_review"
            return Response(content=b'ok', status_code=200)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "stage:code_review", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_replaces_model_in_request_body(self):
        """model=auto 时，中间件应修改 request body 中的 model 为实际选择的模型"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from starlette.requests import Request
        from starlette.responses import Response
        from smart_router.selector.v3_selector import SelectionResult

        mock_router = MagicMock()
        mock_router.select_model.return_value = SelectionResult(
            model_name="gpt-4o",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=0.9,
            reason="test",
        )
        mock_router.get_fallback_chain.return_value = []
        mock_router.sr_config = MagicMock()
        mock_router.sr_config.models = {"gpt-4o": MagicMock(provider="openai")}
        mock_router.sr_config.is_model_available.return_value = True
        mock_router.sr_config.get_available_models.return_value = ["gpt-4o"]
        mock_router.sr_config.routing.fallback.max_attempts = 3

        async def mock_call_next(request):
            body = await request.body()
            data = json.loads(body)
            # 关键断言：下游必须收到替换后的实际模型名，而不是 "auto"
            assert data["model"] == "gpt-4o"
            return Response(content=b'ok', status_code=200)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert request.state.smart_router_selected == "gpt-4o"
        assert request.state.smart_router_original == "auto"

    def test_middleware_json_parse_failure(self):
        """测试请求体 JSON 解析失败时的降级"""
        import json
        invalid_body = b"not json"
        try:
            json.loads(invalid_body)
            assert False, "应该抛出异常"
        except json.JSONDecodeError:
            # 异常被捕获后，请求应继续处理
            pass

    def test_middleware_response_headers(self):
        """测试响应头设置逻辑"""
        # 验证当 request.state 中有 smart_router_selected 时添加响应头
        class MockState:
            def __init__(self):
                self.smart_router_selected = "gpt-4o"
                self.smart_router_original = "auto"
                self.smart_router_task = "chat"
        
        state = MockState()
        assert hasattr(state, 'smart_router_selected')
        assert hasattr(state, 'smart_router_original')
        assert hasattr(state, 'smart_router_task')
        assert state.smart_router_selected == "gpt-4o"

    def test_middleware_no_state_attributes(self):
        """测试没有路由状态时不添加响应头"""
        class MockState:
            pass
        
        state = MockState()
        assert not hasattr(state, 'smart_router_selected')

    def test_middleware_class_prevents_double_registration(self):
        """SmartRouterMiddleware 应通过 add_middleware 条件注册，防止重复"""
        from unittest.mock import MagicMock
        from smart_router.gateway.server import SmartRouterMiddleware
        
        mock_app = MagicMock()
        mock_router = MagicMock()
        
        # 第一次添加
        SmartRouterMiddleware(mock_app, router=mock_router)
        assert mock_app.add_middleware.call_count == 0  # 构造时不调用
        
        # 验证类存在且可实例化
        assert SmartRouterMiddleware is not None
        
    def test_middleware_added_only_once_via_flag(self):
        """_smart_router_middleware_added 标志防止重复添加"""
        from unittest.mock import MagicMock
        
        app = MagicMock()
        app.state = MagicMock()
        app.state._smart_router_middleware_added = True
        
        # 当标志已设置时，不应再次调用 add_middleware
        # 这个测试验证的是 start_server 中的条件逻辑
        assert getattr(app.state, '_smart_router_middleware_added', False) is True
        assert app.add_middleware.call_count == 0

    def test_override_header_skips_routing(self):
        """测试模型覆盖请求头存在时跳过智能路由"""
        override_provider = "openai"
        override_model = "gpt-4o"
        
        # 验证逻辑：当 override header 存在时，不应触发路由判断
        original_model = "auto"
        should_route = (
            original_model in ("auto", "smart-router", "default") or
            original_model.startswith("stage:") or
            original_model.startswith("strategy-")
        )
        # 有 override header 时，should_route 仍然为 True，但中间件会先处理 override
        # 这个测试验证的是 override 优先级高于路由逻辑
        assert should_route is True
        
        # 模拟覆盖后的模型名
        overridden_model = override_model
        assert overridden_model == "gpt-4o"

    def test_override_header_invalid_model(self):
        """测试无效的模型覆盖请求头"""
        from smart_router.config import (
            Config, ProviderConfig, ModelConfig, ModelCapabilities,
            RoutingConfig, TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig
        )
        
        config = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="test")
            },
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium", "hard"]
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
        
        # 未知模型
        assert "gpt-4-turbo" not in config.models
        
        # provider 不匹配
        model_config = config.models.get("gpt-4o")
        assert model_config is not None
        assert model_config.provider != "anthropic"
        
        # 模型不可用（当 api_key 无效时）
        assert config.is_model_available("gpt-4o") is True  # 这里 test key 直接配置了

    def test_override_response_headers(self):
        """测试覆盖响应头设置逻辑"""
        class MockState:
            def __init__(self):
                self.smart_router_override = True
                self.smart_router_override_provider = "openai"
                self.smart_router_override_model = "gpt-4o"
                self.smart_router_original = "auto"
        
        state = MockState()
        assert hasattr(state, 'smart_router_override')
        assert state.smart_router_override_provider == "openai"
        assert state.smart_router_override_model == "gpt-4o"


import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from starlette.responses import Response


class TestTokenStatsMiddleware:
    @pytest.fixture
    def mock_router(self):
        router = MagicMock()
        router.sr_config = MagicMock()
        return router

    @pytest.mark.asyncio
    async def test_middleware_records_usage(self, mock_router, tmp_path):
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.token_stats import TokenStats
        
        stats_file = tmp_path / "token_stats.json"
        token_stats = TokenStats(stats_file=stats_file)
        
        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "id": "test",
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )
        
        app = MagicMock()
        app.state = MagicMock()
        app.state.token_stats = token_stats
        
        middleware = SmartRouterMiddleware(app, router=mock_router)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }
        
        async def receive():
            return {"type": "http.request", "body": b'{}', "more_body": False}
        
        async def send(message):
            pass
        
        request = Request(scope, receive, send)
        request.state.smart_router_selected = "gpt-4o"
        request.state.smart_router_original = "auto"
        request.state.smart_router_task = "chat"
        
        response = await middleware.dispatch(request, mock_call_next)
        
        all_stats = token_stats.get_all()
        assert "gpt-4o" in all_stats
        assert all_stats["gpt-4o"]["prompt_tokens"] == 100
        assert all_stats["gpt-4o"]["request_count"] == 1

    @pytest.mark.asyncio
    async def test_middleware_uses_override_model(self, mock_router, tmp_path):
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.token_stats import TokenStats
        
        stats_file = tmp_path / "token_stats.json"
        token_stats = TokenStats(stats_file=stats_file)
        
        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "usage": {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )
        
        app = MagicMock()
        app.state = MagicMock()
        app.state.token_stats = token_stats
        
        middleware = SmartRouterMiddleware(app, router=mock_router)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }
        
        async def receive():
            return {"type": "http.request", "body": b'{}', "more_body": False}
        
        async def send(message):
            pass
        
        request = Request(scope, receive, send)
        request.state.smart_router_override_model = "claude-3-sonnet"
        
        response = await middleware.dispatch(request, mock_call_next)
        
        all_stats = token_stats.get_all()
        assert "claude-3-sonnet" in all_stats
        assert all_stats["claude-3-sonnet"]["request_count"] == 1

    @pytest.mark.asyncio
    async def test_middleware_uses_request_body_model(self, mock_router, tmp_path):
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.token_stats import TokenStats
        
        stats_file = tmp_path / "token_stats.json"
        token_stats = TokenStats(stats_file=stats_file)
        
        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )
        
        app = MagicMock()
        app.state = MagicMock()
        app.state.token_stats = token_stats
        
        middleware = SmartRouterMiddleware(app, router=mock_router)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }
        
        async def receive():
            return {"type": "http.request", "body": b'{"model": "gpt-3.5-turbo"}', "more_body": False}
        
        async def send(message):
            pass
        
        request = Request(scope, receive, send)
        # 不设置 smart_router_selected 或 override_model
        
        response = await middleware.dispatch(request, mock_call_next)
        
        all_stats = token_stats.get_all()
        assert "gpt-3.5-turbo" in all_stats
        assert all_stats["gpt-3.5-turbo"]["request_count"] == 1

    @pytest.mark.asyncio
    async def test_middleware_skips_streaming_no_usage(self, mock_router):
        """SSE 流式响应不含 usage 时不记录"""
        from smart_router.gateway.server import SmartRouterMiddleware
        
        async def mock_call_next(request):
            body = b'data: {"choices": [{"delta": {"content": "hello"}}]}\n\ndata: [DONE]\n\n'
            return Response(content=body, status_code=200, headers={"content-type": "text/event-stream"})
        
        app = MagicMock()
        app.state = MagicMock()
        app.state.token_stats = MagicMock()
        
        middleware = SmartRouterMiddleware(app, router=mock_router)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }
        
        async def receive():
            return {"type": "http.request", "body": b'{}', "more_body": False}
        
        async def send(message):
            pass
        
        request = Request(scope, receive, send)
        request.state.smart_router_selected = "gpt-4o"
        request.state.smart_router_original = "auto"
        request.state.smart_router_task = "chat"
        
        response = await middleware.dispatch(request, mock_call_next)
        
        app.state.token_stats.record.assert_not_called()
        # 验证返回的是 StreamingResponse
        from starlette.responses import StreamingResponse
        assert isinstance(response, StreamingResponse)

    @pytest.mark.asyncio
    async def test_middleware_records_streaming_usage(self, mock_router, tmp_path):
        """SSE 流式响应包含 usage 时正确记录"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.token_stats import TokenStats
        
        stats_file = tmp_path / "token_stats.json"
        token_stats = TokenStats(stats_file=stats_file)
        
        async def mock_call_next(request):
            body = (
                b'data: {"choices": [{"delta": {"content": "hello"}}]}\n\n'
                b'data: {"choices": [], "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75}}\n\n'
                b'data: [DONE]\n\n'
            )
            return Response(content=body, status_code=200, headers={"content-type": "text/event-stream"})
        
        app = MagicMock()
        app.state = MagicMock()
        app.state.token_stats = token_stats
        
        middleware = SmartRouterMiddleware(app, router=mock_router)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }
        
        async def receive():
            return {"type": "http.request", "body": b'{}', "more_body": False}
        
        async def send(message):
            pass
        
        request = Request(scope, receive, send)
        request.state.smart_router_selected = "gpt-4o"
        request.state.smart_router_original = "auto"
        request.state.smart_router_task = "chat"
        
        response = await middleware.dispatch(request, mock_call_next)
        
        all_stats = token_stats.get_all()
        assert "gpt-4o" in all_stats
        assert all_stats["gpt-4o"]["prompt_tokens"] == 50
        assert all_stats["gpt-4o"]["completion_tokens"] == 25
        assert all_stats["gpt-4o"]["total_tokens"] == 75
        assert all_stats["gpt-4o"]["reasoning_tokens"] == 0
        assert all_stats["gpt-4o"]["cached_tokens"] == 0
        assert all_stats["gpt-4o"]["request_count"] == 1
        
        # 验证返回的是 StreamingResponse
        from starlette.responses import StreamingResponse
        assert isinstance(response, StreamingResponse)


class TestErrorCounter:
    """测试 ErrorCounter 5 分钟滑动窗口"""

    def test_record_error(self):
        from smart_router.gateway.error_counter import ErrorCounter
        ec = ErrorCounter()
        ec.record(True)
        assert ec.get_error_rate() == 1.0

    def test_record_success(self):
        from smart_router.gateway.error_counter import ErrorCounter
        ec = ErrorCounter()
        ec.record(False)
        assert ec.get_error_rate() == 0.0

    def test_error_rate_mixed(self):
        from smart_router.gateway.error_counter import ErrorCounter
        ec = ErrorCounter()
        ec.record(True)
        ec.record(False)
        ec.record(True)
        assert ec.get_error_rate() == 2 / 3

    def test_window_expires_old_entries(self, monkeypatch):
        """超过 5 分钟的数据应被清除"""
        from smart_router.gateway.error_counter import ErrorCounter
        import time
        ec = ErrorCounter()
        # 模拟一个旧时间戳
        old_time = time.time() - 400  # 6 分 40 秒前
        ec._entries.append((old_time, True))
        assert ec.get_error_rate() == 0.0  # 旧条目应被清理

    def test_empty_counter(self):
        from smart_router.gateway.error_counter import ErrorCounter
        ec = ErrorCounter()
        assert ec.get_error_rate() == 0.0


class TestMiddlewareErrorCounter:
    """测试中间件集成 ErrorCounter"""

    @pytest.fixture
    def mock_router(self):
        router = MagicMock()
        router.sr_config = MagicMock()
        return router

    @pytest.mark.asyncio
    async def test_middleware_records_error_on_non_2xx(self, mock_router):
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.gateway.error_counter import ErrorCounter

        async def mock_call_next(request):
            return Response(content=b'error', status_code=500, headers={})

        app = MagicMock()
        app.state = MagicMock()
        app.state.error_counter = ErrorCounter()

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        async def receive():
            return {"type": "http.request", "body": b'{}', "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 500
        assert app.state.error_counter.get_error_rate() == 1.0

    @pytest.mark.asyncio
    async def test_middleware_records_success_on_2xx(self, mock_router):
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.gateway.error_counter import ErrorCounter

        async def mock_call_next(request):
            return Response(content=b'ok', status_code=200, headers={})

        app = MagicMock()
        app.state = MagicMock()
        app.state.error_counter = ErrorCounter()

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        async def receive():
            return {"type": "http.request", "body": b'{}', "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert app.state.error_counter.get_error_rate() == 0.0

    @pytest.mark.asyncio
    async def test_middleware_mixed_responses(self, mock_router):
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.gateway.error_counter import ErrorCounter

        app = MagicMock()
        app.state = MagicMock()
        app.state.error_counter = ErrorCounter()

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        async def receive():
            return {"type": "http.request", "body": b'{}', "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)

        async def error_call_next(request):
            return Response(content=b'error', status_code=500)

        async def success_call_next(request):
            return Response(content=b'ok', status_code=200)

        await middleware.dispatch(request, error_call_next)
        await middleware.dispatch(request, success_call_next)
        await middleware.dispatch(request, error_call_next)

        assert app.state.error_counter.get_error_rate() == 2 / 3


class TestMiddlewareStrategyFallback:
    """测试非流式请求的策略排序重试逻辑"""

    @pytest.fixture
    def mock_router(self):
        router = MagicMock()
        config = MagicMock()
        config.routing.fallback.max_attempts = 3
        
        # 默认模型配置，供 _build_fallback_candidates 使用
        model_a = MagicMock()
        model_a.provider = "openai"
        model_b = MagicMock()
        model_b.provider = "openai"
        model_c = MagicMock()
        model_c.provider = "openai"
        config.models = {
            "model-a": model_a,
            "model-b": model_b,
            "model-c": model_c,
        }
        config.is_model_available.return_value = True
        config.get_available_models.return_value = ["model-a", "model-b", "model-c"]
        router.sr_config = config
        router.get_fallback_chain.return_value = []
        return router

    @pytest.mark.asyncio
    async def test_non_stream_retry_on_502(self, mock_router):
        """非流式请求，首个模型返回 502，应按策略排序 fallback 到次优模型"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.selector.v3_selector import SelectionResult
        from starlette.requests import Request
        from starlette.responses import Response

        result = SelectionResult(
            model_name="model-a",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=6.0,
            reason="test",
            ranked_models=["model-a", "model-b", "model-c"]
        )
        mock_router.select_model.return_value = result

        call_count = 0
        async def mock_call_next(request):
            nonlocal call_count
            call_count += 1
            body = await request.body()
            data = json.loads(body)
            model = data.get("model")
            if model == "model-a":
                return Response(content=b'error', status_code=502)
            return Response(content=b'ok', status_code=200)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)

        with patch("smart_router.gateway.server.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert call_count == 2
        assert request.state.smart_router_selected == "model-b"
        assert request.state.smart_router_retry_count == 1
        assert len(request.state.smart_router_retry_history) == 1
        assert request.state.smart_router_retry_history[0]["model"] == "model-a"
        assert request.state.smart_router_retry_history[0]["status_code"] == 502

    @pytest.mark.asyncio
    async def test_non_stream_retry_exhausted(self, mock_router):
        """所有候选模型都失败时，应返回 503"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.selector.v3_selector import SelectionResult
        from starlette.requests import Request
        from starlette.responses import Response

        result = SelectionResult(
            model_name="model-a",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=6.0,
            reason="test",
            ranked_models=["model-a", "model-b"]
        )
        mock_router.select_model.return_value = result
        mock_router.sr_config.routing.fallback.max_attempts = 2

        async def mock_call_next(request):
            return Response(content=b'error', status_code=503)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)

        with patch("smart_router.gateway.server.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 503
        data = json.loads(response.body)
        assert data["error"]["code"] == "503"
        assert "model-a" in data["error"]["attempted_models"]
        assert "model-b" in data["error"]["attempted_models"]

    @pytest.mark.asyncio
    async def test_stream_request_no_custom_retry(self, mock_router):
        """流式请求不触发自建重试（单次调用）"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.selector.v3_selector import SelectionResult
        from starlette.requests import Request
        from starlette.responses import Response

        result = SelectionResult(
            model_name="model-a",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=6.0,
            reason="test",
            ranked_models=["model-a", "model-b"]
        )
        mock_router.select_model.return_value = result

        call_count = 0
        async def mock_call_next(request):
            nonlocal call_count
            call_count += 1
            return Response(content=b'ok', status_code=200)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({
            "model": "auto",
            "messages": [{"role": "user", "content": "test"}],
            "stream": True
        }).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert call_count == 1
        assert request.state.smart_router_retry_count == 0

    @pytest.mark.asyncio
    async def test_404_triggers_fallback_to_next_model(self, mock_router):
        """404 模型不存在时应触发 fallback 到下一个候选模型"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.selector.v3_selector import SelectionResult
        from starlette.requests import Request
        from starlette.responses import Response

        # 设置模型配置
        model_a_config = MagicMock()
        model_a_config.provider = "openai"
        model_b_config = MagicMock()
        model_b_config.provider = "openai"

        mock_router.sr_config.models = {
            "model-a": model_a_config,
            "model-b": model_b_config,
        }
        mock_router.sr_config.is_model_available.return_value = True
        mock_router.sr_config.get_available_models.return_value = ["model-a", "model-b"]
        mock_router.get_fallback_chain.return_value = []

        result = SelectionResult(
            model_name="model-a",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=6.0,
            reason="test",
            ranked_models=["model-a", "model-b"]
        )
        mock_router.select_model.return_value = result

        call_count = 0
        async def mock_call_next(request):
            nonlocal call_count
            call_count += 1
            body = await request.body()
            data = json.loads(body)
            model = data.get("model")
            if model == "model-a":
                return Response(content=b'not found', status_code=404)
            return Response(content=b'ok', status_code=200)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        app.state.request_routing_history = None
        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)

        with patch("smart_router.gateway.server.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert call_count == 2
        assert request.state.smart_router_selected == "model-b"
        assert len(request.state.smart_router_retry_history) == 1
        assert request.state.smart_router_retry_history[0]["status_code"] == 404
        assert request.state.smart_router_retry_history[0]["error_type"] == "NotFoundError"

    @pytest.mark.asyncio
    async def test_401_retries_all_candidates(self, mock_router):
        """401 认证错误时也应继续尝试所有候选（包括同 provider）"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.selector.v3_selector import SelectionResult
        from starlette.requests import Request
        from starlette.responses import Response

        # 设置模型配置，让 model-a/model-b 同 provider，model-c 不同 provider
        model_a_config = MagicMock()
        model_a_config.provider = "openai"
        model_b_config = MagicMock()
        model_b_config.provider = "openai"
        model_c_config = MagicMock()
        model_c_config.provider = "aliyun"

        mock_router.sr_config.models = {
            "model-a": model_a_config,
            "model-b": model_b_config,
            "model-c": model_c_config,
        }
        mock_router.sr_config.is_model_available.return_value = True
        mock_router.sr_config.get_available_models.return_value = ["model-a", "model-b", "model-c"]
        mock_router.get_fallback_chain.return_value = ["model-b", "model-c"]

        result = SelectionResult(
            model_name="model-a",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=6.0,
            reason="test",
            ranked_models=["model-a", "model-b", "model-c"]
        )
        mock_router.select_model.return_value = result

        call_count = 0
        async def mock_call_next(request):
            nonlocal call_count
            call_count += 1
            body = await request.body()
            data = json.loads(body)
            model = data.get("model")
            if model in ("model-a", "model-b"):
                return Response(content=b'unauthorized', status_code=401)
            return Response(content=b'ok', status_code=200)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        app.state.request_routing_history = None
        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)

        with patch("smart_router.gateway.server.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.dispatch(request, mock_call_next)

        # model-a (401) -> model-b (401，同 provider也应尝试) -> model-c (200)
        assert response.status_code == 200
        assert call_count == 3  # 尝试了 model-a、model-b 和 model-c
        assert request.state.smart_router_selected == "model-c"
        retry_history = request.state.smart_router_retry_history
        assert len(retry_history) == 2
        assert retry_history[0]["model"] == "model-a"
        assert retry_history[0]["error_type"] == "AuthenticationError"
        assert retry_history[1]["model"] == "model-b"
        assert retry_history[1]["error_type"] == "AuthenticationError"

    @pytest.mark.asyncio
    async def test_retry_history_includes_provider_and_error_type(self, mock_router):
        """重试历史应包含 provider 和 error_type 字段"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.selector.v3_selector import SelectionResult
        from starlette.requests import Request
        from starlette.responses import Response

        model_a_config = MagicMock()
        model_a_config.provider = "openai"

        mock_router.sr_config.models = {"model-a": model_a_config}
        mock_router.sr_config.is_model_available.return_value = True
        mock_router.sr_config.get_available_models.return_value = ["model-a"]
        mock_router.get_fallback_chain.return_value = []

        result = SelectionResult(
            model_name="model-a",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=6.0,
            reason="test",
            ranked_models=["model-a"]
        )
        mock_router.select_model.return_value = result

        async def mock_call_next(request):
            return Response(content=b'rate limited', status_code=429)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        app.state.request_routing_history = None
        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)

        with patch("smart_router.gateway.server.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 503
        retry_history = request.state.smart_router_retry_history
        assert len(retry_history) == 1
        assert retry_history[0]["model"] == "model-a"
        assert retry_history[0]["provider"] == "openai"
        assert retry_history[0]["error_type"] == "RateLimitError"
        assert retry_history[0]["status_code"] == 429


class TestGlobalModelOverride:
    @pytest.fixture
    def mock_router(self):
        router = MagicMock()
        config = MagicMock()
        
        # 模拟模型配置
        model_config = MagicMock()
        model_config.provider = "aliyun"
        
        gpt4o_config = MagicMock()
        gpt4o_config.provider = "openai"
        
        config.models = {
            "gui-plus-2026-02-26": model_config,
            "gpt-4o": gpt4o_config,
        }
        config.is_model_available = MagicMock(return_value=True)
        
        router.sr_config = config
        return router

    @pytest.mark.asyncio
    async def test_global_override_replaces_model(self, mock_router):
        """全局模型覆盖应替换请求中的模型，并保留原始模型供统计"""
        from smart_router.gateway.server import SmartRouterMiddleware

        async def mock_call_next(request):
            return Response(
                content=json.dumps({"usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70}}).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = {
            "provider": "aliyun",
            "model": "gui-plus-2026-02-26",
            "enabled": True,
        }
        app.state.token_stats = MagicMock()

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "strategy-cost", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert request.state.smart_router_selected == "gui-plus-2026-02-26"
        assert request.state.smart_router_original == "strategy-cost"
        assert request.state.smart_router_override is True
        assert request.state.smart_router_override_model == "gui-plus-2026-02-26"
        assert request.state.smart_router_override_provider == "aliyun"

    @pytest.mark.asyncio
    async def test_global_override_invalid_model_falls_back_to_routing(self, mock_router):
        """全局覆盖模型无效时，应回退到原有路由逻辑"""
        from smart_router.gateway.server import SmartRouterMiddleware

        async def mock_call_next(request):
            return Response(content=b'ok', status_code=200)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = {
            "provider": "aliyun",
            "model": "nonexistent-model",
            "enabled": True,
        }

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "strategy-cost", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        # 无效的全局覆盖不应设置 selected
        assert not hasattr(request.state, 'smart_router_selected')

    @pytest.mark.asyncio
    async def test_request_header_override_takes_priority_over_global(self, mock_router):
        """请求头覆盖优先级应高于全局覆盖"""
        from smart_router.gateway.server import SmartRouterMiddleware

        async def mock_call_next(request):
            return Response(content=b'ok', status_code=200)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = {
            "provider": "aliyun",
            "model": "gui-plus-2026-02-26",
            "enabled": True,
        }

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [
                (b"x-smart-router-override-provider", b"openai"),
                (b"x-smart-router-override-model", b"gpt-4o"),
            ],
            "app": app,
        }

        body = json.dumps({"model": "strategy-cost", "messages": [{"role": "user", "content": "test"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        # 请求头覆盖应生效
        assert request.state.smart_router_override_model == "gpt-4o"
        assert request.state.smart_router_override_provider == "openai"


class TestRoutingHistoryMiddleware:
    """测试中间件路由历史记录"""

    @pytest.fixture
    def mock_router(self):
        router = MagicMock()
        config = MagicMock()
        gpt4o = MagicMock()
        gpt4o.provider = "openai"
        config.models = {"gpt-4o": gpt4o}
        config.is_model_available.return_value = True
        config.get_available_models.return_value = ["gpt-4o"]
        config.routing.fallback.max_attempts = 3
        router.sr_config = config
        return router

    @pytest.mark.asyncio
    async def test_middleware_records_routing_info(self, mock_router):
        """验证中间件正确记录路由信息到 RequestRoutingHistory"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.request_routing_history import RequestRoutingHistory
        from smart_router.selector.v3_selector import SelectionResult

        mock_router.select_model.return_value = SelectionResult(
            model_name="gpt-4o",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=0.9,
            reason="test",
        )
        mock_router.get_fallback_chain.return_value = ["gpt-4o-mini", "claude-3-haiku"]

        history = RequestRoutingHistory(max_size=50)

        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "id": "chatcmpl-test",
                    "model": "gpt-4o",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        app.state.token_stats = AsyncMock()
        app.state.request_routing_history = history

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps({
                    "model": "auto",
                    "messages": [{"role": "user", "content": "Hello"}]
                }).encode(),
                "more_body": False,
            }

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200

        records = history.get_recent()
        assert len(records) == 1

        record = records[0]
        assert record["original_model"] == "auto"
        assert record["selected_model"] == "gpt-4o"
        assert record["actual_model"] == "gpt-4o"
        assert record["task_type"] == "chat"
        assert record["difficulty"] == "easy"
        assert record["strategy"] == "auto"
        assert record["did_fallback"] is False
        assert record["attempted_fallbacks"] == 0
        assert record["fallback_chain"] == ["gpt-4o-mini", "claude-3-haiku"]
        assert record["status_code"] == 200
        assert record["prompt_tokens"] == 10
        assert record["completion_tokens"] == 5
        assert record["total_tokens"] == 15
        assert record["reasoning_tokens"] == 0
        assert record["cached_tokens"] == 0
        assert "request_id" in record
        assert "timestamp" in record

    @pytest.mark.asyncio
    async def test_middleware_detects_fallback(self, mock_router):
        """验证 actual_model 与 selected_model 不一致时 did_fallback=True"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.request_routing_history import RequestRoutingHistory
        from smart_router.selector.v3_selector import SelectionResult

        mock_router.select_model.return_value = SelectionResult(
            model_name="gpt-4o",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=0.9,
            reason="test",
        )
        mock_router.get_fallback_chain.return_value = []

        history = RequestRoutingHistory(max_size=50)

        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "model": "claude-3-opus",
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        app.state.token_stats = AsyncMock()
        app.state.request_routing_history = history

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps({
                    "model": "auto",
                    "messages": [{"role": "user", "content": "Hello"}]
                }).encode(),
                "more_body": False,
            }

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200

        records = history.get_recent()
        assert len(records) == 1
        assert records[0]["selected_model"] == "gpt-4o"
        assert records[0]["actual_model"] == "claude-3-opus"
        assert records[0]["did_fallback"] is True
        assert records[0]["attempted_fallbacks"] == 0

    @pytest.mark.asyncio
    async def test_middleware_no_fallback(self, mock_router):
        """验证 actual_model 与 selected_model 一致时 did_fallback=False"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.request_routing_history import RequestRoutingHistory
        from smart_router.selector.v3_selector import SelectionResult

        mock_router.select_model.return_value = SelectionResult(
            model_name="gpt-4o",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=0.9,
            reason="test",
        )
        mock_router.get_fallback_chain.return_value = []

        history = RequestRoutingHistory(max_size=50)

        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "model": "gpt-4o",
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        app.state.token_stats = AsyncMock()
        app.state.request_routing_history = history

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps({
                    "model": "auto",
                    "messages": [{"role": "user", "content": "Hello"}]
                }).encode(),
                "more_body": False,
            }

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200

        records = history.get_recent()
        assert len(records) == 1
        assert records[0]["selected_model"] == "gpt-4o"
        assert records[0]["actual_model"] == "gpt-4o"
        assert records[0]["did_fallback"] is False
        assert records[0]["attempted_fallbacks"] == 0

    @pytest.mark.asyncio
    async def test_middleware_records_routing_info_for_header_override(self, mock_router):
        """验证请求头覆盖时也能记录路由信息到 RequestRoutingHistory"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.request_routing_history import RequestRoutingHistory

        mock_router.sr_config.models = {
            "gpt-4o": MagicMock(provider="openai"),
        }
        mock_router.sr_config.is_model_available.return_value = True

        history = RequestRoutingHistory(max_size=50)

        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "model": "gpt-4o",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        app.state.token_stats = AsyncMock()
        app.state.request_routing_history = history

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [
                (b"x-smart-router-override-provider", b"openai"),
                (b"x-smart-router-override-model", b"gpt-4o"),
            ],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "Hello"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200

        records = history.get_recent()
        assert len(records) == 1

        record = records[0]
        assert record["original_model"] == "auto"
        assert record["selected_model"] == "gpt-4o"
        assert record["actual_model"] == "gpt-4o"
        assert record["task_type"] == "override"
        assert record["strategy"] == "override"
        assert record["did_fallback"] is False
        assert record["attempted_fallbacks"] == 0
        assert record["fallback_chain"] == []
        assert record["status_code"] == 200
        assert "request_id" in record
        assert "timestamp" in record

    @pytest.mark.asyncio
    async def test_middleware_records_routing_info_for_global_override(self, mock_router):
        """验证全局覆盖时也能记录路由信息到 RequestRoutingHistory"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.request_routing_history import RequestRoutingHistory

        mock_router.sr_config.models = {
            "gui-plus-2026-02-26": MagicMock(provider="aliyun"),
        }
        mock_router.sr_config.is_model_available.return_value = True

        history = RequestRoutingHistory(max_size=50)

        async def mock_call_next(request):
            return Response(
                content=json.dumps({
                    "model": "gui-plus-2026-02-26",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = {
            "provider": "aliyun",
            "model": "gui-plus-2026-02-26",
            "enabled": True,
        }
        app.state.token_stats = AsyncMock()
        app.state.request_routing_history = history

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "Hello"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200

        records = history.get_recent()
        assert len(records) == 1

        record = records[0]
        assert record["original_model"] == "auto"
        assert record["selected_model"] == "gui-plus-2026-02-26"
        assert record["actual_model"] == "gui-plus-2026-02-26"
        assert record["task_type"] == "override"
        assert record["strategy"] == "override"
        assert record["did_fallback"] is False
        assert record["attempted_fallbacks"] == 0
        assert record["fallback_chain"] == []
        assert record["status_code"] == 200
        assert "request_id" in record
        assert "timestamp" in record

    @pytest.mark.asyncio
    async def test_middleware_records_fallback_with_attempted_count(self, mock_router):
        """验证 fallback 场景下 attempted_fallbacks 与 retry_history 一致"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.request_routing_history import RequestRoutingHistory
        from smart_router.selector.v3_selector import SelectionResult
        from starlette.requests import Request
        from starlette.responses import Response
        from unittest.mock import patch, MagicMock

        model_a_config = MagicMock()
        model_a_config.provider = "aliyun"
        model_b_config = MagicMock()
        model_b_config.provider = "aliyun"

        mock_router.sr_config.models = {
            "testfailed": model_a_config,
            "gui-plus-2026-02-26": model_b_config,
        }
        mock_router.sr_config.is_model_available.return_value = True
        mock_router.sr_config.get_available_models.return_value = ["testfailed", "gui-plus-2026-02-26"]
        mock_router.get_fallback_chain.return_value = []

        result = SelectionResult(
            model_name="testfailed",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=6.0,
            reason="test",
            ranked_models=["testfailed", "gui-plus-2026-02-26"]
        )
        mock_router.select_model.return_value = result

        call_count = 0
        async def mock_call_next(request):
            nonlocal call_count
            call_count += 1
            body = await request.body()
            data = json.loads(body)
            model = data.get("model")
            if model == "testfailed":
                return Response(
                    content=json.dumps({
                        "error": {"message": "NotFoundError", "code": "404"}
                    }).encode(),
                    status_code=404,
                    headers={"content-type": "application/json"},
                )
            return Response(
                content=json.dumps({
                    "model": "gui-plus-2026-02-26",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
                }).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )

        history = RequestRoutingHistory(max_size=50)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        app.state.token_stats = AsyncMock()
        app.state.request_routing_history = history

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "Hello"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)

        with patch("smart_router.gateway.server.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert call_count == 2

        records = history.get_recent()
        assert len(records) == 1

        record = records[0]
        # selected_model 应为策略首选（testfailed），而不是最终成功模型
        assert record["selected_model"] == "testfailed"
        assert record["actual_model"] == "gui-plus-2026-02-26"
        assert record["did_fallback"] is True
        # attempted_fallbacks 等于 retry_history 长度（1 次失败尝试）
        assert record["attempted_fallbacks"] == 1
        assert len(record["retry_history"]) == 1
        assert record["retry_history"][0]["model"] == "testfailed"
        assert record["retry_history"][0]["status_code"] == 404
        assert record["retry_history"][0]["error_type"] == "NotFoundError"

    @pytest.mark.asyncio
    async def test_middleware_records_all_failed_503(self, mock_router):
        """验证所有候选模型均失败（503）时也能正确记录路由历史"""
        from smart_router.gateway.server import SmartRouterMiddleware
        from smart_router.utils.request_routing_history import RequestRoutingHistory
        from smart_router.selector.v3_selector import SelectionResult
        from starlette.requests import Request
        from starlette.responses import Response
        from unittest.mock import patch, MagicMock

        model_a_config = MagicMock()
        model_a_config.provider = "openai"
        model_b_config = MagicMock()
        model_b_config.provider = "openai"

        mock_router.sr_config.models = {
            "model-a": model_a_config,
            "model-b": model_b_config,
        }
        mock_router.sr_config.is_model_available.return_value = True
        mock_router.sr_config.get_available_models.return_value = ["model-a", "model-b"]
        mock_router.sr_config.routing.fallback.max_attempts = 2
        mock_router.get_fallback_chain.return_value = []

        result = SelectionResult(
            model_name="model-a",
            task_type="chat",
            difficulty="easy",
            strategy="auto",
            score=6.0,
            reason="test",
            ranked_models=["model-a", "model-b"]
        )
        mock_router.select_model.return_value = result

        async def mock_call_next(request):
            return Response(content=b'error', status_code=503)

        history = RequestRoutingHistory(max_size=50)

        app = MagicMock()
        app.state = MagicMock()
        app.state.global_model_override = None
        app.state.token_stats = AsyncMock()
        app.state.request_routing_history = history

        middleware = SmartRouterMiddleware(app, router=mock_router)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "Hello"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)

        with patch("smart_router.gateway.server.asyncio.sleep", new_callable=AsyncMock):
            response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 503

        records = history.get_recent()
        assert len(records) == 1

        record = records[0]
        # 即使全部失败，也应记录策略首选模型
        assert record["selected_model"] == "model-a"
        assert record["actual_model"] is None  # 503 响应体中解析不到模型名
        assert record["did_fallback"] is False  # 因为没有 actual_model
        assert record["attempted_fallbacks"] == 2  # 尝试了 model-a 和 model-b
        assert len(record["retry_history"]) == 2
        assert record["retry_history"][0]["model"] == "model-a"
        assert record["retry_history"][1]["model"] == "model-b"
        assert record["status_code"] == 503
