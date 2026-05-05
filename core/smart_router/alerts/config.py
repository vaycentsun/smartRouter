"""Alert 配置模块 — YAML 持久化"""

import logging
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AlertCondition(BaseModel):
    """告警条件"""

    metric: Literal["daily_cost", "daily_requests", "daily_tokens", "error_rate"]
    operator: Literal[">", "<", ">=", "<="]
    threshold: float


class AlertChannel(BaseModel):
    """告警通知渠道"""

    type: Literal["webhook", "log"]
    url: Optional[str] = None  # webhook 必填


class AlertRule(BaseModel):
    """告警规则"""

    id: str
    name: str
    enabled: bool = True
    condition: AlertCondition
    severity: Literal["info", "warning", "critical"] = "warning"
    time_window: str = "1d"  # "1d" | "7d" | "30d"
    channels: list[AlertChannel] = Field(default_factory=list)
    cooldown_minutes: int = 60


class AlertConfig:
    """告警配置管理器"""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.rules: list[AlertRule] = []
        self._load()

    def _load(self):
        """从 YAML 加载规则，无效规则跳过并记录警告"""
        if self.config_path.exists():
            try:
                data = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
                if not data:
                    return
                for item in data.get("alerts", []):
                    try:
                        self.rules.append(AlertRule(**item))
                    except Exception as e:
                        logger.warning(f"Invalid alert rule: {e}")
            except Exception as e:
                logger.warning(f"Failed to load alert config: {e}")

    def save(self):
        """保存规则到 YAML，创建时设置文件权限 0o600"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"alerts": [r.model_dump() for r in self.rules]}
        tmp = self.config_path.with_suffix(".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        tmp.replace(self.config_path)
        try:
            self.config_path.chmod(0o600)
        except OSError:
            pass

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """根据 ID 获取规则"""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def add_rule(self, rule: AlertRule) -> None:
        """添加新规则"""
        self.rules.append(rule)
        self.save()

    def update_rule(self, rule_id: str, rule: AlertRule) -> bool:
        """更新规则，返回是否成功"""
        for i, existing in enumerate(self.rules):
            if existing.id == rule_id:
                self.rules[i] = rule
                self.save()
                return True
        return False

    def delete_rule(self, rule_id: str) -> bool:
        """删除规则，返回是否成功"""
        for i, existing in enumerate(self.rules):
            if existing.id == rule_id:
                self.rules.pop(i)
                self.save()
                return True
        return False
