"""AlertChecker 单元测试"""

import time
from unittest.mock import MagicMock

import pytest

from smart_router.alerts.config import AlertConfig, AlertRule, AlertCondition
from smart_router.alerts.checker import AlertChecker


pytestmark = pytest.mark.asyncio


class TestAlertChecker:
    @pytest.fixture
    def mock_token_stats(self):
        stats = MagicMock()
        stats.get_daily.return_value = {}
        return stats

    @pytest.fixture
    def mock_error_counter(self):
        counter = MagicMock()
        counter.get_error_rate.return_value = 0.0
        return counter

    @pytest.fixture
    def checker(self, mock_token_stats, mock_error_counter, tmp_path):
        config = AlertConfig(tmp_path / "alerts.yaml")
        return AlertChecker(config, mock_token_stats, mock_error_counter)

    async def test_no_rules(self, checker):
        """无规则时不触发"""
        triggers = await checker.check_all()
        assert triggers == []

    async def test_trigger_when_condition_met(self, checker, mock_token_stats):
        """条件满足时触发"""
        mock_token_stats.get_daily.return_value = {
            "gpt-4o": {"request_count": 200, "total_tokens": 5000}
        }
        rule = AlertRule(
            id="req-high",
            name="请求数过高",
            enabled=True,
            condition=AlertCondition(metric="daily_requests", operator=">", threshold=100),
        )
        checker.config.add_rule(rule)

        triggers = await checker.check_all()
        assert len(triggers) == 1
        assert triggers[0].rule_id == "req-high"
        assert triggers[0].current_value == 200

    async def test_no_trigger_when_condition_not_met(self, checker, mock_token_stats):
        """条件不满足时不触发"""
        mock_token_stats.get_daily.return_value = {
            "gpt-4o": {"request_count": 50, "total_tokens": 1000}
        }
        rule = AlertRule(
            id="req-high",
            name="请求数过高",
            enabled=True,
            condition=AlertCondition(metric="daily_requests", operator=">", threshold=100),
        )
        checker.config.add_rule(rule)

        triggers = await checker.check_all()
        assert triggers == []

    async def test_cooldown(self, checker, mock_token_stats):
        """冷却期内不重复触发"""
        mock_token_stats.get_daily.return_value = {
            "gpt-4o": {"request_count": 200, "total_tokens": 5000}
        }
        rule = AlertRule(
            id="req-high",
            name="请求数过高",
            enabled=True,
            condition=AlertCondition(metric="daily_requests", operator=">", threshold=100),
            cooldown_minutes=60,
        )
        checker.config.add_rule(rule)

        # 第一次应触发
        triggers = await checker.check_all()
        assert len(triggers) == 1

        # 第二次在冷却期内，不应触发
        triggers = await checker.check_all()
        assert triggers == []

    async def test_disabled_rule(self, checker, mock_token_stats):
        """禁用规则不触发"""
        mock_token_stats.get_daily.return_value = {
            "gpt-4o": {"request_count": 200, "total_tokens": 5000}
        }
        rule = AlertRule(
            id="req-high",
            name="请求数过高",
            enabled=False,
            condition=AlertCondition(metric="daily_requests", operator=">", threshold=100),
        )
        checker.config.add_rule(rule)

        triggers = await checker.check_all()
        assert triggers == []

    async def test_error_rate_metric(self, checker, mock_error_counter):
        """error_rate 指标直接读取 error_counter"""
        mock_error_counter.get_error_rate.return_value = 0.1
        rule = AlertRule(
            id="err-high",
            name="错误率过高",
            enabled=True,
            condition=AlertCondition(metric="error_rate", operator=">=", threshold=0.05),
        )
        checker.config.add_rule(rule)

        triggers = await checker.check_all()
        assert len(triggers) == 1
        assert triggers[0].current_value == 0.1
        assert triggers[0].metric == "error_rate"

    async def test_error_rate_not_trigger(self, checker, mock_error_counter):
        """error_rate 未达阈值不触发"""
        mock_error_counter.get_error_rate.return_value = 0.01
        rule = AlertRule(
            id="err-high",
            name="错误率过高",
            enabled=True,
            condition=AlertCondition(metric="error_rate", operator=">=", threshold=0.05),
        )
        checker.config.add_rule(rule)

        triggers = await checker.check_all()
        assert triggers == []

    async def test_time_window_7d(self, checker, mock_token_stats):
        """7天窗口应汇总7天数据"""
        # 模拟 checker 内部日期计算：这里简化，直接让 get_daily 返回数据
        # 实际上 checker 会循环7天调用 get_daily
        mock_token_stats.get_daily.side_effect = lambda date_str: {
            "gpt-4o": {"request_count": 100, "total_tokens": 1000}
        } if date_str else {}

        rule = AlertRule(
            id="req-7d",
            name="7天请求数",
            enabled=True,
            condition=AlertCondition(metric="daily_requests", operator=">", threshold=500),
            time_window="7d",
        )
        checker.config.add_rule(rule)

        triggers = await checker.check_all()
        # 7天 * 100 = 700 > 500，应触发
        assert len(triggers) == 1
        assert triggers[0].current_value == 700.0

    async def test_daily_tokens_metric(self, checker, mock_token_stats):
        """daily_tokens 指标"""
        mock_token_stats.get_daily.return_value = {
            "gpt-4o": {"request_count": 10, "total_tokens": 5000}
        }
        rule = AlertRule(
            id="tok-high",
            name="Token 数过高",
            enabled=True,
            condition=AlertCondition(metric="daily_tokens", operator=">", threshold=3000),
        )
        checker.config.add_rule(rule)

        triggers = await checker.check_all()
        assert len(triggers) == 1
        assert triggers[0].current_value == 5000

    async def test_operators(self, checker, mock_token_stats):
        """测试各种比较运算符"""
        mock_token_stats.get_daily.return_value = {
            "gpt-4o": {"request_count": 100, "total_tokens": 1000}
        }

        test_cases = [
            (">", 50, True),
            (">", 100, False),
            (">=", 100, True),
            ("<", 200, True),
            ("<", 100, False),
            ("<=", 100, True),
        ]

        for op, threshold, expected in test_cases:
            checker.config.rules = []
            rule = AlertRule(
                id=f"op-{op}",
                name="Operator Test",
                enabled=True,
                condition=AlertCondition(metric="daily_requests", operator=op, threshold=threshold),
            )
            checker.config.add_rule(rule)

            triggers = await checker.check_all()
            if expected:
                assert len(triggers) == 1, f"operator {op} {threshold} should trigger"
            else:
                assert triggers == [], f"operator {op} {threshold} should not trigger"
