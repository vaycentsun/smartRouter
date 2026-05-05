"""dashboard_api 模块单元测试"""

import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from smart_router.gateway.dashboard_api import build_dashboard_app


@pytest.fixture
def client():
    """构建 TestClient，不挂载静态文件"""
    app = build_dashboard_app(static_dir=None)
    return TestClient(app)


class TestHealth:
    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestStatus:
    def test_status_not_running(self, client):
        with patch("smart_router.gateway.dashboard_api._get_pid", return_value=None):
            response = client.get("/api/status")
            assert response.status_code == 200
            data = response.json()
            assert data["running"] is False
            assert data["pid"] is None

    def test_status_running(self, client):
        with patch("smart_router.gateway.dashboard_api._get_pid", return_value=12345), \
             patch("smart_router.gateway.dashboard_api._is_process_running", return_value=True), \
             patch("smart_router.gateway.dashboard_api.get_start_time", return_value=1000.0), \
             patch("time.time", return_value=1100.0):
            response = client.get("/api/status")
            assert response.status_code == 200
            data = response.json()
            assert data["running"] is True
            assert data["pid"] == 12345
            assert data["uptime_seconds"] == 100


class TestModels:
    def test_models_empty_config(self, client):
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.side_effect = Exception("no config")
            response = client.get("/api/models")
            assert response.status_code == 200
            data = response.json()
            assert data["models"] == []
            assert data["total"] == 0


class TestProviders:
    def test_providers_empty_config(self, client):
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.side_effect = Exception("no config")
            response = client.get("/api/providers")
            assert response.status_code == 200
            data = response.json()
            assert data["providers"] == []


class TestModelOverrides:
    def test_model_overrides_empty_config(self, client):
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.side_effect = Exception("no config")
            response = client.get("/api/model-overrides")
            assert response.status_code == 200
            data = response.json()
            assert data["overrides"] == {}


class TestDryRun:
    def test_dry_run_no_config(self, client):
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.side_effect = Exception("no config")
            response = client.post("/api/dry-run", json={"prompt": "hello"})
            assert response.status_code == 200
            data = response.json()
            assert "error" in data


class TestStop:
    def test_stop(self, client):
        with patch("smart_router.gateway.dashboard_api.stop_daemon") as mock_stop:
            response = client.post("/api/stop")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_stop.assert_called_once()


class TestUpdateProviders:
    def test_update_provider_not_found(self, client):
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_instance = MagicMock()
            mock_instance._load_yaml.return_value = {"providers": {}}
            mock_loader.return_value = mock_instance
            response = client.put("/api/providers", json={"providers": {"unknown": {"api_base": "http://test"}}})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


class TestStaticFiles:
    def test_static_without_static_dir(self, client):
        response = client.get("/some-random-path")
        assert response.status_code == 404

    def test_static_with_static_dir(self, tmp_path):
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        index = static_dir / "index.html"
        index.write_text("<html>test</html>")

        app = build_dashboard_app(static_dir=static_dir)
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "test" in response.text

    def test_static_api_still_works_with_static_dir(self, tmp_path):
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<html>test</html>")

        app = build_dashboard_app(static_dir=static_dir)
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_spa_fallback_to_index(self, tmp_path):
        """访问不存在的无扩展名路径应回退到 index.html（SPA 刷新支持）"""
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<html>spa</html>")

        app = build_dashboard_app(static_dir=static_dir)
        client = TestClient(app)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "spa" in response.text

    def test_spa_fallback_404_for_files(self, tmp_path):
        """访问不存在的带扩展名路径不应回退，应返回 404"""
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<html>spa</html>")

        app = build_dashboard_app(static_dir=static_dir)
        client = TestClient(app)
        response = client.get("/missing.js")
        assert response.status_code == 404


import json
from unittest.mock import patch
from smart_router.utils.token_stats import TokenStats as RealTokenStats


class TestModelOverrideAPI:
    def test_get_model_override_initial(self, client):
        response = client.get("/api/model-override")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["provider"] is None
        assert data["model"] is None

    def test_set_and_get_model_override(self, client):
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            mock_cfg.models = {
                "gui-plus-2026-02-26": MagicMock(provider="aliyun"),
            }
            mock_cfg.is_model_available.return_value = True
            mock_loader.return_value.load.return_value = mock_cfg

            response = client.post("/api/model-override", json={"provider": "aliyun", "model": "gui-plus-2026-02-26"})
            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is True
            assert data["provider"] == "aliyun"
            assert data["model"] == "gui-plus-2026-02-26"

            response = client.get("/api/model-override")
            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is True
            assert data["provider"] == "aliyun"
            assert data["model"] == "gui-plus-2026-02-26"

    def test_set_model_override_unknown_model(self, client):
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            mock_cfg.models = {}
            mock_loader.return_value.load.return_value = mock_cfg

            response = client.post("/api/model-override", json={"provider": "aliyun", "model": "unknown"})
            assert response.status_code == 400
            assert "未知模型" in response.json()["detail"]

    def test_set_model_override_provider_mismatch(self, client):
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            mock_cfg.models = {
                "gui-plus-2026-02-26": MagicMock(provider="aliyun"),
            }
            mock_loader.return_value.load.return_value = mock_cfg

            response = client.post("/api/model-override", json={"provider": "openai", "model": "gui-plus-2026-02-26"})
            assert response.status_code == 400
            assert "Provider 不匹配" in response.json()["detail"]

    def test_delete_model_override(self, client):
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            mock_cfg.models = {
                "gui-plus-2026-02-26": MagicMock(provider="aliyun"),
            }
            mock_cfg.is_model_available.return_value = True
            mock_loader.return_value.load.return_value = mock_cfg

            client.post("/api/model-override", json={"provider": "aliyun", "model": "gui-plus-2026-02-26"})

            response = client.delete("/api/model-override")
            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is False
            assert data["provider"] is None
            assert data["model"] is None

            response = client.get("/api/model-override")
            assert response.json()["enabled"] is False


class TestTokenStatsAPI:
    def test_token_stats_empty(self, client):
        response = client.get("/api/token-stats")
        assert response.status_code == 200
        data = response.json()
        assert data["stats"] == []
        assert data["total_prompt_tokens"] == 0
        assert data["total_completion_tokens"] == 0
        assert data["total_requests"] == 0

    def test_token_stats_with_data(self, client, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        stats_data = {
            "version": 1,
            "records": {
                "gpt-4o": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 500,
                    "total_tokens": 1500,
                    "request_count": 10,
                },
                "claude-3-sonnet": {
                    "prompt_tokens": 2000,
                    "completion_tokens": 1000,
                    "total_tokens": 3000,
                    "request_count": 5,
                },
            },
        }
        stats_file.write_text(json.dumps(stats_data))

        with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
            mock_instance = RealTokenStats(stats_file=stats_file)
            MockStats.return_value = mock_instance

            response = client.get("/api/token-stats")
            assert response.status_code == 200
            data = response.json()
            assert len(data["stats"]) == 2
            assert data["total_prompt_tokens"] == 3000
            assert data["total_completion_tokens"] == 1500
            assert data["total_requests"] == 15
