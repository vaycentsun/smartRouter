"""日志配置模块测试"""

import logging
import tempfile
from pathlib import Path

from smart_router.utils.logging_config import get_uvicorn_log_config, setup_logging


class TestSetupLogging:
    """测试 setup_logging 函数"""

    def test_creates_log_file(self):
        """测试创建日志文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            logger = setup_logging(log_file)

            # 写入一条日志
            logger.info("测试消息")

            # 验证日志文件被创建
            assert log_file.exists()

    def test_log_format_contains_timestamp_and_level(self):
        """测试日志格式包含时间戳和等级"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            logger = setup_logging(log_file, level=logging.DEBUG)
            logger.info("测试消息123")

            # 读取日志内容
            content = log_file.read_text(encoding="utf-8")

            # 验证格式：时间戳 - name - level - message
            assert "INFO" in content
            assert "测试消息123" in content
            # 验证时间戳格式（YYYY-MM-DD HH:MM:SS）
            assert len(content) > 0

    def test_different_log_levels(self):
        """测试不同日志级别"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            logger = setup_logging(log_file, level=logging.WARNING)
            logger.info("这条不应出现")
            logger.warning("这条应该出现")

            content = log_file.read_text(encoding="utf-8")

            assert "这条不应出现" not in content
            assert "这条应该出现" in content

    def test_with_logger_name(self):
        """测试指定 logger_name"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            logger = setup_logging(log_file, logger_name="test_logger")

            # 验证返回的是指定名称的 logger
            assert logger.name == "test_logger"

            # 使用该 logger 记录日志
            logger.info("命名logger测试")

            content = log_file.read_text(encoding="utf-8")
            assert "命名logger测试" in content

    def test_without_logger_name_uses_root(self):
        """测试不指定 logger_name 时使用 root logger"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            logger = setup_logging(log_file)

            # root logger 的名称为空字符串或 'root'
            assert logger.name == "root" or logger.name == ""

    def test_creates_parent_directories(self):
        """测试自动创建父目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir1" / "subdir2" / "test.log"

            # 确保目录不存在
            assert not log_file.parent.exists()

            logger = setup_logging(log_file)
            logger.info("测试")

            # 验证目录被创建
            assert log_file.parent.exists()
            assert log_file.exists()

    def test_returns_logger_instance(self):
        """测试返回 logger 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            logger = setup_logging(log_file)

            assert isinstance(logger, logging.Logger)


class TestGetUvicornLogConfig:
    """测试 get_uvicorn_log_config 函数"""

    def test_returns_dict(self):
        """测试返回字典"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "uvicorn.log"

            config = get_uvicorn_log_config(log_file)

            assert isinstance(config, dict)

    def test_contains_required_keys(self):
        """测试返回字典包含必需的键"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "uvicorn.log"

            config = get_uvicorn_log_config(log_file)

            assert "version" in config
            assert "disable_existing_loggers" in config
            assert "formatters" in config
            assert "handlers" in config
            assert "loggers" in config

    def test_version_is_1(self):
        """测试 version 为 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "uvicorn.log"

            config = get_uvicorn_log_config(log_file)

            assert config["version"] == 1

    def test_handlers_contain_file_and_console(self):
        """测试 handlers 包含 file 和 console"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "uvicorn.log"

            config = get_uvicorn_log_config(log_file)

            assert "file" in config["handlers"]
            assert "console" in config["handlers"]

    def test_file_handler_has_correct_filename(self):
        """测试 file handler 包含正确的文件名"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "uvicorn.log"

            config = get_uvicorn_log_config(log_file)

            assert config["handlers"]["file"]["filename"] == str(log_file)

    def test_loggers_contain_uvicorn(self):
        """测试 loggers 包含 uvicorn 和 uvicorn.access"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "uvicorn.log"

            config = get_uvicorn_log_config(log_file)

            assert "uvicorn" in config["loggers"]
            assert "uvicorn.access" in config["loggers"]
