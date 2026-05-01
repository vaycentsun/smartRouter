"""Token 使用量统计 — JSON 文件持久化

数据存储在 ~/.smart-router/token_stats.json，采用原子写入。
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

    def _save(self):
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.stats_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.stats_file)

    async def record(
        self, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int
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
                    "request_count": 0,
                }
            entry = records[model]
            entry["prompt_tokens"] += prompt_tokens
            entry["completion_tokens"] += completion_tokens
            entry["total_tokens"] += total_tokens
            entry["request_count"] += 1
            self._data["_meta"] = {
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self._save()

    def get_all(self) -> dict:
        return dict(self._data.get("records", {}))

    def reset(self):
        """仅供测试使用：清空所有统计数据"""
        self._data = {"version": 1, "records": {}}
        if self.stats_file.exists():
            self.stats_file.unlink()
