import pytest
import asyncio
import json
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
        assert ts._data["version"] == 1

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
        assert content["version"] == 1
        assert "records" in content
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
