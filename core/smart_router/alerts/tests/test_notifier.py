"""AlertNotifier 单元测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from smart_router.alerts.checker import AlertTrigger
from smart_router.alerts.config import AlertChannel, AlertCondition, AlertRule
from smart_router.alerts.notifier import AlertNotifier

pytestmark = pytest.mark.asyncio


class TestAlertNotifier:
    @pytest.fixture
    def rule(self):
        return AlertRule(
            id="test-rule",
            name="测试告警",
            enabled=True,
            condition=AlertCondition(metric="daily_requests", operator=">", threshold=100),
        )

    @pytest.fixture
    def trigger(self):
        return AlertTrigger(
            rule_id="test-rule",
            rule_name="测试告警",
            severity="warning",
            metric="daily_requests",
            operator=">",
            threshold=100,
            current_value=200,
            timestamp=1714909200.0,
            message="Smart Router 告警：测试告警 — daily_requests 当前值 200.0000 > 阈值 100",
        )

    @pytest.fixture
    def notifier(self):
        return AlertNotifier()

    async def test_webhook_success(self, notifier, rule, trigger):
        """webhook 成功发送"""
        channel = AlertChannel(type="webhook", url="https://hooks.example.com/alert")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            result = await notifier.send(rule, trigger, channel)
            assert result is True

            # 验证调用参数
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://hooks.example.com/alert"
            payload = call_args[1]["json"]
            assert payload["alert_name"] == "测试告警"
            assert payload["severity"] == "warning"
            assert payload["metric"] == "daily_requests"
            assert payload["current_value"] == 200
            assert payload["threshold"] == 100
            assert "message" in payload
            assert "timestamp" in payload

    async def test_webhook_failure_fallback_to_log(self, notifier, rule, trigger):
        """webhook 失败时回退到 log"""
        channel = AlertChannel(type="webhook", url="https://hooks.example.com/alert")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Connection failed")

            with patch.object(notifier, "_send_log", return_value=True) as mock_log:
                result = await notifier.send(rule, trigger, channel)
                assert result is True
                mock_log.assert_called_once_with(rule, trigger)

    async def test_webhook_non_https_fallback_to_log(self, notifier, rule, trigger):
        """非 https webhook 回退到 log"""
        channel = AlertChannel(type="webhook", url="http://insecure.example.com/alert")

        with patch.object(notifier, "_send_log", return_value=True) as mock_log:
            result = await notifier.send(rule, trigger, channel)
            assert result is True
            mock_log.assert_called_once_with(rule, trigger)

    async def test_log_channel(self, notifier, rule, trigger):
        """log 渠道直接记录日志"""
        channel = AlertChannel(type="log")

        with patch("smart_router.alerts.notifier.logger.warning") as mock_warning:
            result = await notifier.send(rule, trigger, channel)
            assert result is True
            mock_warning.assert_called_once()
            log_msg = mock_warning.call_args[0][0]
            assert "测试告警" in log_msg
            assert "daily_requests" in log_msg
            assert "200" in log_msg

    async def test_unknown_channel_type(self, notifier, rule, trigger):
        """未知渠道类型返回 False"""
        # 绕过 Pydantic 验证创建无效 channel
        channel = object.__new__(AlertChannel)
        object.__setattr__(channel, "type", "unknown")
        result = await notifier.send(rule, trigger, channel)
        assert result is False
