"""请求路由历史记录 — 支持内存 + 文件持久化双模式

存储最近 N 条请求路由记录，用于 Dashboard 和调试。基于 collections.deque 实现，
支持协程安全的异步写入。当提供 persist_file 时自动持久化到 JSON 文件，
解决 Proxy 与 Dashboard 跨进程数据共享问题。
"""

import asyncio
import json
import logging
import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
DEFAULT_HISTORY_FILE = Path.home() / ".smart-router" / "request_routing_history.json"


@dataclass
class RequestRoutingEntry:
    """单条请求路由记录"""

    request_id: str
    timestamp: str  # ISO 8601 format
    original_model: str
    selected_model: str
    actual_model: Optional[str] = None
    task_type: Optional[str] = None
    difficulty: Optional[str] = None
    strategy: Optional[str] = None
    fallback_chain: list[str] = field(default_factory=list)
    attempted_fallbacks: Optional[int] = None
    did_fallback: bool = False
    status_code: int = 200
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error_info: Optional[str] = None


class RequestRoutingHistory:
    """请求路由历史记录管理器（内存环形缓冲区，可选文件持久化）"""

    def __init__(self, max_size: int = 50, persist_file: Optional[Path] = None):
        self._buffer: deque[RequestRoutingEntry] = deque(maxlen=max_size)
        self._lock: Optional[asyncio.Lock] = None
        self._max_size = max_size
        self._persist_file = persist_file
        if self._persist_file:
            self._load()

    def _load(self) -> None:
        """从持久化文件加载记录"""
        if not self._persist_file or not self._persist_file.exists():
            return
        try:
            with open(self._persist_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            records = data.get("records", [])
            for item in records:
                entry = RequestRoutingEntry(
                    request_id=item["request_id"],
                    timestamp=item["timestamp"],
                    original_model=item["original_model"],
                    selected_model=item["selected_model"],
                    actual_model=item.get("actual_model"),
                    task_type=item.get("task_type"),
                    difficulty=item.get("difficulty"),
                    strategy=item.get("strategy"),
                    fallback_chain=item.get("fallback_chain", []),
                    attempted_fallbacks=item.get("attempted_fallbacks"),
                    did_fallback=item.get("did_fallback", False),
                    status_code=item.get("status_code", 200),
                    prompt_tokens=item.get("prompt_tokens", 0),
                    completion_tokens=item.get("completion_tokens", 0),
                    total_tokens=item.get("total_tokens", 0),
                    error_info=item.get("error_info"),
                )
                self._buffer.append(entry)
            logger.debug(f"Loaded {len(self._buffer)} routing history records from {self._persist_file}")
        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.warning(f"Failed to load routing history from {self._persist_file}: {e}")

    def _save(self) -> None:
        """保存记录到持久化文件（原子写入）"""
        if not self._persist_file:
            return
        try:
            self._persist_file.parent.mkdir(parents=True, exist_ok=True)
            records = [self._entry_to_dict(e) for e in self._buffer]
            data = {
                "version": 1,
                "max_size": self._max_size,
                "records": records,
            }
            tmp = self._persist_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self._persist_file)
            try:
                os.chmod(self._persist_file, 0o600)
            except OSError:
                pass
        except IOError as e:
            logger.warning(f"Failed to save routing history: {e}")

    async def record(self, entry: RequestRoutingEntry) -> None:
        """协程安全地写入一条记录"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            self._buffer.append(entry)
            self._save()

    def get_recent(self, limit: int = 50) -> list[dict]:
        """返回最近 N 条记录的字典列表（按时间倒序）"""
        # 如果启用了持久化，先重新加载以获取其他进程写入的数据
        if self._persist_file:
            self._buffer.clear()
            self._load()
        # deque 的迭代顺序是从旧到新，需要反转以获得倒序
        recent_entries = list(self._buffer)[-limit:]
        return [self._entry_to_dict(entry) for entry in reversed(recent_entries)]

    def _entry_to_dict(self, entry: RequestRoutingEntry) -> dict:
        """将 RequestRoutingEntry 转换为字典"""
        return {
            "request_id": entry.request_id,
            "timestamp": entry.timestamp,
            "original_model": entry.original_model,
            "selected_model": entry.selected_model,
            "actual_model": entry.actual_model,
            "task_type": entry.task_type,
            "difficulty": entry.difficulty,
            "strategy": entry.strategy,
            "fallback_chain": entry.fallback_chain,
            "attempted_fallbacks": entry.attempted_fallbacks,
            "did_fallback": entry.did_fallback,
            "status_code": entry.status_code,
            "prompt_tokens": entry.prompt_tokens,
            "completion_tokens": entry.completion_tokens,
            "total_tokens": entry.total_tokens,
            "error_info": entry.error_info,
        }
