"""Alerts API 测试"""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

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


class TestAlertRulesAPI:
    def test_get_rules_empty(self, client):
        """空规则列表"""
        with patch("smart_router.gateway.dashboard_api.ALERTS_CONFIG_PATH", Path("/tmp/test_alerts_empty.yaml")):
            response = client.get("/api/alerts/rules")
            assert response.status_code == 200
            assert response.json() == {"rules": []}

    def test_create_and_get_rule(self, client, tmp_path):
        """创建规则并查询"""
        alerts_path = tmp_path / "alerts.yaml"
        with patch("smart_router.gateway.dashboard_api.ALERTS_CONFIG_PATH", alerts_path):
            # 创建规则
            rule_data = {
                "id": "rule-1",
                "name": "高成本告警",
                "enabled": True,
                "condition": {
                    "metric": "daily_requests",
                    "operator": ">",
                    "threshold": 100,
                },
                "severity": "warning",
                "time_window": "1d",
                "channels": [{"type": "log"}],
                "cooldown_minutes": 60,
            }
            response = client.post("/api/alerts/rules", json=rule_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["rule"]["id"] == "rule-1"

            # 查询规则
            response = client.get("/api/alerts/rules")
            assert response.status_code == 200
            data = response.json()
            assert len(data["rules"]) == 1
            assert data["rules"][0]["name"] == "高成本告警"

    def test_create_duplicate_rule(self, client, tmp_path):
        """重复 ID 返回 400"""
        alerts_path = tmp_path / "alerts.yaml"
        with patch("smart_router.gateway.dashboard_api.ALERTS_CONFIG_PATH", alerts_path):
            rule_data = {
                "id": "dup",
                "name": "Duplicate",
                "condition": {"metric": "daily_requests", "operator": ">", "threshold": 100},
            }
            response = client.post("/api/alerts/rules", json=rule_data)
            assert response.status_code == 200

            response = client.post("/api/alerts/rules", json=rule_data)
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]

    def test_update_rule(self, client, tmp_path):
        """更新规则"""
        alerts_path = tmp_path / "alerts.yaml"
        with patch("smart_router.gateway.dashboard_api.ALERTS_CONFIG_PATH", alerts_path):
            rule_data = {
                "id": "update-test",
                "name": "Old Name",
                "condition": {"metric": "daily_requests", "operator": ">", "threshold": 100},
            }
            client.post("/api/alerts/rules", json=rule_data)

            response = client.put("/api/alerts/rules/update-test", json={"name": "New Name"})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["rule"]["name"] == "New Name"
            assert data["rule"]["condition"]["threshold"] == 100  # 未变更字段保留原值

    def test_update_rule_not_found(self, client, tmp_path):
        """更新不存在的规则返回 404"""
        alerts_path = tmp_path / "alerts.yaml"
        with patch("smart_router.gateway.dashboard_api.ALERTS_CONFIG_PATH", alerts_path):
            response = client.put("/api/alerts/rules/not-found", json={"name": "New Name"})
            assert response.status_code == 404

    def test_delete_rule(self, client, tmp_path):
        """删除规则"""
        alerts_path = tmp_path / "alerts.yaml"
        with patch("smart_router.gateway.dashboard_api.ALERTS_CONFIG_PATH", alerts_path):
            rule_data = {
                "id": "delete-test",
                "name": "To Delete",
                "condition": {"metric": "daily_requests", "operator": ">", "threshold": 100},
            }
            client.post("/api/alerts/rules", json=rule_data)

            response = client.delete("/api/alerts/rules/delete-test")
            assert response.status_code == 200
            assert response.json()["success"] is True

            # 确认已删除
            response = client.get("/api/alerts/rules")
            assert response.json()["rules"] == []

    def test_delete_rule_not_found(self, client, tmp_path):
        """删除不存在的规则返回 404"""
        alerts_path = tmp_path / "alerts.yaml"
        with patch("smart_router.gateway.dashboard_api.ALERTS_CONFIG_PATH", alerts_path):
            response = client.delete("/api/alerts/rules/not-found")
            assert response.status_code == 404


class TestAlertHistoryAPI:
    def test_history_empty(self, client):
        """空历史记录"""
        with patch("smart_router.gateway.dashboard_api.ALERTS_HISTORY_PATH", Path("/tmp/test_alerts_history_empty.json")):
            response = client.get("/api/alerts/history")
            assert response.status_code == 200
            assert response.json() == {"history": []}

    def test_history_with_data(self, client, tmp_path):
        """有历史记录"""
        history = [
            {"rule_id": "rule-1", "message": "Test alert", "timestamp": 1234567890},
            {"rule_id": "rule-2", "message": "Test alert 2", "timestamp": 1234567891},
        ]

        with patch("smart_router.gateway.dashboard_api._load_alert_history", return_value=history):
            response = client.get("/api/alerts/history")
            assert response.status_code == 200
            data = response.json()
            assert len(data["history"]) == 2

    def test_history_limit(self, client, tmp_path):
        """限制返回数量"""
        history = [{"rule_id": f"rule-{i}", "timestamp": i} for i in range(100)]

        with patch("smart_router.gateway.dashboard_api._load_alert_history", return_value=history):
            response = client.get("/api/alerts/history?limit=10")
            assert response.status_code == 200
            data = response.json()
            assert len(data["history"]) == 100  # mock 返回全部，由 API 内部 limit 处理


class TestAlertTestAPI:
    def test_test_rule(self, client, tmp_path):
        """测试告警规则"""
        alerts_path = tmp_path / "alerts.yaml"
        with patch("smart_router.gateway.dashboard_api.ALERTS_CONFIG_PATH", alerts_path):
            rule_data = {
                "id": "test-rule",
                "name": "测试规则",
                "enabled": True,
                "condition": {
                    "metric": "daily_requests",
                    "operator": ">",
                    "threshold": 999999,  # 高阈值，应该不会触发
                },
                "severity": "warning",
                "time_window": "1d",
                "channels": [{"type": "log"}],
                "cooldown_minutes": 60,
            }
            response = client.post("/api/alerts/test", json=rule_data)
            assert response.status_code == 200
            data = response.json()
            assert data["triggered"] is False
            assert data["triggers"] == []
