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


import json
from unittest.mock import patch
from smart_router.utils.token_stats import TokenStats as RealTokenStats


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
