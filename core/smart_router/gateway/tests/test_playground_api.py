"""Playground API 测试"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from smart_router.config.schema import (
    Config,
    FallbackConfig,
    ModelCapabilities,
    ModelConfig,
    ModelPrice,
    ProviderConfig,
    RoutingConfig,
)
from smart_router.gateway.dashboard_api import build_dashboard_app


@pytest.fixture
def client(tmp_path):
    from unittest.mock import patch

    import smart_router.utils.request_routing_history as rrh
    # 使用临时文件隔离测试状态，避免历史记录跨测试泄漏
    temp_history = tmp_path / "request_routing_history.json"
    with patch.object(rrh, "DEFAULT_HISTORY_FILE", temp_history):
        app = build_dashboard_app(static_dir=None)
        return TestClient(app)


@pytest.fixture
def mock_config():
    return Config(
        providers={
            "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
        },
        models={
            "gpt-4o": ModelConfig(
                provider="openai",
                litellm_model="openai/gpt-4o",
                capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                supported_tasks=["chat"],
                difficulty_support=["easy"],
                price=ModelPrice(prompt_per_1k=0.005, completion_per_1k=0.015, currency="USD"),
            ),
            "claude-3": ModelConfig(
                provider="openai",
                litellm_model="openai/claude-3",
                capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                supported_tasks=["chat"],
                difficulty_support=["easy"],
                price=ModelPrice(prompt_per_1k=0.003, completion_per_1k=0.015, currency="USD"),
            ),
        },
        routing=RoutingConfig(tasks={}, difficulties={}, strategies={}, fallback=FallbackConfig()),
    )


class TestCompletions:
    def test_single_mode(self, client, mock_config):
        """single 模式调用单个模型"""
        with patch("smart_router.gateway.playground_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = mock_config
            with patch("smart_router.gateway.playground_api.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Hello, world!"
                mock_response.usage.prompt_tokens = 10
                mock_response.usage.completion_tokens = 5
                mock_response.usage.completion_tokens_details = None
                mock_response.usage.prompt_tokens_details = None
                mock_llm.return_value = mock_response

                response = client.post(
                    "/api/playground/completions",
                    json={"mode": "single", "prompt": "Say hi", "models": ["gpt-4o"], "stream": False},
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data["results"]) == 1
                result = data["results"][0]
                assert result["model"] == "gpt-4o"
                assert result["response"] == "Hello, world!"
                assert result["error"] is None
                # cost = 10/1000 * 0.005 + 5/1000 * 0.015 = 0.00005 + 0.000075 = 0.000125
                assert result["estimated_cost"] == 0.000125
                assert "routing_info" in result

    def test_compare_mode(self, client, mock_config):
        """compare 模式并发调用多个模型"""
        with patch("smart_router.gateway.playground_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = mock_config
            with patch("smart_router.gateway.playground_api.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
                async def side_effect(*args, **kwargs):
                    model = kwargs.get("model", "")
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    if "gpt-4o" in model:
                        mock_response.choices[0].message.content = "GPT-4o response"
                        mock_response.usage.prompt_tokens = 10
                        mock_response.usage.completion_tokens = 5
                    else:
                        mock_response.choices[0].message.content = "Claude response"
                        mock_response.usage.prompt_tokens = 8
                        mock_response.usage.completion_tokens = 4
                    mock_response.usage.completion_tokens_details = None
                    mock_response.usage.prompt_tokens_details = None
                    return mock_response

                mock_llm.side_effect = side_effect

                response = client.post(
                    "/api/playground/completions",
                    json={"mode": "compare", "prompt": "Say hi", "models": ["gpt-4o", "claude-3"], "stream": False},
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data["results"]) == 2

                models = [r["model"] for r in data["results"]]
                assert "gpt-4o" in models
                assert "claude-3" in models

                for r in data["results"]:
                    assert r["error"] is None
                    assert "routing_info" in r

    def test_timeout(self, client, mock_config):
        """超时返回错误信息"""
        with patch("smart_router.gateway.playground_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = mock_config
            with patch("smart_router.gateway.playground_api.asyncio.wait_for") as mock_wait:
                mock_wait.side_effect = asyncio.TimeoutError()

                response = client.post(
                    "/api/playground/completions",
                    json={"mode": "single", "prompt": "Say hi", "models": ["gpt-4o"]},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["results"][0]["error"] == "请求超时"

    def test_api_error(self, client, mock_config):
        """API 错误返回状态码和错误信息"""
        with patch("smart_router.gateway.playground_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = mock_config
            with patch("smart_router.gateway.playground_api.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
                class FakeError(Exception):
                    status_code = 429
                    def __str__(self):
                        return "Rate limit exceeded"

                mock_llm.side_effect = FakeError()

                response = client.post(
                    "/api/playground/completions",
                    json={"mode": "single", "prompt": "Say hi", "models": ["gpt-4o"]},
                )
                assert response.status_code == 200
                data = response.json()
                assert "429" in data["results"][0]["error"]
                assert "Rate limit exceeded" in data["results"][0]["error"]

    def test_unknown_model(self, client, mock_config):
        """未知模型返回 400"""
        with patch("smart_router.gateway.playground_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = mock_config

            response = client.post(
                "/api/playground/completions",
                json={"mode": "single", "prompt": "Say hi", "models": ["unknown-model"]},
            )
            assert response.status_code == 400


class TestHistory:
    def test_get_history_empty(self, client):
        """空历史记录"""
        with patch("smart_router.gateway.playground_api.HISTORY_FILE", Path("/tmp/nonexistent_playground_history.json")):
            response = client.get("/api/playground/history")
            assert response.status_code == 200
            assert response.json() == {"history": []}

    def test_history_crud(self, client, mock_config, tmp_path):
        """历史记录的增删查"""
        history_file = tmp_path / "playground_history.json"

        # 先创建一个记录
        record = {
            "id": "test-id-123",
            "mode": "single",
            "prompt": "Hello",
            "models": ["gpt-4o"],
            "results": [],
            "created_at": 1234567890,
        }
        history_file.write_text(json.dumps([record]), encoding="utf-8")

        with patch("smart_router.gateway.playground_api.HISTORY_FILE", history_file):
            # 查询
            response = client.get("/api/playground/history")
            assert response.status_code == 200
            data = response.json()
            assert len(data["history"]) == 1
            assert data["history"][0]["id"] == "test-id-123"

            # 删除
            response = client.delete("/api/playground/history/test-id-123")
            assert response.status_code == 200
            assert response.json()["success"] is True

            # 再次查询
            response = client.get("/api/playground/history")
            assert response.status_code == 200
            assert response.json() == {"history": []}

    def test_completions_saves_history(self, client, mock_config, tmp_path):
        """completions 调用后应保存历史记录"""
        history_file = tmp_path / "playground_history.json"

        with patch("smart_router.gateway.playground_api.HISTORY_FILE", history_file):
            with patch("smart_router.gateway.playground_api.ConfigLoader") as mock_loader:
                mock_loader.return_value.load.return_value = mock_config
                with patch("smart_router.gateway.playground_api.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    mock_response.choices[0].message.content = "Hi!"
                    mock_response.usage.prompt_tokens = 2
                    mock_response.usage.completion_tokens = 1
                    mock_response.usage.completion_tokens_details = None
                    mock_response.usage.prompt_tokens_details = None
                    mock_llm.return_value = mock_response

                    response = client.post(
                        "/api/playground/completions",
                        json={"mode": "single", "prompt": "Hello", "models": ["gpt-4o"]},
                    )
                    assert response.status_code == 200

                    # 验证历史记录文件
                    assert history_file.exists()
                    data = json.loads(history_file.read_text(encoding="utf-8"))
                    assert len(data) == 1
                    assert data[0]["mode"] == "single"
                    assert data[0]["prompt"] == "Hello"
                    assert data[0]["models"] == ["gpt-4o"]
