"""Analytics API 测试 — 覆盖汇总、每日趋势、按模型聚合、TOP10、最近请求"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from smart_router.gateway.dashboard_api import build_dashboard_app
from smart_router.utils.token_stats import TokenStats
from smart_router.utils.request_routing_history import RequestRoutingHistory, RequestRoutingEntry
from smart_router.config.schema import Config, ProviderConfig, ModelConfig, ModelCapabilities, ModelPrice, RoutingConfig, FallbackConfig


@pytest.fixture
def client():
    app = build_dashboard_app(static_dir=None)
    return TestClient(app)


class TestAnalyticsSummary:
    def test_summary_empty(self, client):
        """空数据返回零值"""
        mock_ts = MagicMock()
        mock_ts.get_summary.return_value = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_requests": 0,
            "model_breakdown": {},
        }
        with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
            MockStats.return_value = mock_ts
            response = client.get("/api/analytics/summary?days=7")
            assert response.status_code == 200
            data = response.json()
            assert data["total_cost"] == 0.0
            assert data["total_requests"] == 0
            assert data["total_tokens"] == 0
            assert data["avg_daily_cost"] == 0.0

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
                assert data["total_tokens"] == 4500
                assert data["avg_daily_cost"] == 0.0375 / 7
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
        mock_ts = MagicMock()
        mock_ts.get_summary.return_value = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_requests": 0,
            "model_breakdown": {},
        }
        with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
            MockStats.return_value = mock_ts
            response = client.get("/api/analytics/summary?days=100")
            assert response.status_code == 200
            # 应该按 90 处理，空数据返回 0
            data = response.json()
            assert data["total_requests"] == 0


class TestAnalyticsDaily:
    def test_daily_empty(self, client):
        mock_ts = MagicMock()
        mock_ts.get_daily.return_value = {}
        with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
            MockStats.return_value = mock_ts
            response = client.get("/api/analytics/daily?days=7")
            assert response.status_code == 200
            assert response.json() == []

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
            date_set = {item["date"] for item in data}
            for d in dates:
                assert d in date_set
            # 找到今天的数据项
            today_item = next(item for item in data if item["date"] == dates[0])
            assert today_item["requests"] == 1
            assert today_item["tokens"] == 150


class TestAnalyticsByModel:
    def test_by_model_empty(self, client):
        mock_ts = MagicMock()
        mock_ts.get_summary.return_value = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_requests": 0,
            "model_breakdown": {},
        }
        with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
            MockStats.return_value = mock_ts
            response = client.get("/api/analytics/by-model?days=7")
            assert response.status_code == 200
            assert response.json() == []

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
                assert len(data) == 1
                assert data[0]["model"] == "gpt-4o"
                assert data[0]["cost"] == (2000 / 1000 * 0.005 + 1000 / 1000 * 0.015)
                assert data[0]["request_count"] == 1


class TestAnalyticsTopModels:
    def test_top_models_empty(self, client):
        mock_ts = MagicMock()
        mock_ts.get_summary.return_value = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_requests": 0,
            "model_breakdown": {},
        }
        with patch("smart_router.utils.token_stats.TokenStats") as MockStats:
            MockStats.return_value = mock_ts
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


class TestRecentRequests:
    def test_recent_requests_empty(self, client):
        """无历史记录时返回空列表"""
        response = client.get("/api/analytics/recent-requests")
        assert response.status_code == 200
        data = response.json()
        assert data == {"requests": []}

    def test_recent_requests_with_data(self):
        """预置记录时返回正确格式和字段"""
        import asyncio

        # Python 3.9 下 asyncio.Lock() 需要当前线程存在 event loop
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        app = build_dashboard_app(static_dir=None)
        history = RequestRoutingHistory(max_size=50)
        entry = RequestRoutingEntry(
            request_id="abc123",
            timestamp="2024-01-01T00:00:00+00:00",
            original_model="auto",
            selected_model="gpt-4o",
            actual_model="gpt-4o",
            task_type="chat",
            difficulty="medium",
            strategy="auto",
            fallback_chain=["claude-3", "gpt-3.5"],
            did_fallback=False,
            status_code=200,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        asyncio.run(history.record(entry))
        app.state.request_routing_history = history

        test_client = TestClient(app)
        response = test_client.get("/api/analytics/recent-requests")
        assert response.status_code == 200
        data = response.json()
        assert "requests" in data
        assert len(data["requests"]) == 1
        req = data["requests"][0]
        assert req["request_id"] == "abc123"
        assert req["timestamp"] == "2024-01-01T00:00:00+00:00"
        assert req["original_model"] == "auto"
        assert req["selected_model"] == "gpt-4o"
        assert req["actual_model"] == "gpt-4o"
        assert req["task_type"] == "chat"
        assert req["difficulty"] == "medium"
        assert req["strategy"] == "auto"
        assert req["fallback_chain"] == ["claude-3", "gpt-3.5"]
        assert req["did_fallback"] is False
        assert req["status_code"] == 200
        assert req["prompt_tokens"] == 10
        assert req["completion_tokens"] == 5
        assert req["total_tokens"] == 15

    def test_recent_requests_limit(self):
        """limit 参数限制返回数量"""
        import asyncio

        # Python 3.9 下 asyncio.Lock() 需要当前线程存在 event loop
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        app = build_dashboard_app(static_dir=None)
        history = RequestRoutingHistory(max_size=100)
        for i in range(60):
            entry = RequestRoutingEntry(
                request_id=f"req-{i:03d}",
                timestamp=f"2024-01-01T{i:02d}:00:00+00:00",
                original_model="auto",
                selected_model="gpt-4o",
                actual_model="gpt-4o",
                task_type="chat",
                difficulty="medium",
                strategy="auto",
                fallback_chain=[],
                did_fallback=False,
                status_code=200,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            )
            asyncio.run(history.record(entry))
        app.state.request_routing_history = history

        test_client = TestClient(app)
        response = test_client.get("/api/analytics/recent-requests?limit=50")
        assert response.status_code == 200
        data = response.json()
        assert len(data["requests"]) == 50
        # 验证是按时间倒序（最新的在前）
        assert data["requests"][0]["request_id"] == "req-059"
        assert data["requests"][49]["request_id"] == "req-010"
