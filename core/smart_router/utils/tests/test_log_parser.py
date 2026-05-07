"""日志解析器单元测试"""

import pytest
import logging

from smart_router.utils.log_parser import LogEntry, parse_log_line


class TestParseLogLine:
    """测试 parse_log_line 函数"""

    def test_parse_new_format_complete(self):
        """测试解析完整的新格式日志行"""
        line = "2026-05-07 14:23:01,234 - smart_router.gateway - INFO - 请求处理完成"
        
        entry = parse_log_line(line)
        
        assert entry.timestamp == "2026-05-07 14:23:01,234"
        assert entry.level == "INFO"
        assert entry.levelno == logging.INFO
        assert entry.name == "smart_router.gateway"
        assert entry.message == "请求处理完成"
        assert entry.raw == line

    def test_parse_new_format_debug(self):
        """测试解析 DEBUG 级别的新格式日志"""
        line = "2026-05-07 10:00:00,123 - smart_router.auth - DEBUG - 调试信息"
        
        entry = parse_log_line(line)
        
        assert entry.timestamp == "2026-05-07 10:00:00,123"
        assert entry.level == "DEBUG"
        assert entry.levelno == logging.DEBUG
        assert entry.name == "smart_router.auth"
        assert entry.message == "调试信息"

    def test_parse_new_format_warning(self):
        """测试解析 WARNING 级别的新格式日志"""
        line = "2026-05-07 11:11:11,111 - smart_router.proxy - WARNING - 警告信息"
        
        entry = parse_log_line(line)
        
        assert entry.level == "WARNING"
        assert entry.levelno == logging.WARNING

    def test_parse_new_format_error(self):
        """测试解析 ERROR 级别的新格式日志"""
        line = "2026-05-07 12:12:12,222 - smart_router.server - ERROR - 错误信息"
        
        entry = parse_log_line(line)
        
        assert entry.level == "ERROR"
        assert entry.levelno == logging.ERROR

    def test_parse_new_format_critical(self):
        """测试解析 CRITICAL 级别的新格式日志"""
        line = "2026-05-07 13:13:13,333 - smart_router.core - CRITICAL - 严重错误"
        
        entry = parse_log_line(line)
        
        assert entry.level == "CRITICAL"
        assert entry.levelno == logging.CRITICAL

    def test_parse_new_format_with_extra_dashes(self):
        """测试解析消息中包含破折号的新格式日志"""
        line = "2026-05-07 14:23:01,234 - smart_router.gateway - INFO - 请求失败 - 连接超时"
        
        entry = parse_log_line(line)
        
        assert entry.message == "请求失败 - 连接超时"

    def test_parse_old_format_plain_text(self):
        """测试兼容旧格式：纯文本"""
        line = "这是一条旧格式的日志"
        
        entry = parse_log_line(line)
        
        assert entry.timestamp is None
        assert entry.level == "INFO"
        assert entry.levelno == logging.INFO
        assert entry.name is None
        assert entry.message == "这是一条旧格式的日志"
        assert entry.raw == line

    def test_parse_old_format_empty_line(self):
        """测试兼容旧格式：空行"""
        line = ""
        
        entry = parse_log_line(line)
        
        assert entry.timestamp is None
        assert entry.level == "INFO"
        assert entry.message == ""

    def test_parse_old_format_whitespace(self):
        """测试兼容旧格式：带空白字符的行"""
        line = "  带空白的旧格式日志  "
        
        entry = parse_log_line(line)
        
        assert entry.message == "带空白的旧格式日志"

    def test_parse_new_format_multiline_message(self):
        """测试解析多行消息（单行处理）"""
        line = "2026-05-07 14:23:01,234 - smart_router.gateway - INFO - 第一行消息"
        
        entry = parse_log_line(line)
        
        assert entry.message == "第一行消息"

    def test_log_entry_dataclass(self):
        """测试 LogEntry 数据类"""
        entry = LogEntry(
            timestamp="2026-05-07 14:23:01,234",
            level="INFO",
            levelno=logging.INFO,
            name="smart_router.gateway",
            message="测试消息",
            raw="原始行",
        )
        
        assert entry.timestamp == "2026-05-07 14:23:01,234"
        assert entry.level == "INFO"
        assert entry.levelno == logging.INFO
        assert entry.name == "smart_router.gateway"
        assert entry.message == "测试消息"
        assert entry.raw == "原始行"
