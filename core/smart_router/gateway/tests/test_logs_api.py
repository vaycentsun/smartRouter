"""日志 API 单元测试"""

import pytest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from smart_router.gateway.dashboard_api import build_dashboard_app


@pytest.fixture
def client():
    app = build_dashboard_app(static_dir=None)
    return TestClient(app)


class TestLogs:
    def test_logs_service_source(self, client, tmp_path):
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("line1\nline2\nline3\n")

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            response = client.get("/api/logs?source=service&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["lines"] == ["line1", "line2", "line3"]
            assert data["offset"] == 18
            assert data["total_size"] == 18

    def test_logs_with_offset(self, client, tmp_path):
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("line1\nline2\nline3\n")

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            # offset 在 line2 之后
            response = client.get("/api/logs?source=service&offset=12")
            assert response.status_code == 200
            data = response.json()
            assert data["lines"] == ["line3"]
            assert data["offset"] == 18

    def test_logs_file_not_exist(self, client, tmp_path):
        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": tmp_path / "nonexistent.log",
            "dashboard": tmp_path / "dashboard.log",
        }):
            response = client.get("/api/logs?source=service&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["lines"] == []
            assert data["offset"] == 0
            assert data["total_size"] == 0

    def test_logs_invalid_source(self, client):
        response = client.get("/api/logs?source=invalid&offset=0")
        assert response.status_code == 400

    def test_logs_offset_overflow(self, client, tmp_path):
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("newcontent\n")

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            # offset 大于文件大小，应该从头开始
            response = client.get("/api/logs?source=service&offset=9999")
            assert response.status_code == 200
            data = response.json()
            assert data["lines"] == ["newcontent"]
            assert data["offset"] == 11

    def test_logs_limit(self, client, tmp_path):
        log_file = tmp_path / "smart-router.log"
        lines_text = "\n".join([f"line{i}" for i in range(10)]) + "\n"
        log_file.write_text(lines_text)

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            response = client.get("/api/logs?source=service&offset=0&limit=3")
            assert response.status_code == 200
            data = response.json()
            assert len(data["lines"]) == 3
            assert data["lines"] == ["line7", "line8", "line9"]

    def test_logs_dashboard_source(self, client, tmp_path):
        log_file = tmp_path / "dashboard.log"
        log_file.write_text("dashboard line\n")

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": tmp_path / "smart-router.log",
            "dashboard": log_file,
        }):
            response = client.get("/api/logs?source=dashboard&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["lines"] == ["dashboard line"]

    def test_logs_with_level_filter(self, client, tmp_path):
        """测试 level=ERROR 筛选只返回 ERROR 及以上等级的日志"""
        log_file = tmp_path / "smart-router.log"
        log_content = """2026-05-07 14:23:01,234 - smart_router.gateway - INFO - Info message
2026-05-07 14:23:02,345 - smart_router.gateway - WARNING - Warning message
2026-05-07 14:23:03,456 - smart_router.gateway - ERROR - Error message
2026-05-07 14:23:04,567 - smart_router.gateway - CRITICAL - Critical message
"""
        log_file.write_text(log_content)

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            response = client.get("/api/logs?source=service&offset=0&level=ERROR")
            assert response.status_code == 200
            data = response.json()
            # ERROR 及以上应该只有 ERROR 和 CRITICAL
            assert len(data["structured_lines"]) == 2
            levels = [s["level"] for s in data["structured_lines"]]
            assert "INFO" not in levels
            assert "WARNING" not in levels
            assert "ERROR" in levels
            assert "CRITICAL" in levels

    def test_logs_structured_lines(self, client, tmp_path):
        """验证 structured_lines 字段包含 timestamp、level、name、message"""
        log_file = tmp_path / "smart-router.log"
        log_content = """2026-05-07 14:23:01,234 - smart_router.gateway - INFO - Server started
"""
        log_file.write_text(log_content)

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            response = client.get("/api/logs?source=service&offset=0&level=ALL")
            assert response.status_code == 200
            data = response.json()
            assert "structured_lines" in data
            assert len(data["structured_lines"]) == 1
            entry = data["structured_lines"][0]
            # 验证所有必需字段存在
            assert "timestamp" in entry
            assert "level" in entry
            assert "name" in entry
            assert "message" in entry
            # 验证字段值
            assert entry["timestamp"] == "2026-05-07 14:23:01,234"
            assert entry["level"] == "INFO"
            assert entry["name"] == "smart_router.gateway"
            assert entry["message"] == "Server started"

    def test_logs_invalid_level(self, client, tmp_path):
        """验证无效 level 参数返回 400 错误"""
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("line1\n")

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            response = client.get("/api/logs?source=service&offset=0&level=INVALID_LEVEL")
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "Invalid log level" in data["detail"]

    def test_logs_level_all(self, client, tmp_path):
        """验证默认 level=ALL 返回所有日志"""
        log_file = tmp_path / "smart-router.log"
        log_content = """2026-05-07 14:23:01,234 - smart_router.gateway - DEBUG - Debug message
2026-05-07 14:23:02,345 - smart_router.gateway - INFO - Info message
2026-05-07 14:23:03,456 - smart_router.gateway - ERROR - Error message
"""
        log_file.write_text(log_content)

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            # 不传 level 参数，应该默认 ALL
            response = client.get("/api/logs?source=service&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert len(data["structured_lines"]) == 3

            # 显式传 level=ALL
            response = client.get("/api/logs?source=service&offset=0&level=ALL")
            assert response.status_code == 200
            data = response.json()
            assert len(data["structured_lines"]) == 3

    def test_logs_structured_lines_old_format(self, client, tmp_path):
        """验证旧格式日志解析（无时间戳/等级）"""
        log_file = tmp_path / "smart-router.log"
        # 旧格式：没有时间戳和等级
        log_content = """Simple log line without format
Another old format line
"""
        log_file.write_text(log_content)

        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            response = client.get("/api/logs?source=service&offset=0&level=ALL")
            assert response.status_code == 200
            data = response.json()
            assert len(data["structured_lines"]) == 2
            # 旧格式应该仍能解析，只是字段为空或默认值
            entry = data["structured_lines"][0]
            assert "timestamp" in entry
            assert "level" in entry
            assert "name" in entry
            assert "message" in entry
            # 旧格式的 message 应该是整行内容
            assert entry["message"] == "Simple log line without format"


class TestReadLogLinesStructured:
    """测试 read_log_lines 的结构化输出和等级筛选"""

    def test_structured_lines_returned(self, tmp_path):
        """测试返回结果包含 structured_lines 字段"""
        from smart_router.gateway.dashboard_api import read_log_lines, LogReadResult
        
        log_file = tmp_path / "smart-router.log"
        # 写入符合新格式的日志
        log_content = """2026-05-07 14:23:01,234 - smart_router.gateway - INFO - Server started
2026-05-07 14:23:02,345 - smart_router.selector - DEBUG - Selecting model
2026-05-07 14:23:03,456 - smart_router.gateway - ERROR - Connection failed
"""
        log_file.write_text(log_content)
        
        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            result = read_log_lines("service", offset=0, limit=500, level="ALL")
            
            assert isinstance(result, LogReadResult)
            assert hasattr(result, "structured_lines")
            assert len(result.structured_lines) == 3
            # 检查结构化字段
            assert result.structured_lines[0]["level"] == "INFO"
            assert result.structured_lines[0]["name"] == "smart_router.gateway"
            assert result.structured_lines[0]["message"] == "Server started"
            assert result.structured_lines[0]["timestamp"] == "2026-05-07 14:23:01,234"

    def test_level_filter_info(self, tmp_path):
        """测试 level=INFO 筛选（只返回 INFO 及以上）"""
        from smart_router.gateway.dashboard_api import read_log_lines
        
        log_file = tmp_path / "smart-router.log"
        log_content = """2026-05-07 14:23:01,234 - smart_router.gateway - DEBUG - Debug message
2026-05-07 14:23:02,345 - smart_router.gateway - INFO - Info message
2026-05-07 14:23:03,456 - smart_router.gateway - WARNING - Warning message
2026-05-07 14:23:04,567 - smart_router.gateway - ERROR - Error message
"""
        log_file.write_text(log_content)
        
        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            result = read_log_lines("service", offset=0, limit=500, level="INFO")
            
            # DEBUG (10) < INFO (20)，应该被过滤
            assert len(result.structured_lines) == 3
            levels = [s["level"] for s in result.structured_lines]
            assert "DEBUG" not in levels
            assert "INFO" in levels
            assert "WARNING" in levels
            assert "ERROR" in levels

    def test_level_filter_error(self, tmp_path):
        """测试 level=ERROR 筛选（只返回 ERROR 及以上）"""
        from smart_router.gateway.dashboard_api import read_log_lines
        
        log_file = tmp_path / "smart-router.log"
        log_content = """2026-05-07 14:23:01,234 - smart_router.gateway - INFO - Info message
2026-05-07 14:23:02,345 - smart_router.gateway - WARNING - Warning message
2026-05-07 14:23:03,456 - smart_router.gateway - ERROR - Error message
2026-05-07 14:23:04,567 - smart_router.gateway - CRITICAL - Critical message
"""
        log_file.write_text(log_content)
        
        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            result = read_log_lines("service", offset=0, limit=500, level="ERROR")
            
            # INFO, WARNING < ERROR，应该被过滤
            assert len(result.structured_lines) == 2
            levels = [s["level"] for s in result.structured_lines]
            assert "INFO" not in levels
            assert "WARNING" not in levels
            assert "ERROR" in levels
            assert "CRITICAL" in levels

    def test_level_all_returns_all(self, tmp_path):
        """测试 level=ALL 返回所有日志"""
        from smart_router.gateway.dashboard_api import read_log_lines
        
        log_file = tmp_path / "smart-router.log"
        log_content = """2026-05-07 14:23:01,234 - smart_router.gateway - DEBUG - Debug message
2026-05-07 14:23:02,345 - smart_router.gateway - INFO - Info message
"""
        log_file.write_text(log_content)
        
        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            result = read_log_lines("service", offset=0, limit=500, level="ALL")
            
            assert len(result.structured_lines) == 2

    def test_api_returns_structured_lines(self, client, tmp_path):
        """测试 API 端点返回 structured_lines"""
        log_file = tmp_path / "smart-router.log"
        log_content = """2026-05-07 14:23:01,234 - smart_router.gateway - INFO - Server started
"""
        log_file.write_text(log_content)
        
        with patch("smart_router.gateway.dashboard_api.LOG_FILE_MAP", {
            "service": log_file,
            "dashboard": tmp_path / "dashboard.log",
        }):
            response = client.get("/api/logs?source=service&offset=0&level=ALL")
            assert response.status_code == 200
            data = response.json()
            assert "structured_lines" in data
            assert len(data["structured_lines"]) == 1
            assert data["structured_lines"][0]["level"] == "INFO"
