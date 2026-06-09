"""AlertConfig 单元测试"""

import json

from smart_router.alerts.config import (
    AlertChannel,
    AlertCondition,
    AlertConfig,
    AlertRule,
)


class TestAlertConfig:
    def test_load_empty_file(self, tmp_path):
        """空文件应得到空规则列表"""
        config_path = tmp_path / "alerts.yaml"
        config_path.write_text("")
        cfg = AlertConfig(config_path)
        assert cfg.rules == []

    def test_load_valid_rules(self, tmp_path):
        """正常解析有效规则"""
        config_path = tmp_path / "alerts.yaml"
        data = {
            "alerts": [
                {
                    "id": "rule-1",
                    "name": "高成本告警",
                    "enabled": True,
                    "condition": {
                        "metric": "daily_cost",
                        "operator": ">",
                        "threshold": 10.0,
                    },
                    "severity": "warning",
                    "time_window": "1d",
                    "channels": [{"type": "log"}],
                    "cooldown_minutes": 30,
                },
                {
                    "id": "rule-2",
                    "name": "错误率告警",
                    "enabled": False,
                    "condition": {
                        "metric": "error_rate",
                        "operator": ">=",
                        "threshold": 0.05,
                    },
                    "severity": "critical",
                    "time_window": "1d",
                    "channels": [
                        {"type": "webhook", "url": "https://hooks.example.com/alert"}
                    ],
                    "cooldown_minutes": 60,
                },
            ]
        }
        config_path.write_text(json.dumps(data), encoding="utf-8")
        cfg = AlertConfig(config_path)

        assert len(cfg.rules) == 2
        assert cfg.rules[0].id == "rule-1"
        assert cfg.rules[0].condition.metric == "daily_cost"
        assert cfg.rules[1].id == "rule-2"
        assert cfg.rules[1].enabled is False
        assert cfg.rules[1].channels[0].type == "webhook"
        assert cfg.rules[1].channels[0].url == "https://hooks.example.com/alert"

    def test_skip_invalid_rules(self, tmp_path):
        """无效规则应被跳过，不影响其他规则"""
        config_path = tmp_path / "alerts.yaml"
        data = {
            "alerts": [
                {
                    "id": "valid-rule",
                    "name": "Valid",
                    "condition": {
                        "metric": "daily_requests",
                        "operator": ">",
                        "threshold": 100,
                    },
                },
                {
                    "id": "invalid-rule",
                    "name": "Invalid",
                    "condition": {
                        "metric": "unknown_metric",  # 无效
                        "operator": ">",
                        "threshold": 100,
                    },
                },
            ]
        }
        config_path.write_text(json.dumps(data), encoding="utf-8")
        cfg = AlertConfig(config_path)

        assert len(cfg.rules) == 1
        assert cfg.rules[0].id == "valid-rule"

    def test_save_and_load_consistency(self, tmp_path):
        """save/load 一致性"""
        config_path = tmp_path / "alerts.yaml"
        cfg = AlertConfig(config_path)
        rule = AlertRule(
            id="test-rule",
            name="测试规则",
            enabled=True,
            condition=AlertCondition(metric="daily_tokens", operator=">=", threshold=1000),
            severity="info",
            time_window="7d",
            channels=[AlertChannel(type="webhook", url="https://example.com/hook")],
            cooldown_minutes=120,
        )
        cfg.add_rule(rule)

        # 重新加载
        cfg2 = AlertConfig(config_path)
        assert len(cfg2.rules) == 1
        loaded = cfg2.rules[0]
        assert loaded.id == "test-rule"
        assert loaded.name == "测试规则"
        assert loaded.condition.metric == "daily_tokens"
        assert loaded.condition.operator == ">="
        assert loaded.condition.threshold == 1000
        assert loaded.severity == "info"
        assert loaded.time_window == "7d"
        assert len(loaded.channels) == 1
        assert loaded.channels[0].type == "webhook"
        assert loaded.channels[0].url == "https://example.com/hook"
        assert loaded.cooldown_minutes == 120

    def test_get_rule(self, tmp_path):
        """根据 ID 获取规则"""
        config_path = tmp_path / "alerts.yaml"
        cfg = AlertConfig(config_path)
        rule = AlertRule(
            id="find-me",
            name="Find Me",
            condition=AlertCondition(metric="error_rate", operator=">", threshold=0.1),
        )
        cfg.add_rule(rule)

        found = cfg.get_rule("find-me")
        assert found is not None
        assert found.name == "Find Me"

        not_found = cfg.get_rule("not-exist")
        assert not_found is None

    def test_update_rule(self, tmp_path):
        """更新规则"""
        config_path = tmp_path / "alerts.yaml"
        cfg = AlertConfig(config_path)
        rule = AlertRule(
            id="update-me",
            name="Old Name",
            condition=AlertCondition(metric="daily_cost", operator=">", threshold=10),
        )
        cfg.add_rule(rule)

        updated = AlertRule(
            id="update-me",
            name="New Name",
            condition=AlertCondition(metric="daily_cost", operator=">", threshold=20),
        )
        assert cfg.update_rule("update-me", updated) is True
        assert cfg.get_rule("update-me").name == "New Name"
        assert cfg.get_rule("update-me").condition.threshold == 20
        assert cfg.update_rule("not-exist", updated) is False

    def test_delete_rule(self, tmp_path):
        """删除规则"""
        config_path = tmp_path / "alerts.yaml"
        cfg = AlertConfig(config_path)
        rule = AlertRule(
            id="delete-me",
            name="Delete Me",
            condition=AlertCondition(metric="daily_cost", operator=">", threshold=10),
        )
        cfg.add_rule(rule)

        assert cfg.delete_rule("delete-me") is True
        assert cfg.get_rule("delete-me") is None
        assert cfg.delete_rule("not-exist") is False

    def test_file_permissions(self, tmp_path):
        """创建时文件权限应为 0o600"""
        config_path = tmp_path / "alerts.yaml"
        cfg = AlertConfig(config_path)
        rule = AlertRule(
            id="perm-test",
            name="Permission Test",
            condition=AlertCondition(metric="daily_cost", operator=">", threshold=10),
        )
        cfg.add_rule(rule)

        import stat
        mode = config_path.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600
