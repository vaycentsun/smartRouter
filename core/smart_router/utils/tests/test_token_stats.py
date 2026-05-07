import pytest
import asyncio
import json
import time
from pathlib import Path
from smart_router.utils.token_stats import TokenStats


class TestTokenStats:
    def test_load_empty_file(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        stats_file.write_text("")
        ts = TokenStats(stats_file=stats_file)
        assert ts.get_all() == {}

    def test_load_nonexistent_file(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        assert ts.get_all() == {}
        assert ts._data["version"] == 2

    def test_record_single_model(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        asyncio.run(ts.record("gpt-4o", 100, 50, 150))
        
        all_stats = ts.get_all()
        assert all_stats["gpt-4o"]["prompt_tokens"] == 100
        assert all_stats["gpt-4o"]["completion_tokens"] == 50
        assert all_stats["gpt-4o"]["total_tokens"] == 150
        assert all_stats["gpt-4o"]["request_count"] == 1

    def test_record_multiple_models(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        asyncio.run(ts.record("gpt-4o", 100, 50, 150))
        asyncio.run(ts.record("claude-3-sonnet", 200, 100, 300))
        asyncio.run(ts.record("gpt-4o", 50, 25, 75))
        
        all_stats = ts.get_all()
        assert all_stats["gpt-4o"]["prompt_tokens"] == 150
        assert all_stats["gpt-4o"]["request_count"] == 2
        assert all_stats["claude-3-sonnet"]["request_count"] == 1

    def test_persistence(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts1 = TokenStats(stats_file=stats_file)
        asyncio.run(ts1.record("gpt-4o", 100, 50, 150))
        
        ts2 = TokenStats(stats_file=stats_file)
        all_stats = ts2.get_all()
        assert all_stats["gpt-4o"]["prompt_tokens"] == 100
        assert all_stats["gpt-4o"]["request_count"] == 1

    def test_file_schema(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        asyncio.run(ts.record("gpt-4o", 100, 50, 150))
        
        content = json.loads(stats_file.read_text())
        assert content["version"] == 2
        assert "records" in content
        assert "daily_records" in content
        assert "_meta" in content
        assert "last_updated" in content["_meta"]

    def test_concurrent_record(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        
        async def worker():
            for _ in range(10):
                await ts.record("gpt-4o", 1, 1, 2)
        
        async def run():
            await asyncio.gather(*[worker() for _ in range(5)])
        
        asyncio.run(run())
        all_stats = ts.get_all()
        assert all_stats["gpt-4o"]["request_count"] == 50
        assert all_stats["gpt-4o"]["total_tokens"] == 100

    def test_reset(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        asyncio.run(ts.record("gpt-4o", 100, 50, 150))
        ts.reset()
        assert ts.get_all() == {}
        assert not stats_file.exists()

    def test_corrupted_file(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        stats_file.write_text("not valid json")
        ts = TokenStats(stats_file=stats_file)
        assert ts.get_all() == {}


class TestTokenStatsV1Migration:
    """测试 v1 格式自动升级到 v2"""

    def test_v1_format_auto_upgraded(self, tmp_path):
        """v1 格式加载时自动升级到 v2，保留 records"""
        stats_file = tmp_path / "token_stats.json"
        v1_data = {
            "version": 1,
            "records": {
                "gpt-4o": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 500,
                    "total_tokens": 1500,
                    "request_count": 10,
                }
            }
        }
        stats_file.write_text(json.dumps(v1_data))

        ts = TokenStats(stats_file=stats_file)
        assert ts._data["version"] == 2
        assert "daily_records" in ts._data
        assert ts.get_all()["gpt-4o"]["prompt_tokens"] == 1000

    def test_v1_backup_created(self, tmp_path):
        """升级前创建 .bak 备份"""
        stats_file = tmp_path / "token_stats.json"
        v1_data = {
            "version": 1,
            "records": {"gpt-4o": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150, "request_count": 1}}
        }
        stats_file.write_text(json.dumps(v1_data))

        ts = TokenStats(stats_file=stats_file)
        backup_file = stats_file.with_suffix(".json.bak")
        assert backup_file.exists(), "升级前应创建 .bak 备份"
        backup_content = json.loads(backup_file.read_text())
        assert backup_content["version"] == 1


class TestTokenStatsDaily:
    """测试按日聚合功能"""

    def test_record_updates_daily(self, tmp_path, monkeypatch):
        """record() 同时更新累计和每日数据"""
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        # 固定日期为 2024-01-15
        monkeypatch.setattr(time, "strftime", lambda fmt, t=None: "2024-01-15")
        asyncio.run(ts.record("gpt-4o", 100, 50, 150))

        daily = ts.get_daily("2024-01-15")
        assert daily["gpt-4o"]["prompt_tokens"] == 100
        assert daily["gpt-4o"]["request_count"] == 1

    def test_get_daily_range(self, tmp_path, monkeypatch):
        """测试获取日期范围数据"""
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        dates = ["2024-01-10", "2024-01-11", "2024-01-12", "2024-01-13"]
        for i, date_str in enumerate(dates):
            monkeypatch.setattr(time, "strftime", lambda fmt, t=None, d=date_str: d)
            asyncio.run(ts.record("gpt-4o", (i + 1) * 10, (i + 1) * 5, (i + 1) * 15))

        range_data = ts.get_daily_range("2024-01-11", "2024-01-12")
        assert len(range_data) == 2
        assert "2024-01-11" in range_data
        assert "2024-01-12" in range_data
        assert range_data["2024-01-11"]["gpt-4o"]["prompt_tokens"] == 20
        assert "2024-01-10" not in range_data
        assert "2024-01-13" not in range_data

    def test_get_summary(self, tmp_path, monkeypatch):
        """测试汇总统计"""
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        # 模拟最近 3 天的数据
        for i in range(3):
            date_str = f"2024-01-{10 + i:02d}"
            monkeypatch.setattr(time, "strftime", lambda fmt, t=None, d=date_str: d)
            asyncio.run(ts.record("gpt-4o", 100, 50, 150))
            asyncio.run(ts.record("claude-3", 200, 100, 300))

        summary = ts.get_summary(days=3)
        assert summary["total_prompt_tokens"] == 900  # (100+200)*3
        assert summary["total_completion_tokens"] == 450  # (50+100)*3
        assert summary["total_requests"] == 6  # 2 models * 3 days
        assert "model_breakdown" in summary
        assert summary["model_breakdown"]["gpt-4o"]["request_count"] == 3

    def test_get_daily_missing_date(self, tmp_path):
        """获取不存在的日期返回空 dict"""
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        assert ts.get_daily("2024-01-01") == {}

    def test_corrupted_file_degrades_gracefully(self, tmp_path):
        """文件损坏时降级处理，不抛异常"""
        stats_file = tmp_path / "token_stats.json"
        stats_file.write_text("not valid json")
        ts = TokenStats(stats_file=stats_file)
        assert ts.get_all() == {}
        assert ts.get_daily("2024-01-01") == {}
        assert ts.get_daily_range("2024-01-01", "2024-01-02") == {}
        assert ts.get_summary(days=7) == {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_reasoning_tokens": 0,
            "total_cached_tokens": 0,
            "total_requests": 0,
            "model_breakdown": {},
        }

    def test_concurrent_daily_record(self, tmp_path):
        """测试并发写入每日数据的安全"""
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        async def worker(date_str):
            for _ in range(10):
                # 使用 monkeypatch 不方便在 async 内，直接调用
                await ts.record("gpt-4o", 1, 1, 2, date=date_str)

        async def run():
            await asyncio.gather(
                worker("2024-01-01"),
                worker("2024-01-01"),
                worker("2024-01-01"),
                worker("2024-01-01"),
                worker("2024-01-01"),
            )

        asyncio.run(run())
        daily = ts.get_daily("2024-01-01")
        assert daily["gpt-4o"]["request_count"] == 50
        assert daily["gpt-4o"]["total_tokens"] == 100


class TestTokenStatsDetailedTokens:
    """测试 reasoning_tokens 和 cached_tokens 统计"""

    def test_record_with_reasoning_and_cached_tokens(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        asyncio.run(ts.record("gpt-4o", 100, 50, 150, reasoning_tokens=30, cached_tokens=20))

        all_stats = ts.get_all()
        assert all_stats["gpt-4o"]["reasoning_tokens"] == 30
        assert all_stats["gpt-4o"]["cached_tokens"] == 20
        assert all_stats["gpt-4o"]["prompt_tokens"] == 100
        assert all_stats["gpt-4o"]["completion_tokens"] == 50
        assert all_stats["gpt-4o"]["total_tokens"] == 150
        assert all_stats["gpt-4o"]["request_count"] == 1

    def test_record_accumulates_reasoning_and_cached_tokens(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        asyncio.run(ts.record("gpt-4o", 100, 50, 150, reasoning_tokens=30, cached_tokens=20))
        asyncio.run(ts.record("gpt-4o", 50, 25, 75, reasoning_tokens=10, cached_tokens=5))

        all_stats = ts.get_all()
        assert all_stats["gpt-4o"]["reasoning_tokens"] == 40
        assert all_stats["gpt-4o"]["cached_tokens"] == 25

    def test_daily_record_with_reasoning_and_cached_tokens(self, tmp_path, monkeypatch):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        monkeypatch.setattr(time, "strftime", lambda fmt, t=None: "2024-01-15")
        asyncio.run(ts.record("gpt-4o", 100, 50, 150, reasoning_tokens=30, cached_tokens=20))

        daily = ts.get_daily("2024-01-15")
        assert daily["gpt-4o"]["reasoning_tokens"] == 30
        assert daily["gpt-4o"]["cached_tokens"] == 20

    def test_summary_includes_reasoning_and_cached_tokens(self, tmp_path, monkeypatch):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)

        for i in range(3):
            date_str = f"2024-01-{10 + i:02d}"
            monkeypatch.setattr(time, "strftime", lambda fmt, t=None, d=date_str: d)
            asyncio.run(ts.record("gpt-4o", 100, 50, 150, reasoning_tokens=30, cached_tokens=20))
            asyncio.run(ts.record("claude-3", 200, 100, 300, reasoning_tokens=60, cached_tokens=40))

        summary = ts.get_summary(days=3)
        assert summary["total_reasoning_tokens"] == 270  # (30+60)*3
        assert summary["total_cached_tokens"] == 180  # (20+40)*3
        assert summary["model_breakdown"]["gpt-4o"]["reasoning_tokens"] == 90
        assert summary["model_breakdown"]["gpt-4o"]["cached_tokens"] == 60
        assert summary["model_breakdown"]["claude-3"]["reasoning_tokens"] == 180
        assert summary["model_breakdown"]["claude-3"]["cached_tokens"] == 120

    def test_empty_summary_includes_new_fields(self, tmp_path):
        stats_file = tmp_path / "token_stats.json"
        ts = TokenStats(stats_file=stats_file)
        summary = ts.get_summary(days=7)
        assert summary["total_reasoning_tokens"] == 0
        assert summary["total_cached_tokens"] == 0
