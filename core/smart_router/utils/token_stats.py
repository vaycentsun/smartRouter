"""Token 使用量统计 — JSON 文件持久化

数据存储在 ~/.smart-router/token_stats.json，采用原子写入。
v2 格式支持双轨存储：累计 records + 按日聚合 daily_records。
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional
import asyncio

DEFAULT_STATS_FILE = Path.home() / ".smart-router" / "token_stats.json"
logger = logging.getLogger(__name__)


class TokenStats:
    def __init__(self, stats_file: Optional[Path] = None):
        self.stats_file = stats_file or DEFAULT_STATS_FILE
        self._data: dict = {}
        self._lock: Optional[asyncio.Lock] = None
        self._load()

    def _load(self):
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self._data = json.loads(content)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Token stats file corrupted or unreadable: {e}. Starting fresh.")
                self._data = {}
        if "records" not in self._data:
            self._data["records"] = {}
        if "version" not in self._data:
            self._data["version"] = 1
        # v1 → v2 自动升级
        if self._data.get("version") == 1:
            self._migrate_v1_to_v2()

    def _migrate_v1_to_v2(self):
        """将 v1 格式升级到 v2：保留 records，新增 daily_records，升级前备份"""
        try:
            backup_path = self.stats_file.with_suffix(".json.bak")
            with open(self.stats_file, "r", encoding="utf-8") as f:
                original_content = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original_content)
            logger.info(f"Token stats v1 backup created: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create v1 backup: {e}")
        self._data["version"] = 2
        self._data.setdefault("daily_records", {})
        self._save()
        logger.info("Token stats migrated from v1 to v2")

    def _save(self):
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.stats_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.stats_file)
        # 敏感数据文件权限设为 0o600
        try:
            os.chmod(self.stats_file, 0o600)
        except OSError:
            pass

    async def record(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        reasoning_tokens: int = 0,
        cached_tokens: int = 0,
        date: Optional[str] = None,
    ):
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            records = self._data.setdefault("records", {})
            if model not in records:
                records[model] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "reasoning_tokens": 0,
                    "cached_tokens": 0,
                    "request_count": 0,
                }
            entry = records[model]
            entry["prompt_tokens"] += prompt_tokens
            entry["completion_tokens"] += completion_tokens
            entry["total_tokens"] += total_tokens
            entry["reasoning_tokens"] += reasoning_tokens
            entry["cached_tokens"] += cached_tokens
            entry["request_count"] += 1

            # 同时更新每日数据
            date_str = date or time.strftime("%Y-%m-%d", time.gmtime())
            daily_records = self._data.setdefault("daily_records", {})
            if date_str not in daily_records:
                daily_records[date_str] = {}
            if model not in daily_records[date_str]:
                daily_records[date_str][model] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "reasoning_tokens": 0,
                    "cached_tokens": 0,
                    "request_count": 0,
                }
            daily_entry = daily_records[date_str][model]
            daily_entry["prompt_tokens"] += prompt_tokens
            daily_entry["completion_tokens"] += completion_tokens
            daily_entry["total_tokens"] += total_tokens
            daily_entry["reasoning_tokens"] += reasoning_tokens
            daily_entry["cached_tokens"] += cached_tokens
            daily_entry["request_count"] += 1

            self._data["_meta"] = {
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self._save()

    def get_all(self) -> dict:
        return dict(self._data.get("records", {}))

    def get_daily(self, date_str: str) -> dict:
        """获取指定日期的模型统计"""
        return dict(self._data.get("daily_records", {}).get(date_str, {}))

    def get_daily_range(self, start: str, end: str) -> dict:
        """获取日期范围内的每日统计（含起止）"""
        daily_records = self._data.get("daily_records", {})
        result = {}
        for date_str, models in daily_records.items():
            if start <= date_str <= end:
                result[date_str] = dict(models)
        return result

    def get_summary(self, days: int) -> dict:
        """获取最近 N 天的汇总统计"""
        daily_records = self._data.get("daily_records", {})
        if not daily_records:
            return {
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_reasoning_tokens": 0,
                "total_cached_tokens": 0,
                "total_requests": 0,
                "model_breakdown": {},
            }

        # 按日期排序，取最近 days 天
        sorted_dates = sorted(daily_records.keys(), reverse=True)
        recent_dates = sorted_dates[:days]

        total_prompt = 0
        total_completion = 0
        total_reasoning = 0
        total_cached = 0
        total_requests = 0
        model_breakdown: dict = {}

        for date_str in recent_dates:
            for model, entry in daily_records[date_str].items():
                pt = entry.get("prompt_tokens", 0)
                ct = entry.get("completion_tokens", 0)
                rt = entry.get("reasoning_tokens", 0)
                cat = entry.get("cached_tokens", 0)
                rc = entry.get("request_count", 0)
                total_prompt += pt
                total_completion += ct
                total_reasoning += rt
                total_cached += cat
                total_requests += rc

                if model not in model_breakdown:
                    model_breakdown[model] = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "reasoning_tokens": 0,
                        "cached_tokens": 0,
                        "request_count": 0,
                    }
                mb = model_breakdown[model]
                mb["prompt_tokens"] += pt
                mb["completion_tokens"] += ct
                mb["total_tokens"] += entry.get("total_tokens", 0)
                mb["reasoning_tokens"] += rt
                mb["cached_tokens"] += cat
                mb["request_count"] += rc

        return {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_reasoning_tokens": total_reasoning,
            "total_cached_tokens": total_cached,
            "total_requests": total_requests,
            "model_breakdown": model_breakdown,
        }

    def reset(self):
        """仅供测试使用：清空所有统计数据"""
        self._data = {"version": 2, "records": {}, "daily_records": {}}
        if self.stats_file.exists():
            self.stats_file.unlink()
