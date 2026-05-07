"""请求路由历史记录 — 内存环形缓冲区

存储最近 N 条请求路由记录，用于 Dashboard 和调试。基于 collections.deque 实现，
支持协程安全的异步写入。
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


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
    """请求路由历史记录管理器（内存环形缓冲区）"""

    def __init__(self, max_size: int = 50):
        self._buffer: deque[RequestRoutingEntry] = deque(maxlen=max_size)
        self._lock = asyncio.Lock()

    async def record(self, entry: RequestRoutingEntry) -> None:
        """协程安全地写入一条记录"""
        async with self._lock:
            self._buffer.append(entry)

    def get_recent(self, limit: int = 50) -> list[dict]:
        """返回最近 N 条记录的字典列表（按时间倒序）"""
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
