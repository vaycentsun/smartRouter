"""Analytics API 测试 — 覆盖汇总、每日趋势、按模型聚合、TOP10"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from smart_router.gateway.dashboard_api import build_dashboard_app
from smart_router.utils.token_stats import TokenStats
from smart_router.config.schema import Config, ProviderConfig, ModelConfig, ModelCapabilities, ModelPrice, RoutingConfig, FallbackConfig


@pytest.fixture
def client():
    app = build_dashboard_app(static_dir=None)
    return TestClient(app)


class TestAnalyticsSummary:
    def test_summary_empty(self, client):
        """空数据返回零值"""
        response = client.get("/api/analytics/summary?days=7")
        assert response.status_code == 200
        data = response.json()
        assert data["total_cost"] == 0.0
        assert data["total_requests"] == 0
        assert data["total_prompt_tokens"] == 0
        assert data["total_completion_tokens"] == 0

    def test_summary_with_data(self, client, tmp_path, monkeypatch):
        """有数据时正确计算汇总"""
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        # 准备 config mock（带 price）
        mock_config = Config(
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
                    price=ModelPrice(prompt_per_1k=0.005, completion_per_1k=0.015, currency="USD")
                ),
            },
            routing=RoutingConfig(tasks={}, difficulties={}, strategies={}, fallback=FallbackConfig())
        )

        # 写入 3 天的数据
        import time
        for i in range(3):
            date_str = f"2024-01-{10 + i:02d}"
            monkeypatch.setattr(time, "strftime", lambda fmt, t=None, d=date_str: d)
            # 使用内部 async 辅助直接写入
            import asyncio
            asyncio.run(ts.record("gpt-4o", 1000, 500, 1500))

        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = mock_config

            with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
                MockStats.return_value = ts
                response = client.get("/api/analytics/summary?days=7")
                assert response.status_code == 200
                data = response.json()
                # cost = (3000/1000 * 0.005) + (1500/1000 * 0.015) = 0.015 + 0.0225 = 0.0375
                assert data["total_cost"] == 0.0375
                assert data["total_requests"] == 3
                assert data["total_prompt_tokens"] == 3000
                assert data["total_completion_tokens"] == 1500
                assert data["incomplete"] is False

    def test_summary_incomplete_without_price(self, client, tmp_path, monkeypatch):
        """无单价的模型应标记 incomplete"""
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        mock_config = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                    # 无 price
                ),
            },
            routing=RoutingConfig(tasks={}, difficulties={}, strategies={}, fallback=FallbackConfig())
        )

        import time, asyncio
        monkeypatch.setattr(time, "strftime", lambda fmt, t=None: "2024-01-15")
        asyncio.run(ts.record("gpt-4o", 1000, 500, 1500))

        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = mock_config
            with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
                MockStats.return_value = ts
                response = client.get("/api/analytics/summary?days=7")
                assert response.status_code == 200
                data = response.json()
                assert data["total_cost"] == 0.0
                assert data["incomplete"] is True

    def test_summary_days_max_90(self, client):
        """days 超过 90 应被限制"""
        response = client.get("/api/analytics/summary?days=100")
        assert response.status_code == 200
        # 应该按 90 处理，空数据返回 0
        data = response.json()
        assert data["total_requests"] == 0


class TestAnalyticsDaily:
    def test_daily_empty(self, client):
        response = client.get("/api/analytics/daily?days=7")
        assert response.status_code == 200
        assert response.json() == {}

    def test_daily_with_data(self, client, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        import asyncio
        from datetime import datetime, timedelta
        # 使用相对于今天的日期，确保在 days=7 范围内
        base = datetime.utcnow()
        dates = []
        for i in range(3):
            date_obj = base - timedelta(days=i)
            date_str = date_obj.strftime("%Y-%m-%d")
            dates.append(date_str)
            asyncio.run(ts.record("gpt-4o", 100 * (i + 1), 50 * (i + 1), 150 * (i + 1), date=date_str))

        with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
            MockStats.return_value = ts
            response = client.get("/api/analytics/daily?days=7")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            for d in dates:
                assert d in data
            assert data[dates[0]]["gpt-4o"]["prompt_tokens"] == 100


class TestAnalyticsByModel:
    def test_by_model_empty(self, client):
        response = client.get("/api/analytics/by-model?days=7")
        assert response.status_code == 200
        assert response.json() == {}

    def test_by_model_with_data(self, client, tmp_path, monkeypatch):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        mock_config = Config(
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
                    price=ModelPrice(prompt_per_1k=0.005, completion_per_1k=0.015, currency="USD")
                ),
            },
            routing=RoutingConfig(tasks={}, difficulties={}, strategies={}, fallback=FallbackConfig())
        )

        import time, asyncio
        monkeypatch.setattr(time, "strftime", lambda fmt, t=None: "2024-01-15")
        asyncio.run(ts.record("gpt-4o", 2000, 1000, 3000))

        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = mock_config
            with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
                MockStats.return_value = ts
                response = client.get("/api/analytics/by-model?days=7")
                assert response.status_code == 200
                data = response.json()
                assert "gpt-4o" in data
                assert data["gpt-4o"]["cost"] == (2000 / 1000 * 0.005 + 1000 / 1000 * 0.015)
                assert data["gpt-4o"]["request_count"] == 1


class TestAnalyticsTopModels:
    def test_top_models_empty(self, client):
        response = client.get("/api/analytics/top-models?limit=10&days=7")
        assert response.status_code == 200
        assert response.json() == []

    def test_top_models_with_data(self, client, tmp_path, monkeypatch):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        mock_config = Config(
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
                    price=ModelPrice(prompt_per_1k=0.005, completion_per_1k=0.015, currency="USD")
                ),
                "claude-3": ModelConfig(
                    provider="openai",
                    litellm_model="openai/claude-3",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"],
                    price=ModelPrice(prompt_per_1k=0.003, completion_per_1k=0.015, currency="USD")
                ),
            },
            routing=RoutingConfig(tasks={}, difficulties={}, strategies={}, fallback=FallbackConfig())
        )

        import time, asyncio
        monkeypatch.setattr(time, "strftime", lambda fmt, t=None: "2024-01-15")
        # claude-3 有 2 次请求，gpt-4o 有 1 次，确保排序确定
        asyncio.run(ts.record("gpt-4o", 1000, 500, 1500))
        asyncio.run(ts.record("claude-3", 2000, 1000, 3000))
        asyncio.run(ts.record("claude-3", 500, 250, 750))

        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = mock_config
            with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
                MockStats.return_value = ts
                response = client.get("/api/analytics/top-models?limit=10&days=7")
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                # 按 request_count 降序
                assert data[0]["model"] == "claude-3"
                assert data[0]["request_count"] == 2
                assert data[1]["model"] == "gpt-4o"
                assert data[1]["request_count"] == 1

    def test_top_models_respects_limit(self, client, tmp_path, monkeypatch):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        mock_config = Config(
            providers={
                "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")
            },
            models={
                "model-a": ModelConfig(
                    provider="openai", litellm_model="openai/a",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"], difficulty_support=["easy"],
                    price=ModelPrice(prompt_per_1k=0.001, completion_per_1k=0.001, currency="USD")
                ),
                "model-b": ModelConfig(
                    provider="openai", litellm_model="openai/b",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"], difficulty_support=["easy"],
                    price=ModelPrice(prompt_per_1k=0.001, completion_per_1k=0.001, currency="USD")
                ),
            },
            routing=RoutingConfig(tasks={}, difficulties={}, strategies={}, fallback=FallbackConfig())
        )

        import time, asyncio
        monkeypatch.setattr(time, "strftime", lambda fmt, t=None: "2024-01-15")
        # model-b 有 2 次请求，model-a 有 1 次，确保排序和 limit 测试稳定
        asyncio.run(ts.record("model-a", 100, 50, 150))
        asyncio.run(ts.record("model-b", 200, 100, 300))
        asyncio.run(ts.record("model-b", 50, 25, 75))

        with patch("smart_router.gateway.dashboard_api.ConfigLoader") as mock_loader:
            mock_loader.return_value.load.return_value = mock_config
            with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
                MockStats.return_value = ts
                response = client.get("/api/analytics/top-models?limit=1&days=7")
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["model"] == "model-b"
                assert data[0]["request_count"] == 2
