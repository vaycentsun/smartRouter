"""model_mappings 中间件映射逻辑与 Dashboard API 集成测试"""

import json
from unittest.mock import MagicMock

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from smart_router.config.mapping_loader import ModelMappingLoader
from smart_router.config.mapping_schema import ModelMappingConfig, ModelMappingRule
from smart_router.gateway.server import SmartRouterMiddleware

# ==================== Fixtures ====================

@pytest.fixture
def mock_router_with_mappings():
    """返回带有模型映射配置的 mock router"""
    router = MagicMock()
    router.model_mappings = ModelMappingConfig(
        enabled=True,
        mappings=[
            ModelMappingRule(
                id="map_gpt4_to_claude",
                enabled=True,
                from_model="gpt-4",
                to_provider="anthropic",
                to_model="claude-3-opus",
                to_litellm_provider="anthropic",
                to_base_url="https://api.anthropic.com/v1",
                to_api_key="sk-test",
            ),
            ModelMappingRule(
                id="map_disabled",
                enabled=False,
                from_model="gpt-3.5",
                to_provider="openai",
                to_model="gpt-4o",
                to_litellm_provider="openai",
                to_base_url="https://api.openai.com/v1",
                to_api_key="sk-test",
            ),
        ]
    )
    router.sr_config = MagicMock()
    return router


@pytest.fixture
def mock_router_no_mappings():
    """返回没有模型映射配置的 mock router"""
    router = MagicMock()
    router.model_mappings = ModelMappingConfig(enabled=False, mappings=[])
    router.sr_config = MagicMock()
    return router


@pytest.fixture
def mock_app():
    """返回带有必要 state 属性的 mock ASGI app"""
    app = MagicMock()
    app.state = MagicMock()
    app.state.global_model_override = None
    app.state.error_counter = MagicMock()
    return app


# ==================== 场景 1: 中间件精确匹配映射规则 ====================

class TestMiddlewareMappingMatch:
    """中间件精确匹配映射规则，请求体 model 被替换"""

    @pytest.mark.asyncio
    async def test_middleware_maps_model_exact_match(self, mock_router_with_mappings, mock_app):
        """精确匹配映射规则时，下游请求体 model 被替换，响应头包含映射信息"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_mappings)

        captured_body = None

        async def mock_call_next(request):
            nonlocal captured_body
            body = await request.body()
            captured_body = json.loads(body)
            return Response(
                content=json.dumps({"id": "test", "model": "claude-3-opus"}).encode(),
                status_code=200,
                headers={"content-type": "application/json"},
            )

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-4", "messages": [{"role": "user", "content": "hello"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        # 验证下游请求体已被替换
        assert captured_body is not None
        assert captured_body["model"] == "claude-3-opus"
        assert captured_body["messages"] == [{"role": "user", "content": "hello"}]

    @pytest.mark.asyncio
    async def test_middleware_sets_mapping_state(self, mock_router_with_mappings, mock_app):
        """映射时 request.state 被正确设置"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_mappings)

        async def mock_call_next(request):
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-4", "messages": []}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert request.state.smart_router_mapped is True
        assert request.state.smart_router_mapped_from == "gpt-4"
        assert request.state.smart_router_mapped_to == "claude-3-opus"
        assert hasattr(request.state, 'smart_router_request_id')
        assert hasattr(request.state, 'smart_router_routing_info')
        assert request.state.smart_router_routing_info["task_type"] == "mapping"


# ==================== 场景 2: 中间件无匹配时，请求体不变 ====================

class TestMiddlewareMappingNoMatch:
    """中间件无匹配时，请求体不变"""

    @pytest.mark.asyncio
    async def test_middleware_no_mapping_model_unchanged(self, mock_router_with_mappings, mock_app):
        """模型不在映射表中时，请求体未被修改"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_mappings)

        captured_body = None

        async def mock_call_next(request):
            nonlocal captured_body
            body = await request.body()
            captured_body = json.loads(body)
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert captured_body is not None
        assert captured_body["model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_middleware_disabled_mapping_no_change(self, mock_router_no_mappings, mock_app):
        """映射全局关闭时，请求体未被修改"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_no_mappings)

        captured_body = None

        async def mock_call_next(request):
            nonlocal captured_body
            body = await request.body()
            captured_body = json.loads(body)
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-4", "messages": []}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert captured_body is not None
        assert captured_body["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_middleware_disabled_rule_no_change(self, mock_router_with_mappings, mock_app):
        """映射规则关闭时（from_model 匹配但 enabled=False），请求体未被修改"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_mappings)

        captured_body = None

        async def mock_call_next(request):
            nonlocal captured_body
            body = await request.body()
            captured_body = json.loads(body)
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-3.5", "messages": []}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert captured_body is not None
        assert captured_body["model"] == "gpt-3.5"


# ==================== 场景 3: API GET /api/model-mappings 返回正确 JSON ====================

class TestModelMappingsGetAPI:
    """API GET /api/model-mappings 返回正确 JSON"""

    @pytest.fixture
    def mapping_client(self, tmp_path):
        """构建带有 model-mappings API 的 TestClient，使用临时配置目录"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        app = FastAPI()

        @app.get("/api/model-mappings")
        async def get_model_mappings():
            loader = ModelMappingLoader(config_dir)
            config = loader.load()
            return {
                "enabled": config.enabled,
                "mappings": [
                    {
                        "id": r.id,
                        "enabled": r.enabled,
                        "from_model": r.from_model,
                        "to_provider": r.to_provider,
                        "to_model": r.to_model,
                        "to_litellm_provider": r.to_litellm_provider,
                        "to_base_url": r.to_base_url,
                        "to_api_key": r.to_api_key,
                    }
                    for r in config.mappings
                ]
            }

        return TestClient(app), config_dir

    def test_get_model_mappings_empty(self, mapping_client):
        """无配置文件时返回 enabled=false 和空 mappings"""
        client, config_dir = mapping_client
        response = client.get("/api/model-mappings")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["mappings"] == []

    def test_get_model_mappings_with_data(self, mapping_client):
        """有配置文件时返回正确结构和内容"""
        client, config_dir = mapping_client

        # 创建临时映射配置文件
        mapping_file = config_dir / "model_mappings.yaml"
        mapping_data = {
            "enabled": True,
            "mappings": [
                {
                    "id": "test_map_1",
                    "enabled": True,
                    "from_model": "gpt-4",
                    "to_provider": "anthropic",
                    "to_model": "claude-3-opus",
                    "to_litellm_provider": "anthropic",
                    "to_base_url": "https://api.anthropic.com/v1",
                    "to_api_key": "sk-test-key",
                }
            ]
        }
        mapping_file.write_text(yaml.safe_dump(mapping_data), encoding="utf-8")

        response = client.get("/api/model-mappings")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert len(data["mappings"]) == 1
        mapping = data["mappings"][0]
        assert mapping["id"] == "test_map_1"
        assert mapping["enabled"] is True
        assert mapping["from_model"] == "gpt-4"
        assert mapping["to_provider"] == "anthropic"
        assert mapping["to_model"] == "claude-3-opus"
        assert mapping["to_litellm_provider"] == "anthropic"
        assert mapping["to_base_url"] == "https://api.anthropic.com/v1"
        assert mapping["to_api_key"] == "sk-test-key"


# ==================== 场景 4: API PUT /api/model-mappings/yaml 保存后文件内容正确 ====================

class TestModelMappingsPutYamlAPI:
    """API PUT /api/model-mappings/yaml 保存后文件内容正确"""

    @pytest.fixture
    def mapping_yaml_client(self, tmp_path):
        """构建带有 model-mappings/yaml API 的 TestClient，使用临时配置目录"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        app = FastAPI()

        @app.put("/api/model-mappings/yaml")
        async def update_model_mappings_yaml(body: dict):
            raw_yaml = body.get("yaml", "")
            try:
                loader = ModelMappingLoader(config_dir)
                loader.save_raw(raw_yaml)
                return {"success": True}
            except Exception as e:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=str(e))

        return TestClient(app), config_dir

    def test_put_yaml_creates_file(self, mapping_yaml_client):
        """PUT YAML 后文件被正确创建"""
        client, config_dir = mapping_yaml_client

        yaml_text = (
            "enabled: true\n"
            "mappings:\n"
            "  - id: map_1\n"
            "    enabled: true\n"
            "    from_model: gpt-4\n"
            "    to_provider: anthropic\n"
            "    to_model: claude-3-opus\n"
            "    to_litellm_provider: anthropic\n"
            "    to_base_url: https://api.anthropic.com/v1\n"
            "    to_api_key: sk-test\n"
        )

        response = client.put("/api/model-mappings/yaml", json={"yaml": yaml_text})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证文件内容
        mapping_file = config_dir / "model_mappings.yaml"
        assert mapping_file.exists()
        saved_data = yaml.safe_load(mapping_file.read_text(encoding="utf-8"))
        assert saved_data["enabled"] is True
        assert len(saved_data["mappings"]) == 1
        assert saved_data["mappings"][0]["id"] == "map_1"
        assert saved_data["mappings"][0]["from_model"] == "gpt-4"
        assert saved_data["mappings"][0]["to_model"] == "claude-3-opus"

    def test_put_yaml_overwrites_existing(self, mapping_yaml_client):
        """PUT YAML 覆盖已有文件"""
        client, config_dir = mapping_yaml_client

        # 先创建旧文件
        old_file = config_dir / "model_mappings.yaml"
        old_file.write_text("enabled: false\nmappings: []\n", encoding="utf-8")

        yaml_text = (
            "enabled: true\n"
            "mappings:\n"
            "  - id: new_map\n"
            "    enabled: true\n"
            "    from_model: llama\n"
            "    to_provider: ollama\n"
            "    to_model: llama3\n"
            "    to_litellm_provider: ollama\n"
            "    to_base_url: http://localhost:11434\n"
            "    to_api_key: ''\n"
        )

        response = client.put("/api/model-mappings/yaml", json={"yaml": yaml_text})
        assert response.status_code == 200

        saved_data = yaml.safe_load(old_file.read_text(encoding="utf-8"))
        assert saved_data["enabled"] is True
        assert saved_data["mappings"][0]["id"] == "new_map"
        assert saved_data["mappings"][0]["from_model"] == "llama"


# ==================== 场景 5: API PUT 无效 YAML 返回 400 ====================

class TestModelMappingsPutYamlInvalid:
    """API PUT 无效 YAML 返回 400"""

    @pytest.fixture
    def mapping_yaml_client(self, tmp_path):
        """构建带有 model-mappings/yaml API 的 TestClient，使用临时配置目录"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        app = FastAPI()

        @app.put("/api/model-mappings/yaml")
        async def update_model_mappings_yaml(body: dict):
            raw_yaml = body.get("yaml", "")
            try:
                loader = ModelMappingLoader(config_dir)
                loader.save_raw(raw_yaml)
                return {"success": True}
            except Exception as e:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=str(e))

        return TestClient(app), config_dir

    def test_put_invalid_yaml_syntax_returns_400(self, mapping_yaml_client):
        """无效 YAML 语法返回 400"""
        client, config_dir = mapping_yaml_client

        invalid_yaml = "enabled: true\nmappings:\n  - id: test\n    enabled: true\n    bad_indent"

        response = client.put("/api/model-mappings/yaml", json={"yaml": invalid_yaml})
        assert response.status_code == 400

    def test_put_invalid_yaml_schema_returns_400(self, mapping_yaml_client):
        """YAML 语法正确但 schema 验证失败返回 400"""
        client, config_dir = mapping_yaml_client

        # missing required fields like to_base_url
        invalid_yaml = (
            "enabled: true\n"
            "mappings:\n"
            "  - id: test\n"
            "    enabled: true\n"
            "    from_model: gpt-4\n"
            "    to_provider: anthropic\n"
            "    to_model: claude\n"
        )

        response = client.put("/api/model-mappings/yaml", json={"yaml": invalid_yaml})
        assert response.status_code == 400

    def test_put_empty_body_returns_400(self, mapping_yaml_client):
        """空 YAML 文本应触发验证失败"""
        client, config_dir = mapping_yaml_client

        response = client.put("/api/model-mappings/yaml", json={"yaml": ""})
        assert response.status_code == 400


# ==================== 场景 6: 响应头包含 X-Smart-Router-Mapped ====================

class TestMiddlewareMappingResponseHeaders:
    """响应头包含 X-Smart-Router-Mapped"""

    @pytest.mark.asyncio
    async def test_response_header_contains_mapped(self, mock_router_with_mappings, mock_app):
        """映射请求后，验证响应头包含映射相关信息"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_mappings)

        async def mock_call_next(request):
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-4", "messages": []}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert response.headers["X-Smart-Router-Mapped"] == "true"
        assert response.headers["X-Smart-Router-Mapped-From"] == "gpt-4"
        assert response.headers["X-Smart-Router-Mapped-To"] == "claude-3-opus"

    @pytest.mark.asyncio
    async def test_response_header_no_mapped_when_no_match(self, mock_router_with_mappings, mock_app):
        """无匹配时响应头不应包含 X-Smart-Router-Mapped"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_mappings)

        async def mock_call_next(request):
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "unknown-model", "messages": []}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert "X-Smart-Router-Mapped" not in response.headers
        assert "X-Smart-Router-Mapped-From" not in response.headers
        assert "X-Smart-Router-Mapped-To" not in response.headers


# ==================== 场景 7: /v1/responses 端点支持模型映射 ====================

class TestResponsesEndpointMapping:
    """/v1/responses 端点支持模型映射"""

    @pytest.mark.asyncio
    async def test_responses_endpoint_model_mapping(self, mock_router_with_mappings, mock_app):
        """/v1/responses 请求匹配映射规则时，model 被替换"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_mappings)

        captured_body = None

        async def mock_call_next(request):
            nonlocal captured_body
            body = await request.body()
            captured_body = json.loads(body)
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/responses",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-4", "input": "hello"}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert captured_body is not None
        assert captured_body["model"] == "claude-3-opus"
        assert captured_body["input"] == "hello"

    @pytest.mark.asyncio
    async def test_responses_endpoint_mapping_response_headers(self, mock_router_with_mappings, mock_app):
        """映射后的 /v1/responses 响应包含正确头"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_mappings)

        async def mock_call_next(request):
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/responses",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-4", "input": []}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert response.headers["X-Smart-Router-Mapped"] == "true"
        assert response.headers["X-Smart-Router-Mapped-From"] == "gpt-4"
        assert response.headers["X-Smart-Router-Mapped-To"] == "claude-3-opus"


# ==================== 场景 8: /v1/responses 端点支持 Model Override ====================

class TestResponsesEndpointOverride:
    """/v1/responses 端点支持 Model Override"""

    @pytest.mark.asyncio
    async def test_responses_endpoint_override_header(self, mock_app):
        """带 Override 头的 /v1/responses 请求，model 被替换"""
        router = MagicMock()
        router.model_mappings = None

        # mock config
        config = MagicMock()
        model_config = MagicMock()
        model_config.provider = "openai"
        config.models = {"gpt-4o": model_config}
        config.is_model_available = MagicMock(return_value=True)
        router.sr_config = config

        middleware = SmartRouterMiddleware(mock_app, router=router)

        captured_body = None

        async def mock_call_next(request):
            nonlocal captured_body
            body = await request.body()
            captured_body = json.loads(body)
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/responses",
            "headers": [
                (b"x-smart-router-override-provider", b"openai"),
                (b"x-smart-router-override-model", b"gpt-4o"),
            ],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-4", "input": "hello"}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert captured_body is not None
        assert captured_body["model"] == "gpt-4o"
        assert response.headers["X-Smart-Router-Override-Active"] == "true"
        assert response.headers["X-Smart-Router-Override-Provider"] == "openai"
        assert response.headers["X-Smart-Router-Override-Model"] == "gpt-4o"


# ==================== 场景 9: /v1/responses 端点无映射时直接透传 ====================

class TestResponsesEndpointPassthrough:
    """/v1/responses 端点无映射/覆盖时直接透传，不走智能路由"""

    @pytest.mark.asyncio
    async def test_responses_endpoint_no_mapping_no_route(self, mock_router_no_mappings, mock_app):
        """无映射、无覆盖时，请求体不变，_route_with_retry 不被调用"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_no_mappings)

        captured_body = None
        route_called = False

        original_route_with_retry = middleware._route_with_retry

        async def mock_route_with_retry(request, call_next, data, original_model):
            nonlocal route_called
            route_called = True
            return await original_route_with_retry(request, call_next, data, original_model)

        middleware._route_with_retry = mock_route_with_retry

        async def mock_call_next(request):
            nonlocal captured_body
            body = await request.body()
            captured_body = json.loads(body)
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/responses",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "auto", "input": "test"}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert captured_body is not None
        assert captured_body["model"] == "auto"
        assert route_called is False


# ==================== 场景 9: /v1/chat/completions 回归测试 ====================

class TestChatCompletionsRegression:
    """确保 /v1/chat/completions 的现有行为不受影响"""

    @pytest.mark.asyncio
    async def test_chat_completions_routing_still_works(self, mock_router_with_mappings, mock_app):
        """chat/completions 上的智能路由仍然被触发"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_mappings)

        route_called = False

        original_route_with_retry = middleware._route_with_retry

        async def mock_route_with_retry(request, call_next, data, original_model):
            nonlocal route_called
            route_called = True
            return Response(content=b'routed', status_code=200)

        middleware._route_with_retry = mock_route_with_retry

        async def mock_call_next(request):
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "auto", "messages": [{"role": "user", "content": "hi"}]}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert route_called is True


# ==================== 场景 10: 端点过滤逻辑 ====================

class TestEndpointFiltering:
    """映射规则按端点过滤"""

    @pytest.fixture
    def mock_router_with_endpoint_rules(self):
        """返回带有端点过滤规则的 mock router"""
        router = MagicMock()
        router.model_mappings = ModelMappingConfig(
            enabled=True,
            mappings=[
                ModelMappingRule(
                    id="map_chat_only",
                    enabled=True,
                    from_model="gpt-4",
                    to_provider="anthropic",
                    to_model="claude-chat",
                    to_litellm_provider="anthropic",
                    to_base_url="https://api.anthropic.com/v1",
                    to_api_key="sk-test",
                    endpoints=["chat"],
                ),
                ModelMappingRule(
                    id="map_responses_only",
                    enabled=True,
                    from_model="gpt-4",
                    to_provider="openai",
                    to_model="gpt-4o-resp",
                    to_litellm_provider="openai",
                    to_base_url="https://api.openai.com/v1",
                    to_api_key="sk-test",
                    endpoints=["responses"],
                ),
                ModelMappingRule(
                    id="map_both",
                    enabled=True,
                    from_model="gpt-3.5",
                    to_provider="aliyun",
                    to_model="qwen-turbo",
                    to_litellm_provider="openai",
                    to_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    to_api_key="sk-test",
                    endpoints=["chat", "responses"],
                ),
            ]
        )
        router.sr_config = MagicMock()
        return router

    @pytest.mark.asyncio
    async def test_chat_endpoint_only_matches_chat_rules(self, mock_router_with_endpoint_rules, mock_app):
        """chat 端点只匹配含 chat 的规则"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_endpoint_rules)

        captured_body = None

        async def mock_call_next(request):
            nonlocal captured_body
            body = await request.body()
            captured_body = json.loads(body)
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-4", "messages": []}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert captured_body is not None
        assert captured_body["model"] == "claude-chat"

    @pytest.mark.asyncio
    async def test_responses_endpoint_only_matches_responses_rules(self, mock_router_with_endpoint_rules, mock_app):
        """responses 端点只匹配含 responses 的规则"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_endpoint_rules)

        captured_body = None

        async def mock_call_next(request):
            nonlocal captured_body
            body = await request.body()
            captured_body = json.loads(body)
            return Response(content=b'ok', status_code=200)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/responses",
            "headers": [],
            "app": mock_app,
        }

        body = json.dumps({"model": "gpt-4", "input": "test"}).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            pass

        request = Request(scope, receive, send)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        assert captured_body is not None
        assert captured_body["model"] == "gpt-4o-resp"

    @pytest.mark.asyncio
    async def test_both_endpoints_matches_both_rules(self, mock_router_with_endpoint_rules, mock_app):
        """两个端点都匹配含两个端点的规则"""
        middleware = SmartRouterMiddleware(mock_app, router=mock_router_with_endpoint_rules)

        for path, endpoint_type in [("/v1/chat/completions", "chat"), ("/v1/responses", "responses")]:
            captured_body = None

            async def mock_call_next(request):
                nonlocal captured_body
                body = await request.body()
                captured_body = json.loads(body)
                return Response(content=b'ok', status_code=200)

            scope = {
                "type": "http",
                "method": "POST",
                "path": path,
                "headers": [],
                "app": mock_app,
            }

            body_key = "messages" if endpoint_type == "chat" else "input"
            body = json.dumps({"model": "gpt-3.5", body_key: []}).encode()

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            async def send(message):
                pass

            request = Request(scope, receive, send)
            response = await middleware.dispatch(request, mock_call_next)

            assert response.status_code == 200
            assert captured_body is not None
            assert captured_body["model"] == "qwen-turbo", f"Failed for {path}"

    @pytest.mark.asyncio
    async def test_default_endpoints_backward_compatible(self, mock_app):
        """无 endpoints 字段时默认匹配两个端点（向后兼容）"""
        router = MagicMock()
        router.model_mappings = ModelMappingConfig(
            enabled=True,
            mappings=[
                ModelMappingRule(
                    id="map_default",
                    enabled=True,
                    from_model="gpt-4",
                    to_provider="anthropic",
                    to_model="claude-default",
                    to_litellm_provider="anthropic",
                    to_base_url="https://api.anthropic.com/v1",
                    to_api_key="sk-test",
                    # 不指定 endpoints，使用默认值
                ),
            ]
        )
        router.sr_config = MagicMock()
        middleware = SmartRouterMiddleware(mock_app, router=router)

        for path in ["/v1/chat/completions", "/v1/responses"]:
            captured_body = None

            async def mock_call_next(request):
                nonlocal captured_body
                body = await request.body()
                captured_body = json.loads(body)
                return Response(content=b'ok', status_code=200)

            scope = {
                "type": "http",
                "method": "POST",
                "path": path,
                "headers": [],
                "app": mock_app,
            }

            body_key = "messages" if path == "/v1/chat/completions" else "input"
            body = json.dumps({"model": "gpt-4", body_key: []}).encode()

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            async def send(message):
                pass

            request = Request(scope, receive, send)
            response = await middleware.dispatch(request, mock_call_next)

            assert response.status_code == 200
            assert captured_body is not None
            assert captured_body["model"] == "claude-default", f"Failed for {path}"
