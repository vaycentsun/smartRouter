"""AlertNotifier — 告警通知器"""

import logging

import httpx

from .checker import AlertTrigger
from .config import AlertChannel, AlertRule

logger = logging.getLogger(__name__)


class AlertNotifier:
    """告警通知器 — 支持 webhook 和 log 渠道"""

    async def send(self, rule: AlertRule, trigger: AlertTrigger, channel: AlertChannel) -> bool:
        """发送通知，返回是否成功
        
        webhook: POST JSON payload，强制 https://
        log: 写入 logging.WARNING
        webhook 失败时回退到 log
        """
        try:
            channel_type = channel.type
        except Exception:
            return False
        if channel_type == "webhook":
            return await self._send_webhook(rule, trigger, channel)
        elif channel_type == "log":
            return self._send_log(rule, trigger)
        return False

    async def _send_webhook(self, rule: AlertRule, trigger: AlertTrigger, channel: AlertChannel) -> bool:
        """发送 webhook 通知"""
        url = channel.url or ""
        if not url.startswith("https://"):
            logger.warning(f"Webhook URL must use https://: {url}")
            return self._send_log(rule, trigger)

        payload = {
            "alert_name": rule.name,
            "severity": trigger.severity,
            "metric": trigger.metric,
            "current_value": trigger.current_value,
            "threshold": trigger.threshold,
            "timestamp": self._format_timestamp(trigger.timestamp),
            "message": trigger.message,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.warning(f"Webhook failed for {rule.name}: {e}. Falling back to log.")
            return self._send_log(rule, trigger)

    def _send_log(self, rule: AlertRule, trigger: AlertTrigger) -> bool:
        """发送日志通知"""
        logger.warning(
            f"[ALERT] {rule.name} | severity={trigger.severity} | "
            f"metric={trigger.metric} | value={trigger.current_value} | "
            f"threshold={trigger.threshold} | {trigger.message}"
        )
        return True

    @staticmethod
    def _format_timestamp(timestamp: float) -> str:
        """格式化时间戳为 ISO 8601 UTC"""
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
