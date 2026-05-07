"""RequestRoutingHistory 单元测试"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from smart_router.utils.request_routing_history import (
    DEFAULT_HISTORY_FILE,
    RequestRoutingEntry,
    RequestRoutingHistory,
)


class TestRequestRoutingHistory:
    """RequestRoutingHistory 单元测试"""

    @pytest.fixture
    def history(self):
        return RequestRoutingHistory(max_size=50)

    @pytest.fixture
    def sample_entry(self):
        return RequestRoutingEntry(
            request_id="req-001",
            timestamp="2025-01-01T00:00:00Z",
            original_model="gpt-4o",
            selected_model="gpt-4o-mini",
            actual_model="gpt-4o-mini",
            task_type="coding",
            difficulty="medium",
            strategy="cost",
            fallback_chain=["gpt-4o", "gpt-3.5-turbo"],
            attempted_fallbacks=1,
            did_fallback=True,
            status_code=200,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            error_info=None,
        )

    @pytest.mark.asyncio
    async def test_record_and_get_recent(self, history, sample_entry):
        """记录单条记录后正确读取，验证返回的字典包含所有字段"""
        await history.record(sample_entry)

        recent = history.get_recent()
        assert len(recent) == 1

        result = recent[0]
        assert result["request_id"] == "req-001"
        assert result["timestamp"] == "2025-01-01T00:00:00Z"
        assert result["original_model"] == "gpt-4o"
        assert result["selected_model"] == "gpt-4o-mini"
        assert result["actual_model"] == "gpt-4o-mini"
        assert result["task_type"] == "coding"
        assert result["difficulty"] == "medium"
        assert result["strategy"] == "cost"
        assert result["fallback_chain"] == ["gpt-4o", "gpt-3.5-turbo"]
        assert result["attempted_fallbacks"] == 1
        assert result["did_fallback"] is True
        assert result["status_code"] == 200
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["error_info"] is None

    @pytest.mark.asyncio
    async def test_max_size_limit(self, history):
        """写入 60 条记录，验证只保留后 50 条（最旧的被丢弃）"""
        for i in range(60):
            entry = RequestRoutingEntry(
                request_id=f"req-{i:03d}",
                timestamp="2025-01-01T00:00:00Z",
                original_model="gpt-4o",
                selected_model="gpt-4o-mini",
            )
            await history.record(entry)

        recent = history.get_recent()
        assert len(recent) == 50

        # 最旧的是 req-010，最新的是 req-059
        assert recent[-1]["request_id"] == "req-010"
        assert recent[0]["request_id"] == "req-059"

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, history):
        """使用 asyncio.gather 并发写入 100 条，验证无数据丢失、无异常"""

        async def write_entry(i: int):
            entry = RequestRoutingEntry(
                request_id=f"req-{i:03d}",
                timestamp="2025-01-01T00:00:00Z",
                original_model="gpt-4o",
                selected_model="gpt-4o-mini",
            )
            await history.record(entry)

        await asyncio.gather(*[write_entry(i) for i in range(100)])

        recent = history.get_recent()
        assert len(recent) == 50
        request_ids = {r["request_id"] for r in recent}
        # 由于并发，顺序不确定，但应保留最后的 50 条（某一时刻）
        # 只验证数量和无重复即可
        assert len(request_ids) == 50

    def test_entry_to_dict(self, history, sample_entry):
        """验证字典转换包含所有字段"""
        result = history._entry_to_dict(sample_entry)

        expected_keys = {
            "request_id",
            "timestamp",
            "original_model",
            "selected_model",
            "actual_model",
            "task_type",
            "difficulty",
            "strategy",
            "fallback_chain",
            "attempted_fallbacks",
            "did_fallback",
            "status_code",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "error_info",
        }
        assert set(result.keys()) == expected_keys

        assert result["request_id"] == "req-001"
        assert result["timestamp"] == "2025-01-01T00:00:00Z"
        assert result["original_model"] == "gpt-4o"
        assert result["selected_model"] == "gpt-4o-mini"
        assert result["actual_model"] == "gpt-4o-mini"
        assert result["task_type"] == "coding"
        assert result["difficulty"] == "medium"
        assert result["strategy"] == "cost"
        assert result["fallback_chain"] == ["gpt-4o", "gpt-3.5-turbo"]
        assert result["attempted_fallbacks"] == 1
        assert result["did_fallback"] is True
        assert result["status_code"] == 200
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["error_info"] is None

    # ==================== 持久化测试 ====================

    @pytest.mark.asyncio
    async def test_persistence_save_and_load(self, sample_entry):
        """启用持久化后，写入的记录应保存到文件，新实例能从文件加载"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            persist_file = Path(f.name)

        try:
            # 实例 A 写入记录
            history_a = RequestRoutingHistory(max_size=50, persist_file=persist_file)
            await history_a.record(sample_entry)

            # 验证文件已生成
            assert persist_file.exists()

            # 实例 B 从同一文件加载，应能读到记录
            history_b = RequestRoutingHistory(max_size=50, persist_file=persist_file)
            recent = history_b.get_recent()
            assert len(recent) == 1
            assert recent[0]["request_id"] == "req-001"
            assert recent[0]["fallback_chain"] == ["gpt-4o", "gpt-3.5-turbo"]
        finally:
            persist_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_persistence_cross_instance(self):
        """模拟跨进程场景：实例 A 写入，实例 B 读取，验证数据共享"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            persist_file = Path(f.name)

        try:
            # 实例 A 写入 3 条
            history_a = RequestRoutingHistory(max_size=50, persist_file=persist_file)
            for i in range(3):
                entry = RequestRoutingEntry(
                    request_id=f"req-{i:03d}",
                    timestamp="2025-01-01T00:00:00Z",
                    original_model="auto",
                    selected_model="gpt-4o",
                )
                await history_a.record(entry)

            # 实例 B 读取，应看到 3 条（倒序）
            history_b = RequestRoutingHistory(max_size=50, persist_file=persist_file)
            recent = history_b.get_recent()
            assert len(recent) == 3
            assert recent[0]["request_id"] == "req-002"
            assert recent[2]["request_id"] == "req-000"
        finally:
            persist_file.unlink(missing_ok=True)

    def test_persistence_corrupted_file(self):
        """持久化文件损坏时，应优雅降级，不抛异常，返回空列表"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json at all!!!")
            persist_file = Path(f.name)

        try:
            history = RequestRoutingHistory(max_size=50, persist_file=persist_file)
            recent = history.get_recent()
            assert recent == []
        finally:
            persist_file.unlink(missing_ok=True)

    def test_persistence_missing_file(self):
        """持久化文件不存在时，应返回空列表，不抛异常"""
        persist_file = Path(tempfile.gettempdir()) / "nonexistent_routing_history.json"
        history = RequestRoutingHistory(max_size=50, persist_file=persist_file)
        recent = history.get_recent()
        assert recent == []

    def test_default_history_file_exported(self):
        """DEFAULT_HISTORY_FILE 应正确定义为 Path 对象"""
        assert isinstance(DEFAULT_HISTORY_FILE, Path)
        assert DEFAULT_HISTORY_FILE.name == "request_routing_history.json"
