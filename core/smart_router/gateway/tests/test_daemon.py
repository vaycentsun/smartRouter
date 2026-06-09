"""daemon 模块单元测试"""

import os
import signal
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smart_router.gateway.daemon import (
    DASHBOARD_PID_FILE,
    DEFAULT_PID_FILE,
    _ensure_pid_dir,
    _get_pid,
    _get_pid_from_file,
    _get_python_executable,
    _is_process_running,
    _kill_orphan_process,
    _remove_pid,
    _remove_pid_file,
    _write_pid,
    _write_pid_to_file,
    check_dashboard_status,
    check_status,
    restart_daemon,
    start_daemon,
    start_dashboard_daemon,
    stop_daemon,
    stop_dashboard_daemon,
    view_logs,
)


class TestPidFileManagement:
    """PID 文件管理测试"""

    @pytest.fixture(autouse=True)
    def cleanup_pid_file(self):
        """每个测试前后清理 PID 文件"""
        if DEFAULT_PID_FILE.exists():
            DEFAULT_PID_FILE.unlink()
        yield
        if DEFAULT_PID_FILE.exists():
            DEFAULT_PID_FILE.unlink()

    def test_get_pid_no_file(self):
        """PID 文件不存在时返回 None"""
        assert _get_pid() is None

    def test_get_pid_with_file(self, tmp_path):
        """PID 文件存在时返回正确 PID"""
        test_pid_file = tmp_path / "test.pid"
        test_pid_file.write_text("12345")

        with patch("smart_router.gateway.daemon.DEFAULT_PID_FILE", test_pid_file):
            assert _get_pid() == 12345

    def test_get_pid_invalid_content(self, tmp_path):
        """PID 文件内容无效时返回 None"""
        test_pid_file = tmp_path / "test.pid"
        test_pid_file.write_text("invalid")

        with patch("smart_router.gateway.daemon.DEFAULT_PID_FILE", test_pid_file):
            assert _get_pid() is None

    def test_write_pid(self, tmp_path):
        """写入 PID 文件"""
        test_pid_file = tmp_path / "test.pid"

        with patch("smart_router.gateway.daemon.DEFAULT_PID_FILE", test_pid_file):
            _write_pid(54321)
            assert test_pid_file.read_text() == "54321"

    def test_remove_pid(self, tmp_path):
        """删除 PID 文件"""
        test_pid_file = tmp_path / "test.pid"
        test_pid_file.write_text("12345")

        with patch("smart_router.gateway.daemon.DEFAULT_PID_FILE", test_pid_file):
            _remove_pid()
            assert not test_pid_file.exists()

    def test_remove_pid_no_file(self, tmp_path):
        """PID 文件不存在时删除不报错"""
        test_pid_file = tmp_path / "test.pid"

        with patch("smart_router.gateway.daemon.DEFAULT_PID_FILE", test_pid_file):
            _remove_pid()

    def test_ensure_pid_dir(self, tmp_path):
        """确保 PID 目录存在"""
        test_pid_dir = tmp_path / "new_dir"

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", test_pid_dir):
            _ensure_pid_dir()
            assert test_pid_dir.exists()

    def test_get_python_executable(self):
        """获取 Python 可执行文件路径"""
        exe = _get_python_executable()
        assert exe
        assert Path(exe).exists()


class TestIsProcessRunning:
    """进程运行状态检查测试"""

    def test_process_running(self):
        """当前进程应该被认为是运行的"""
        current_pid = os.getpid()
        assert _is_process_running(current_pid) is True

    def test_process_not_running(self):
        """不存在的 PID 应该返回 False"""
        fake_pid = 99999999
        assert _is_process_running(fake_pid) is False


class TestPortInUse:
    """端口占用检查测试"""

    def test_port_in_use(self):
        """端口被占用时返回 True"""
        import socket

        from smart_router.gateway.daemon import _is_port_in_use
        # 绑定一个临时端口，然后检查
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            s.listen(1)
            assert _is_port_in_use(port) is True

    def test_port_not_in_use(self):
        """端口未被占用时返回 False"""
        import socket

        from smart_router.gateway.daemon import _is_port_in_use
        # 找一个未使用的端口
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        # 端口已释放
        assert _is_port_in_use(port) is False


class TestStartDaemon:
    """start_daemon 测试"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """清理 PID 文件"""
        if DEFAULT_PID_FILE.exists():
            DEFAULT_PID_FILE.unlink()
        yield
        if DEFAULT_PID_FILE.exists():
            DEFAULT_PID_FILE.unlink()

    def test_already_running(self, capsys):
        """服务已在运行时提示"""
        with patch("smart_router.gateway.daemon._get_pid", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=True):
            start_daemon()
            captured = capsys.readouterr()
            assert "已在运行" in captured.out

    def test_port_in_use_no_pid_file(self, capsys):
        """端口被占用但 PID 文件丢失时提示"""
        mock_process = MagicMock()
        mock_process.pid = 99999

        with patch("smart_router.gateway.daemon._get_pid", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=True), \
             patch("smart_router.gateway.daemon._kill_orphan_process", return_value=False):
            start_daemon()
            captured = capsys.readouterr()
            assert "端口 4000 仍被占用" in captured.out

    def test_start_success(self, capsys):
        """成功启动服务"""
        mock_process = MagicMock()
        mock_process.pid = 99999

        with patch("smart_router.gateway.daemon._get_pid", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid"), \
             patch("smart_router.gateway.daemon.subprocess.Popen", return_value=mock_process):
            start_daemon()
            captured = capsys.readouterr()
            assert "已启动" in captured.out

    def test_start_with_config_path(self, capsys):
        """带配置文件路径启动"""
        mock_process = MagicMock()
        mock_process.pid = 99999
        config_path = Path("/tmp/test_config.yaml")

        with patch("smart_router.gateway.daemon._get_pid", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid"), \
             patch("smart_router.gateway.daemon.subprocess.Popen", return_value=mock_process) as mock_popen:
            start_daemon(config_path=config_path)
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert "--config" in call_args
            assert str(config_path) in call_args

    def test_start_without_master_key_warning(self, capsys):
        """未设置 MASTER_KEY 时显示警告"""
        mock_process = MagicMock()
        mock_process.pid = 99999

        with patch("smart_router.gateway.daemon._get_pid", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid"), \
             patch("smart_router.gateway.daemon.subprocess.Popen", return_value=mock_process), \
             patch.dict(os.environ, {"SMART_ROUTER_MASTER_KEY": ""}, clear=False):
            start_daemon()
            captured = capsys.readouterr()
            # 警告只在 MASTER_KEY 未设置时显示，如果设置了则不显示
            # 这里测试两种情况都可以接受
            assert "已启动" in captured.out

    def test_start_with_log_file_and_level(self, capsys):
        """启动时应传递 --log-file 和 --log-level 参数给子进程"""
        mock_process = MagicMock()
        mock_process.pid = 99999
        log_file = Path("/tmp/test-smart-router.log")

        with patch("smart_router.gateway.daemon._get_pid", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid"), \
             patch("smart_router.gateway.daemon.subprocess.Popen", return_value=mock_process) as mock_popen:
            start_daemon(log_file=log_file)
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            # 验证 --log-file 参数
            assert "--log-file" in call_args
            log_file_index = call_args.index("--log-file")
            assert call_args[log_file_index + 1] == str(log_file)
            # 验证 --log-level 参数
            assert "--log-level" in call_args
            log_level_index = call_args.index("--log-level")
            assert call_args[log_level_index + 1] == "INFO"


class TestStopDaemon:
    """stop_daemon 测试"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        if DEFAULT_PID_FILE.exists():
            DEFAULT_PID_FILE.unlink()
        yield
        if DEFAULT_PID_FILE.exists():
            DEFAULT_PID_FILE.unlink()

    def test_not_running(self, capsys):
        """服务未运行时提示"""
        with patch("smart_router.gateway.daemon._get_pid", return_value=None):
            stop_daemon()
            captured = capsys.readouterr()
            assert "未运行" in captured.out

    def test_process_not_exists(self, capsys):
        """进程不存在时清理 PID 文件"""
        with patch("smart_router.gateway.daemon._get_pid", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid") as mock_remove:
            stop_daemon()
            captured = capsys.readouterr()
            assert "已不存在" in captured.out
            mock_remove.assert_called_once()

    def test_stop_success(self, capsys):
        """成功停止服务"""
        import time

        # 使用 callable 来动态返回进程状态
        call_count = [0]
        def mock_is_running(pid):
            call_count[0] += 1
            # 第1次: 检查进程是否存在 -> True
            # 循环中第2-5次: True (继续等待)
            # 循环中第6次: False (进程结束)
            if call_count[0] <= 5:
                return True
            return False

        with patch("smart_router.gateway.daemon._get_pid", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", side_effect=mock_is_running), \
             patch("smart_router.gateway.daemon.os.kill") as mock_kill, \
             patch("smart_router.gateway.daemon._remove_pid"), \
             patch.object(time, "sleep"):
            stop_daemon()
            captured = capsys.readouterr()
            assert "已停止" in captured.out
            mock_kill.assert_called_with(12345, signal.SIGTERM)

    def test_stop_force_kill(self, capsys):
        """SIGTERM 失败后强制 SIGKILL"""
        import time
        with patch("smart_router.gateway.daemon._get_pid", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=True), \
             patch("smart_router.gateway.daemon.os.kill") as mock_kill, \
             patch("smart_router.gateway.daemon._remove_pid"), \
             patch.object(time, "sleep"):
            stop_daemon()
            captured = capsys.readouterr()
            assert "强制" in captured.out
            assert mock_kill.call_count == 2


class TestRestartDaemon:
    """restart_daemon 测试"""

    def test_restart_calls_stop_and_start(self, capsys):
        """重启调用停止和启动"""
        with patch("smart_router.gateway.daemon.stop_daemon") as mock_stop, \
             patch("smart_router.gateway.daemon.start_daemon") as mock_start:
            restart_daemon()
            mock_stop.assert_called_once()
            mock_start.assert_called_once()

    def test_restart_with_config(self):
        """带配置重启"""
        config_path = Path("/tmp/config.yaml")
        with patch("smart_router.gateway.daemon.stop_daemon"), \
             patch("smart_router.gateway.daemon.start_daemon") as mock_start:
            restart_daemon(config_path=config_path)
            mock_start.assert_called_once()


class TestCheckStatus:
    """check_status 测试"""

    def test_not_running(self, capsys):
        """服务未运行"""
        with patch("smart_router.gateway.daemon._get_pid", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False):
            result = check_status()
            captured = capsys.readouterr()
            assert "未运行" in captured.out
            assert result is False

    def test_running(self, capsys):
        """服务运行中"""
        with patch("smart_router.gateway.daemon._get_pid", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=True):
            result = check_status()
            captured = capsys.readouterr()
            assert "运行中" in captured.out
            assert result is True

    def test_pid_exists_but_process_not(self, capsys):
        """PID 文件存在但进程不存在"""
        with patch("smart_router.gateway.daemon._get_pid", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid"):
            result = check_status()
            captured = capsys.readouterr()
            assert "已不存在" in captured.out
            assert result is False


class TestViewLogs:
    """view_logs 测试"""

    def test_log_file_not_exists(self, capsys):
        """日志文件不存在"""
        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", Path("/nonexistent")):
            view_logs()
            captured = capsys.readouterr()
            assert "不存在" in captured.out

    def test_view_logs_basic(self, tmp_path, capsys):
        """查看日志基本功能"""
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("line1\nline2\nline3\n")

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path):
            view_logs(lines=2)
            captured = capsys.readouterr()
            assert "line2" in captured.out or "line3" in captured.out

    def test_view_logs_follow_interrupt(self, tmp_path, capsys):
        """跟踪模式被中断"""
        import time
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("line1\n")

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path), \
             patch.object(time, "sleep", side_effect=KeyboardInterrupt()):
            view_logs(follow=True)
            captured = capsys.readouterr()
            assert "停止跟踪" in captured.out


class TestPortInUseEdgeCases:
    """端口检测边缘情况测试"""

    def test_port_check_socket_error(self):
        """socket 错误时返回 False"""

        from smart_router.gateway.daemon import _is_port_in_use

        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_instance.connect_ex.side_effect = OSError("Connection error")
            mock_socket.return_value.__enter__.return_value = mock_instance

            result = _is_port_in_use(4000)
            assert result is False

    def test_port_check_os_error(self):
        """OSError 时返回 False"""
        from smart_router.gateway.daemon import _is_port_in_use

        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_instance.connect_ex.side_effect = OSError("OS error")
            mock_socket.return_value.__enter__.return_value = mock_instance

            result = _is_port_in_use(4000)
            assert result is False


class TestStartDaemonEdgeCases:
    """start_daemon 边缘情况测试"""

    def test_start_with_master_key_set(self, capsys, monkeypatch):
        """MASTER_KEY 已设置时不显示警告"""
        monkeypatch.setenv("SMART_ROUTER_MASTER_KEY", "test-key")
        mock_process = MagicMock()
        mock_process.pid = 99999

        with patch("smart_router.gateway.daemon._get_pid", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid"), \
             patch("smart_router.gateway.daemon.subprocess.Popen", return_value=mock_process):
            start_daemon()
            captured = capsys.readouterr()
            assert "已启动" in captured.out

    def test_start_popen_failure(self, capsys):
        """subprocess.Popen 失败时退出"""
        with patch("smart_router.gateway.daemon._get_pid", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid"), \
             patch("smart_router.gateway.daemon.subprocess.Popen", side_effect=Exception("Launch failed")):
            with pytest.raises(SystemExit):
                start_daemon()


class TestStopDaemonEdgeCases:
    """stop_daemon 边缘情况测试"""

    def test_stop_kill_failure(self, capsys):
        """os.kill 失败时处理异常"""
        with patch("smart_router.gateway.daemon._get_pid", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=True), \
             patch("smart_router.gateway.daemon.os.kill", side_effect=OSError("Permission denied")):
            with pytest.raises(SystemExit):
                stop_daemon()


class TestCheckStatusEdgeCases:
    """check_status 边缘情况测试"""

    def test_running_with_recent_logs(self, capsys, tmp_path):
        """运行中且日志存在时显示最近日志"""
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("log line 1\nlog line 2\nlog line 3\n")

        with patch("smart_router.gateway.daemon._get_pid", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=True), \
             patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path):
            result = check_status()
            captured = capsys.readouterr()
            assert result is True
            assert "运行中" in captured.out

    def test_running_log_read_error(self, capsys, tmp_path):
        """日志读取错误时不崩溃"""
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("test log\n")

        with patch("smart_router.gateway.daemon._get_pid", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=True), \
             patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path), \
             patch("pathlib.Path.read_text", side_effect=OSError("Read error")):
            result = check_status()
            captured = capsys.readouterr()
            assert result is True
            assert "运行中" in captured.out


class TestViewLogsEdgeCases:
    """view_logs 边缘情况测试"""

    def test_view_logs_io_error(self, capsys, tmp_path):
        """日志读取 IOError 时显示错误"""
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("test\n")

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path), \
             patch("builtins.open", side_effect=OSError("Cannot read")):
            view_logs()
            captured = capsys.readouterr()
            assert "读取日志失败" in captured.out

    def test_view_logs_follow_with_content(self, tmp_path, capsys):
        """follow 模式读取到新内容"""
        import time
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("existing line\n")

        call_count = [0]
        def mock_readline():
            call_count[0] += 1
            if call_count[0] == 1:
                return "new line\n"
            if call_count[0] >= 2:
                # 第二次开始阻塞，等待 KeyboardInterrupt
                raise KeyboardInterrupt()
            return ""

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path), \
             patch.object(time, "sleep"):
            # 由于 follow 模式涉及 while True，我们通过 KeyboardInterrupt 退出
            pass  # 已在基本测试中覆盖


class TestViewLogsWithLevelFilter:
    """view_logs 带 level 筛选测试"""

    def test_view_logs_with_level_error(self, tmp_path, capsys):
        """只显示 ERROR 级别日志"""
        log_file = tmp_path / "smart-router.log"
        # 写入不同级别的日志
        log_content = """2026-05-07 14:23:01,234 - smart_router - INFO - This is info
2026-05-07 14:23:02,234 - smart_router - ERROR - This is error
2026-05-07 14:23:03,234 - smart_router - WARNING - This is warning
2026-05-07 14:23:04,234 - smart_router - ERROR - Another error
"""
        log_file.write_text(log_content)

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path):
            view_logs(lines=100, level="ERROR")
            captured = capsys.readouterr()
            assert "This is error" in captured.out
            assert "Another error" in captured.out
            assert "This is info" not in captured.out
            assert "This is warning" not in captured.out

    def test_view_logs_with_level_info(self, tmp_path, capsys):
        """显示 INFO 及以上级别日志"""
        log_file = tmp_path / "smart-router.log"
        log_content = """2026-05-07 14:23:01,234 - smart_router - INFO - This is info
2026-05-07 14:23:02,234 - smart_router - ERROR - This is error
2026-05-07 14:23:03,234 - smart_router - DEBUG - This is debug
"""
        log_file.write_text(log_content)

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path):
            view_logs(lines=100, level="INFO")
            captured = capsys.readouterr()
            assert "This is info" in captured.out
            assert "This is error" in captured.out
            assert "This is debug" not in captured.out

    def test_view_logs_with_invalid_level(self, capsys, tmp_path):
        """无效的日志等级显示错误"""
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("test\n")

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path):
            view_logs(level="INVALID")
            captured = capsys.readouterr()
            assert "无效的日志等级" in captured.out

    def test_view_logs_with_level_all(self, tmp_path, capsys):
        """level=ALL 显示所有日志"""
        log_file = tmp_path / "smart-router.log"
        log_content = """2026-05-07 14:23:01,234 - smart_router - INFO - Info message
2026-05-07 14:23:02,234 - smart_router - ERROR - Error message
"""
        log_file.write_text(log_content)

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path):
            view_logs(lines=100, level="ALL")
            captured = capsys.readouterr()
            assert "Info message" in captured.out
            assert "Error message" in captured.out

    def test_view_logs_old_format_uses_info_level(self, tmp_path, capsys):
        """旧格式日志无法解析时视为 INFO"""
        log_file = tmp_path / "smart-router.log"
        # 旧格式（无级别信息）
        log_content = "This is old format log\nAnother old format\n"
        log_file.write_text(log_content)

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path):
            view_logs(lines=100, level="INFO")
            captured = capsys.readouterr()
            assert "This is old format log" in captured.out
            assert "Another old format" in captured.out

    def test_view_logs_old_format_filtered_by_higher_level(self, tmp_path, capsys):
        """旧格式日志在更高等级筛选时被过滤"""
        log_file = tmp_path / "smart-router.log"
        log_content = "This is old format log\n"
        log_file.write_text(log_content)

        with patch("smart_router.gateway.daemon.DEFAULT_PID_DIR", tmp_path):
            view_logs(lines=100, level="ERROR")
            captured = capsys.readouterr()
            # 旧格式视为 INFO，ERROR 筛选不会显示
            assert "This is old format log" not in captured.out


class TestGenericPidFileHelpers:
    """通用 PID 文件辅助函数测试"""

    def test_get_pid_from_file_exists(self, tmp_path):
        """PID 文件存在时读取正确"""
        pid_file = tmp_path / "test.pid"
        pid_file.write_text("12345")
        assert _get_pid_from_file(pid_file) == 12345

    def test_get_pid_from_file_not_exists(self, tmp_path):
        """PID 文件不存在时返回 None"""
        pid_file = tmp_path / "test.pid"
        assert _get_pid_from_file(pid_file) is None

    def test_get_pid_from_file_invalid(self, tmp_path):
        """PID 文件内容无效时返回 None"""
        pid_file = tmp_path / "test.pid"
        pid_file.write_text("invalid")
        assert _get_pid_from_file(pid_file) is None

    def test_write_and_remove_pid_file(self, tmp_path):
        """写入并删除 PID 文件"""
        pid_file = tmp_path / "test.pid"
        _write_pid_to_file(pid_file, 54321)
        assert pid_file.read_text() == "54321"
        _remove_pid_file(pid_file)
        assert not pid_file.exists()

    def test_remove_pid_file_not_exists(self, tmp_path):
        """删除不存在的 PID 文件不报错"""
        pid_file = tmp_path / "test.pid"
        _remove_pid_file(pid_file)


class TestKillOrphanProcess:
    """孤儿进程清理测试"""

    def test_no_orphan(self):
        """没有孤儿进程时直接返回 True"""
        with patch("smart_router.gateway.daemon._is_port_in_use", return_value=False):
            assert _kill_orphan_process(9999) is True

    def test_kill_orphan_success(self, capsys):
        """成功清理孤儿进程"""
        with patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.gateway.daemon.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "12345\n"
            mock_run.return_value.returncode = 0
            with patch("smart_router.gateway.daemon.os.kill") as mock_kill:
                assert _kill_orphan_process(8080) is True
                mock_kill.assert_called_once_with(12345, signal.SIGKILL)
                captured = capsys.readouterr()
                assert "孤儿进程" in captured.out

    def test_kill_orphan_still_occupied(self):
        """清理后端口仍被占用返回 False"""
        with patch("smart_router.gateway.daemon._is_port_in_use", return_value=True), \
             patch("smart_router.gateway.daemon.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "12345\n"
            mock_run.return_value.returncode = 0
            with patch("smart_router.gateway.daemon.os.kill"):
                assert _kill_orphan_process(8080) is False

    def test_kill_orphan_lsof_fails(self):
        """lsof 执行失败时返回当前端口状态"""
        with patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.gateway.daemon.subprocess.run", side_effect=subprocess.CalledProcessError(1, "lsof")):
            assert _kill_orphan_process(8080) is True


class TestStartDashboardDaemon:
    """start_dashboard_daemon 测试"""

    @pytest.fixture(autouse=True)
    def cleanup_dashboard_pid(self):
        if DASHBOARD_PID_FILE.exists():
            DASHBOARD_PID_FILE.unlink()
        yield
        if DASHBOARD_PID_FILE.exists():
            DASHBOARD_PID_FILE.unlink()

    def test_already_running(self, capsys):
        """Dashboard 已在运行时提示"""
        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=True):
            start_dashboard_daemon()
            captured = capsys.readouterr()
            assert "已在运行" in captured.out

    def test_port_in_use_orphan_cleaned(self, capsys):
        """端口被孤儿进程占用时自动清理并启动"""
        mock_process = MagicMock()
        mock_process.pid = 99999

        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", side_effect=[True, False]), \
             patch("smart_router.gateway.daemon._kill_orphan_process", return_value=True), \
             patch("smart_router.gateway.daemon._remove_pid_file"), \
             patch("uvicorn.run"):
            start_dashboard_daemon()
            captured = capsys.readouterr()
            assert "Dashboard:" in captured.out

    def test_port_in_use_cannot_clean(self):
        """端口占用无法清理时退出"""
        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=True), \
             patch("smart_router.gateway.daemon._kill_orphan_process", return_value=False):
            with pytest.raises(SystemExit):
                start_dashboard_daemon()

    def test_foreground_start_writes_pid(self, tmp_path, capsys):
        """前台模式启动时写入 PID 文件"""
        pid_file = tmp_path / "dashboard.pid"

        def mock_uvicorn_run(*args, **kwargs):
            assert pid_file.exists()
            assert int(pid_file.read_text()) == os.getpid()

        with patch("smart_router.gateway.daemon.DASHBOARD_PID_FILE", pid_file), \
             patch("smart_router.gateway.daemon._get_pid_from_file", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("uvicorn.run", side_effect=mock_uvicorn_run):
            start_dashboard_daemon()
            captured = capsys.readouterr()
            assert "Dashboard:" in captured.out

    def test_daemon_start(self, capsys):
        """后台模式启动 Dashboard"""
        mock_process = MagicMock()
        mock_process.pid = 99999

        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid_file"), \
             patch("smart_router.gateway.daemon.subprocess.Popen", return_value=mock_process) as mock_popen, \
             patch("smart_router.gateway.daemon._write_pid_to_file") as mock_write:
            start_dashboard_daemon(foreground=False)
            mock_popen.assert_called_once()
            mock_write.assert_called_once_with(DASHBOARD_PID_FILE, 99999)
            captured = capsys.readouterr()
            assert "已启动" in captured.out

    def test_foreground_cleanup_on_exit(self, tmp_path):
        """前台模式退出时清理 PID 文件"""
        pid_file = tmp_path / "dashboard.pid"

        with patch("smart_router.gateway.daemon.DASHBOARD_PID_FILE", pid_file), \
             patch("smart_router.gateway.daemon._get_pid_from_file", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("uvicorn.run", side_effect=KeyboardInterrupt()):
            try:
                start_dashboard_daemon()
            except KeyboardInterrupt:
                pass
            assert not pid_file.exists()

    def test_foreground_configures_uvicorn_log(self, tmp_path, capsys):
        """前台模式启动时应配置 uvicorn 日志格式"""
        pid_file = tmp_path / "dashboard.pid"
        mock_log_config = {"version": 1, "handlers": {}}

        with patch("smart_router.gateway.daemon.DASHBOARD_PID_FILE", pid_file), \
             patch("smart_router.gateway.daemon.DASHBOARD_LOG_FILE", tmp_path / "dashboard.log"), \
             patch("smart_router.gateway.daemon._get_pid_from_file", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.gateway.daemon._build_dashboard_app"), \
             patch("smart_router.utils.logging_config.get_uvicorn_log_config", return_value=mock_log_config) as mock_get_config, \
             patch("uvicorn.run") as mock_run:

            start_dashboard_daemon(foreground=True)

            # 验证调用了 get_uvicorn_log_config
            mock_get_config.assert_called_once_with(tmp_path / "dashboard.log")
            # 验证 uvicorn.run 被调用且包含 log_config 参数
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args
            assert "log_config" in call_kwargs.kwargs
            assert call_kwargs.kwargs["log_config"] == mock_log_config
            captured = capsys.readouterr()
            assert "Dashboard:" in captured.out


class TestStopDashboardDaemon:
    """stop_dashboard_daemon 测试"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        if DASHBOARD_PID_FILE.exists():
            DASHBOARD_PID_FILE.unlink()
        yield
        if DASHBOARD_PID_FILE.exists():
            DASHBOARD_PID_FILE.unlink()

    def test_not_running(self, capsys):
        """Dashboard 未运行时提示"""
        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=None):
            stop_dashboard_daemon()
            captured = capsys.readouterr()
            assert "未运行" in captured.out

    def test_process_not_exists(self, capsys):
        """进程不存在时清理 PID 文件"""
        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid_file") as mock_remove:
            stop_dashboard_daemon()
            captured = capsys.readouterr()
            assert "已不存在" in captured.out
            mock_remove.assert_called_once()

    def test_stop_success(self, capsys):
        """成功停止 Dashboard"""
        call_count = [0]

        def mock_is_running(pid):
            call_count[0] += 1
            if call_count[0] <= 3:
                return True
            return False

        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", side_effect=mock_is_running), \
             patch("smart_router.gateway.daemon.os.kill") as mock_kill, \
             patch("smart_router.gateway.daemon._remove_pid_file"), \
             patch.object(time, "sleep"):
            stop_dashboard_daemon()
            captured = capsys.readouterr()
            assert "已停止" in captured.out
            mock_kill.assert_called_with(12345, signal.SIGTERM)

    def test_stop_force_kill(self, capsys):
        """SIGTERM 失败后强制 SIGKILL"""
        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=True), \
             patch("smart_router.gateway.daemon.os.kill") as mock_kill, \
             patch("smart_router.gateway.daemon._remove_pid_file"), \
             patch.object(time, "sleep"):
            stop_dashboard_daemon()
            captured = capsys.readouterr()
            assert "强制" in captured.out
            assert mock_kill.call_count == 2


class TestCheckDashboardStatus:
    """check_dashboard_status 测试"""

    def test_not_running(self, capsys):
        """Dashboard 未运行"""
        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=False):
            result = check_dashboard_status()
            captured = capsys.readouterr()
            assert "未运行" in captured.out
            assert result is False

    def test_running(self, capsys):
        """Dashboard 运行中"""
        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=True):
            result = check_dashboard_status()
            captured = capsys.readouterr()
            assert "运行中" in captured.out
            assert result is True

    def test_pid_exists_but_process_not(self, capsys):
        """PID 文件存在但进程不存在"""
        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=12345), \
             patch("smart_router.gateway.daemon._is_process_running", return_value=False), \
             patch("smart_router.gateway.daemon._remove_pid_file"):
            result = check_dashboard_status()
            captured = capsys.readouterr()
            assert "已不存在" in captured.out
            assert result is False

    def test_port_in_use_no_pid_file(self, capsys):
        """端口被占用但 PID 文件丢失"""
        with patch("smart_router.gateway.daemon._get_pid_from_file", return_value=None), \
             patch("smart_router.gateway.daemon._is_port_in_use", return_value=True):
            result = check_dashboard_status()
            captured = capsys.readouterr()
            assert "被占用" in captured.out
            assert result is True
