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
