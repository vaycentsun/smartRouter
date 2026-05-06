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
        with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
            mock_instance = MagicMock()
            mock_instance.get_all.return_value = {}
            MockStats.return_value = mock_instance

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


class TestProviderHealthAPI:
    """Provider 健康检查 API 测试"""

    def test_provider_health_unknown_provider(self, client):
        """不存在的 provider 返回 404"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            mock_cfg.providers = {"openai": MagicMock()}
            mock_cfg.models = {}
            mock_loader.return_value.load.return_value = mock_cfg
            # 确保 health_checker 已初始化，避免 500
            client.app.state.health_checker = MagicMock()

            response = client.get("/api/providers/nonexistent/health")
            assert response.status_code == 404

    def test_provider_models_unknown_provider(self, client):
        """不存在的 provider 返回 404"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            mock_cfg.providers = {"openai": MagicMock()}
            mock_cfg.models = {}
            mock_loader.return_value.load.return_value = mock_cfg
            # 确保 health_checker 已初始化，避免 500
            client.app.state.health_checker = MagicMock()

            response = client.get("/api/providers/nonexistent/models")
            assert response.status_code == 404

    def test_provider_models_no_cache(self, client):
        """未检查时返回空状态"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            mock_cfg.providers = {"openai": MagicMock()}
            mock_cfg.models = {}
            mock_loader.return_value.load.return_value = mock_cfg
            # 确保 health_checker 已初始化，避免 500
            client.app.state.health_checker = MagicMock()
            client.app.state.health_checker.get_cached.return_value = None

            response = client.get("/api/providers/openai/models")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] is None
            assert data["provider_models"] == []

    def test_provider_health_unconfigured(self, client):
        """未配置 Key 的 provider 返回 unconfigured"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            provider = MagicMock()
            provider.api_key = ""
            provider.api_base = "https://api.openai.com/v1"
            mock_cfg.providers = {"openai": provider}
            mock_cfg.models = {}
            mock_loader.return_value.load.return_value = mock_cfg

            # 使用 mock 的 health_checker 确保测试隔离
            from smart_router.utils.health_checker import ProviderHealthChecker
            checker = ProviderHealthChecker(mock_cfg)

            with patch.object(client.app.state, "health_checker", checker):
                response = client.get("/api/providers/openai/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "unconfigured"
                assert "未配置" in data["error"]

    def test_providers_with_health_cache(self, client):
        """/api/providers 返回包含缓存的健康状态"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            provider = MagicMock()
            provider.api_key = "sk-test"
            provider.api_base = "https://api.openai.com/v1"
            provider.timeout = 30
            mock_cfg.providers = {"openai": provider}
            mock_cfg.models = {}
            mock_loader.return_value.load.return_value = mock_cfg

            # 先触发健康检查写入缓存
            from smart_router.utils.health_checker import ProviderHealthChecker
            checker = ProviderHealthChecker(mock_cfg)
            checker._cache["openai"] = MagicMock(
                status="healthy",
                checked_at=1714972800.0,
                models=["gpt-4o"],
                error=None,
            )

            with patch.object(client.app.state, "health_checker", checker):
                response = client.get("/api/providers")
                assert response.status_code == 200
                data = response.json()
                assert len(data["providers"]) == 1
                assert data["providers"][0]["health"]["status"] == "healthy"
                assert data["providers"][0]["health"]["checked_at"] == 1714972800.0

    def test_models_with_health_status(self, client):
        """/api/models 返回包含 health_status"""
        from smart_router.config.schema import ModelConfig, ModelCapabilities

        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            provider = MagicMock()
            provider.api_key = "sk-test"
            provider.api_base = "https://api.openai.com/v1"
            provider.timeout = 30
            mock_cfg.providers = {"openai": provider}

            model = MagicMock()
            model.provider = "openai"
            model.litellm_model = "openai/gpt-4o"
            model.capabilities = MagicMock(
                quality=9, cost=3, context=128000
            )
            model.supported_tasks = ["coding"]
            mock_cfg.models = {"gpt-4o": model}
            mock_cfg.is_model_available.return_value = True
            mock_loader.return_value.load.return_value = mock_cfg

            # 设置健康检查缓存：healthy，且模型在列表中
            from smart_router.utils.health_checker import ProviderHealthChecker
            checker = ProviderHealthChecker(mock_cfg)
            checker._cache["openai"] = MagicMock(
                status="healthy",
                checked_at=1714972800.0,
                models=["gpt-4o"],
                error=None,
            )

            with patch.object(client.app.state, "health_checker", checker):
                response = client.get("/api/models")
                assert response.status_code == 200
                data = response.json()
                assert len(data["models"]) == 1
                assert data["models"][0]["health_status"] == "available"

    def test_models_with_not_found_status(self, client):
        """Provider healthy 但模型不在列表中时返回 not_found"""
        from smart_router.config.schema import ModelConfig, ModelCapabilities

        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            provider = MagicMock()
            provider.api_key = "sk-test"
            provider.api_base = "https://api.openai.com/v1"
            provider.timeout = 30
            mock_cfg.providers = {"openai": provider}

            model = MagicMock()
            model.provider = "openai"
            model.litellm_model = "openai/gpt-4o"
            model.capabilities = MagicMock(
                quality=9, cost=3, context=128000
            )
            model.supported_tasks = ["coding"]
            mock_cfg.models = {"gpt-4o": model}
            mock_cfg.is_model_available.return_value = True
            mock_loader.return_value.load.return_value = mock_cfg

            # 设置健康检查缓存：healthy，但模型不在列表中
            from smart_router.utils.health_checker import ProviderHealthChecker
            checker = ProviderHealthChecker(mock_cfg)
            checker._cache["openai"] = MagicMock(
                status="healthy",
                checked_at=1714972800.0,
                models=["gpt-3.5-turbo"],  # 不匹配
                error=None,
            )

            with patch.object(client.app.state, "health_checker", checker):
                response = client.get("/api/models")
                assert response.status_code == 200
                data = response.json()
                assert data["models"][0]["health_status"] == "not_found"

    def test_models_with_auth_error_status(self, client):
        """Provider auth_error 时模型状态同步"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            provider = MagicMock()
            provider.api_key = "sk-test"
            provider.api_base = "https://api.openai.com/v1"
            provider.timeout = 30
            mock_cfg.providers = {"openai": provider}

            model = MagicMock()
            model.provider = "openai"
            model.litellm_model = "openai/gpt-4o"
            model.capabilities = MagicMock(
                quality=9, cost=3, context=128000
            )
            model.supported_tasks = ["coding"]
            mock_cfg.models = {"gpt-4o": model}
            mock_cfg.is_model_available.return_value = True
            mock_loader.return_value.load.return_value = mock_cfg

            # 设置健康检查缓存：auth_error
            from smart_router.utils.health_checker import ProviderHealthChecker
            checker = ProviderHealthChecker(mock_cfg)
            checker._cache["openai"] = MagicMock(
                status="auth_error",
                checked_at=1714972800.0,
                models=[],
                error="HTTP 401",
            )

            with patch.object(client.app.state, "health_checker", checker):
                response = client.get("/api/models")
                assert response.status_code == 200
                data = response.json()
                assert data["models"][0]["health_status"] == "auth_error"

    def test_provider_health_does_not_trigger_write(self, client, tmp_path):
        """检查连通性不再自动写入 models/{name}.yaml"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            provider = MagicMock()
            provider.api_key = "sk-test"
            provider.api_base = "https://api.openai.com/v1"
            provider.timeout = 30
            mock_cfg.providers = {"openai": provider}
            mock_cfg.models = {}
            mock_loader.return_value.load.return_value = mock_cfg

            from smart_router.utils.health_checker import ProviderHealthChecker
            checker = ProviderHealthChecker(mock_cfg)

            with patch.object(checker, "check") as mock_check, \
                 patch.object(checker, "write_discovered_models") as mock_write:
                mock_check.return_value = MagicMock(
                    status="healthy",
                    checked_at=1714972800.0,
                    models=["gpt-4o"],
                    error=None,
                )

                with patch.object(client.app.state, "health_checker", checker):
                    response = client.get("/api/providers/openai/health")
                    assert response.status_code == 200
                    mock_write.assert_not_called()

    def test_provider_health_uses_latest_config(self, client):
        """health_checker 持有旧配置时，API 应使用最新加载的配置"""
        from smart_router.utils.health_checker import ProviderHealthChecker

        # 1. 模拟启动时的旧配置（api_key 为空）
        old_cfg = MagicMock()
        old_provider = MagicMock()
        old_provider.api_key = ""
        old_provider.api_base = "https://api.openai.com/v1"
        old_cfg.providers = {"openai": old_provider}
        old_cfg.models = {}

        checker = ProviderHealthChecker(old_cfg)

        # 2. 模拟用户更新后的新配置（api_key 已设置）
        new_cfg = MagicMock()
        new_provider = MagicMock()
        new_provider.api_key = "sk-new-key"
        new_provider.api_base = "https://api.openai.com/v1"
        new_cfg.providers = {"openai": new_provider}
        new_cfg.models = {}

        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = new_cfg

            with patch.object(checker, "check") as mock_check:
                mock_check.return_value = MagicMock(
                    status="healthy",
                    checked_at=1714972800.0,
                    models=["gpt-4o"],
                    error=None,
                )

                with patch.object(client.app.state, "health_checker", checker):
                    response = client.get("/api/providers/openai/health")
                    assert response.status_code == 200
                    # 关键断言：checker.config 被更新为新配置
                    assert checker.config is new_cfg
                    # 由于 config 已更新，check 被调用时使用的是新配置
                    mock_check.assert_called_once_with("openai", force=True)
