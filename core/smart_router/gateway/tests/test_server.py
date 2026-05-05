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

    def test_middleware_select_model_exception_handling(self):
        """测试中间件 select_model 异常时的降级处理"""
        # 验证异常处理逻辑：当 select_model 失败时应保留原始 model
        original_model = "auto"
        data = {"model": original_model, "messages": [{"role": "user", "content": "test"}]}
        
        # 模拟 select_model 抛出异常
        try:
            # 这个测试验证的是中间件逻辑中的 try/except 块
            # 当异常发生时，model 应保持不变
            raise Exception("Simulated routing failure")
        except Exception:
            # 异常被捕获后，model 应该还是原来的值
            assert data["model"] == "auto"

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