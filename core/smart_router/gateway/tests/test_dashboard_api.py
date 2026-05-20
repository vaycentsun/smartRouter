"""dashboard_api 模块单元测试"""

import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from smart_router.gateway.dashboard_api import build_dashboard_app


@pytest.fixture
def client(tmp_path):
    from unittest.mock import patch
    import smart_router.utils.request_routing_history as rrh
    # 使用临时文件隔离测试状态，避免历史记录跨测试泄漏
    temp_history = tmp_path / "request_routing_history.json"
    with patch.object(rrh, "DEFAULT_HISTORY_FILE", temp_history):
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

    def test_dry_run_returns_fallback_chain(self, client):
        """dry-run 成功时应返回选中模型的 fallback 链"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            from smart_router.config.schema import Config, ProviderConfig, ModelConfig, ModelCapabilities
            from smart_router.config.schema import RoutingConfig, TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig

            cfg = Config(
                providers={
                    "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test"),
                    "anthropic": ProviderConfig(api_base="https://api.anthropic.com/v1", api_key="sk-test"),
                },
                models={
                    "gpt-4o": ModelConfig(
                        provider="openai",
                        litellm_model="openai/gpt-4o",
                        capabilities=ModelCapabilities(quality=10, cost=3, context=128000),
                        supported_tasks=["chat"],
                        difficulty_support=["easy", "medium", "hard"],
                    ),
                    "claude-3-opus": ModelConfig(
                        provider="anthropic",
                        litellm_model="anthropic/claude-3-opus",
                        capabilities=ModelCapabilities(quality=10, cost=2, context=200000),
                        supported_tasks=["chat"],
                        difficulty_support=["easy", "medium", "hard"],
                    ),
                },
                routing=RoutingConfig(
                    tasks={"chat": TaskConfig(name="聊天", description="日常对话", capability_weights={"quality": 0.5, "cost": 0.5})},
                    difficulties={"easy": DifficultyConfig(description="简单", max_tokens=2000)},
                    strategies={"auto": StrategyConfig(description="自动")},
                    fallback=FallbackConfig(mode="auto", similarity_threshold=2),
                ),
            )
            mock_loader.return_value.load.return_value = cfg

            response = client.post("/api/dry-run", json={"prompt": "hello", "strategy": "cost"})
            assert response.status_code == 200
            data = response.json()
            assert "error" not in data
            assert "fallback_chain" in data
            # gpt-4o (quality=10) 和 claude-3-opus (quality=10) 差异为 0 <= 2，应在 fallback 链中
            assert "claude-3-opus" in data["fallback_chain"]


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
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data


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
            assert data["total_reasoning_tokens"] == 0
            assert data["total_cached_tokens"] == 0
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


class TestAddModel:
    """测试 POST /api/providers/{provider_name}/models"""

    def test_add_model_success(self, client):
        """正常添加 model，返回 200 和 model 信息"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_instance = MagicMock()
            mock_loader.return_value = mock_instance

            response = client.post("/api/providers/openai/models", json={
                "name": "gpt-4o-new",
                "litellm_model": "openai/gpt-4o-new",
                "quality": 9,
                "cost": 3,
                "context": 128000,
                "supported_tasks": ["chat", "coding"],
                "enabled": True,
            })
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["model"]["name"] == "gpt-4o-new"
            assert data["model"]["provider"] == "openai"
            assert data["model"]["available"] is True
            assert data["model"]["health_status"] == "unknown"
            assert data["model"]["quality"] == 9
            assert data["model"]["cost"] == 3
            assert data["model"]["context"] == 128000
            assert data["model"]["supported_tasks"] == ["chat", "coding"]
            assert data["model"]["enabled"] is True
            mock_instance.add_model.assert_called_once_with(
                provider_name="openai",
                name="gpt-4o-new",
                litellm_model="openai/gpt-4o-new",
                quality=9,
                cost=3,
                context=128000,
                supported_tasks=["chat", "coding"],
                enabled=True,
            )

    def test_add_model_provider_not_found(self, client):
        """provider 不存在，返回 404"""
        from smart_router.config.loader import ConfigError
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_instance = MagicMock()
            mock_instance.add_model.side_effect = ConfigError("Provider 'unknown' not found")
            mock_loader.return_value = mock_instance

            response = client.post("/api/providers/unknown/models", json={
                "name": "gpt-4o",
                "litellm_model": "openai/gpt-4o",
                "quality": 9,
                "cost": 3,
                "context": 128000,
                "supported_tasks": ["chat"],
            })
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_add_model_name_exists(self, client):
        """model name 已存在，返回 400"""
        from smart_router.config.loader import ConfigError
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_instance = MagicMock()
            mock_instance.add_model.side_effect = ConfigError("Model 'gpt-4o' already exists")
            mock_loader.return_value = mock_instance

            response = client.post("/api/providers/openai/models", json={
                "name": "gpt-4o",
                "litellm_model": "openai/gpt-4o",
                "quality": 9,
                "cost": 3,
                "context": 128000,
                "supported_tasks": ["chat"],
            })
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()

    def test_add_model_name_with_space(self, client):
        """name 含空格，返回 400"""
        from smart_router.config.loader import ConfigError
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_instance = MagicMock()
            mock_instance.add_model.side_effect = ConfigError("Invalid model name 'bad name'")
            mock_loader.return_value = mock_instance

            response = client.post("/api/providers/openai/models", json={
                "name": "bad name",
                "litellm_model": "openai/gpt-4o",
                "quality": 9,
                "cost": 3,
                "context": 128000,
                "supported_tasks": ["chat"],
            })
            assert response.status_code == 400
            assert "Invalid" in response.json()["detail"]

    def test_add_model_missing_litellm_model(self, client):
        """缺少必填字段 litellm_model，返回 422"""
        response = client.post("/api/providers/openai/models", json={
            "name": "gpt-4o",
            "quality": 9,
            "cost": 3,
            "context": 128000,
            "supported_tasks": ["chat"],
        })
        assert response.status_code == 422

    def test_add_model_validate_failure_rollback(self, client):
        """写入后若 validate 失败（模拟），返回 500"""
        from smart_router.config.loader import ConfigError
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_instance = MagicMock()
            mock_instance.add_model.side_effect = ConfigError(
                "Config validation failed after save"
            )
            mock_loader.return_value = mock_instance

            response = client.post("/api/providers/openai/models", json={
                "name": "rollback-model",
                "litellm_model": "openai/gpt-4o",
                "quality": 9,
                "cost": 3,
                "context": 128000,
                "supported_tasks": ["chat"],
            })
            assert response.status_code == 500
            assert "validation failed" in response.json()["detail"].lower()


class TestCreateProvider:
    """测试 POST /api/providers"""

    def test_create_provider_success(self, client):
        """正常创建 provider，返回 200 和 provider 信息"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_instance = MagicMock()
            mock_loader.return_value = mock_instance

            response = client.post("/api/providers", json={
                "name": "new_provider",
                "api_base": "https://api.test.com/v1",
                "api_key": "sk-secret-key-12345",
                "timeout": 60,
            })
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["provider"]["name"] == "new_provider"
            assert data["provider"]["api_base"] == "https://api.test.com/v1"
            assert data["provider"]["timeout"] == 60
            assert data["provider"]["key_type"] == "direct"
            assert data["provider"]["has_key"] is True
            assert data["provider"]["masked_key"] == "sk-s...2345"
            assert data["provider"]["health"] is None
            mock_instance.create_provider.assert_called_once_with(
                "new_provider", "https://api.test.com/v1", "sk-secret-key-12345", 60
            )

    def test_create_provider_name_exists(self, client):
        """name 已存在，返回 400"""
        from smart_router.config.loader import ConfigError
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_instance = MagicMock()
            mock_instance.create_provider.side_effect = ConfigError("Provider 'existing' already exists")
            mock_loader.return_value = mock_instance

            response = client.post("/api/providers", json={
                "name": "existing",
                "api_base": "https://api.test.com/v1",
                "api_key": "sk-test",
            })
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]

    def test_create_provider_name_with_space(self, client):
        """name 含空格，返回 400"""
        from smart_router.config.loader import ConfigError
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_instance = MagicMock()
            mock_instance.create_provider.side_effect = ConfigError("Invalid provider name")
            mock_loader.return_value = mock_instance

            response = client.post("/api/providers", json={
                "name": "bad name",
                "api_base": "https://api.test.com/v1",
                "api_key": "sk-test",
            })
            assert response.status_code == 400
            assert "Invalid" in response.json()["detail"]

    def test_create_provider_missing_name(self, client):
        """缺少必填字段 name，返回 422"""
        response = client.post("/api/providers", json={
            "api_base": "https://api.test.com/v1",
            "api_key": "sk-test",
        })
        assert response.status_code == 422

    def test_create_provider_validate_failure_rollback(self, client):
        """创建后若 validate 失败（模拟），返回 500，原配置不变"""
        from smart_router.config.loader import ConfigError
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_instance = MagicMock()
            mock_instance.create_provider.side_effect = ConfigError(
                "Config validation failed after save"
            )
            mock_loader.return_value = mock_instance

            response = client.post("/api/providers", json={
                "name": "rollback_provider",
                "api_base": "https://api.test.com/v1",
                "api_key": "sk-test",
            })
            assert response.status_code == 500
            assert "validation failed" in response.json()["detail"]


class TestToggleModel:
    """测试 PUT /api/models/{provider}/{model}"""

    def test_toggle_model_success(self, client, tmp_path):
        """成功切换模型状态"""
        from smart_router.config.loader import ConfigLoader

        # 创建临时配置目录
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
  _virtual:
    api_base: ""
    api_key: ""
    timeout: 30
""")
        (config_dir / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = config_dir / "models"
        models_dir.mkdir()
        (models_dir / "openai.yaml").write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.side_effect = lambda path: ConfigLoader(config_dir)
            mock_loader.return_value = ConfigLoader(config_dir)

            response = client.put("/api/models/openai/gpt-4o", json={"enabled": False})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["provider"] == "openai"
            assert data["model"] == "gpt-4o"
            assert data["enabled"] is False

    def test_toggle_model_provider_not_found(self, client):
        """Provider 不存在返回 404"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            mock_cfg.providers = {}
            mock_cfg.models = {}
            mock_loader.return_value.load.return_value = mock_cfg

            response = client.put("/api/models/unknown/gpt-4o", json={"enabled": False})
            assert response.status_code == 404
            assert "Provider not found" in response.json()["detail"]

    def test_toggle_model_model_not_found(self, client):
        """Model 不存在返回 404"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            provider = MagicMock()
            mock_cfg.providers = {"openai": provider}
            mock_cfg.models = {}
            mock_loader.return_value.load.return_value = mock_cfg

            response = client.put("/api/models/openai/unknown", json={"enabled": False})
            assert response.status_code == 404
            assert "Model not found" in response.json()["detail"]

    def test_toggle_model_wrong_provider(self, client):
        """Model 不属于该 Provider 返回 404"""
        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_cfg = MagicMock()
            provider = MagicMock()
            mock_cfg.providers = {"openai": provider, "anthropic": provider}
            model = MagicMock()
            model.provider = "anthropic"
            mock_cfg.models = {"claude-3": model}
            mock_loader.return_value.load.return_value = mock_cfg

            response = client.put("/api/models/openai/claude-3", json={"enabled": False})
            assert response.status_code == 404
            assert "does not belong to provider" in response.json()["detail"]

    def test_models_returns_enabled(self, client):
        """GET /api/models 返回包含 enabled 字段"""
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
            model.enabled = False
            mock_cfg.models = {"gpt-4o": model}
            mock_cfg.is_model_available.return_value = True
            mock_loader.return_value.load.return_value = mock_cfg

            response = client.get("/api/models")
            assert response.status_code == 200
            data = response.json()
            assert len(data["models"]) == 1
            assert data["models"][0]["enabled"] is False
