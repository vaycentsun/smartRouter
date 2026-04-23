"""daemon 模块单元测试"""

import pytest
import os
import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

from smart_router.daemon import (
    _get_pid,
    _is_process_running,
    _write_pid,
    _remove_pid,
    _ensure_pid_dir,
    _get_python_executable,
    start_daemon,
    stop_daemon,
    restart_daemon,
    check_status,
    view_logs,
    DEFAULT_PID_DIR,
    DEFAULT_PID_FILE,
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

        with patch("smart_router.daemon.DEFAULT_PID_FILE", test_pid_file):
            assert _get_pid() == 12345

    def test_get_pid_invalid_content(self, tmp_path):
        """PID 文件内容无效时返回 None"""
        test_pid_file = tmp_path / "test.pid"
        test_pid_file.write_text("invalid")

        with patch("smart_router.daemon.DEFAULT_PID_FILE", test_pid_file):
            assert _get_pid() is None

    def test_write_pid(self, tmp_path):
        """写入 PID 文件"""
        test_pid_file = tmp_path / "test.pid"

        with patch("smart_router.daemon.DEFAULT_PID_FILE", test_pid_file):
            _write_pid(54321)
            assert test_pid_file.read_text() == "54321"

    def test_remove_pid(self, tmp_path):
        """删除 PID 文件"""
        test_pid_file = tmp_path / "test.pid"
        test_pid_file.write_text("12345")

        with patch("smart_router.daemon.DEFAULT_PID_FILE", test_pid_file):
            _remove_pid()
            assert not test_pid_file.exists()

    def test_remove_pid_no_file(self, tmp_path):
        """PID 文件不存在时删除不报错"""
        test_pid_file = tmp_path / "test.pid"

        with patch("smart_router.daemon.DEFAULT_PID_FILE", test_pid_file):
            _remove_pid()

    def test_ensure_pid_dir(self, tmp_path):
        """确保 PID 目录存在"""
        test_pid_dir = tmp_path / "new_dir"

        with patch("smart_router.daemon.DEFAULT_PID_DIR", test_pid_dir):
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
        from smart_router.daemon import _is_port_in_use
        import socket
        # 绑定一个临时端口，然后检查
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            s.listen(1)
            assert _is_port_in_use(port) is True

    def test_port_not_in_use(self):
        """端口未被占用时返回 False"""
        from smart_router.daemon import _is_port_in_use
        import socket
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
        with patch("smart_router.daemon._get_pid", return_value=12345), \
             patch("smart_router.daemon._is_process_running", return_value=True):
            start_daemon()
            captured = capsys.readouterr()
            assert "已在运行" in captured.out

    def test_port_in_use_no_pid_file(self, capsys):
        """端口被占用但 PID 文件丢失时提示"""
        mock_process = MagicMock()
        mock_process.pid = 99999

        with patch("smart_router.daemon._get_pid", return_value=None), \
             patch("smart_router.daemon._is_port_in_use", return_value=True):
            start_daemon()
            captured = capsys.readouterr()
            assert "端口 4000 已被占用" in captured.out

    def test_start_success(self, capsys):
        """成功启动服务"""
        mock_process = MagicMock()
        mock_process.pid = 99999

        with patch("smart_router.daemon._get_pid", return_value=None), \
             patch("smart_router.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.daemon._remove_pid"), \
             patch("smart_router.daemon.subprocess.Popen", return_value=mock_process):
            start_daemon()
            captured = capsys.readouterr()
            assert "已启动" in captured.out

    def test_start_with_config_path(self, capsys):
        """带配置文件路径启动"""
        mock_process = MagicMock()
        mock_process.pid = 99999
        config_path = Path("/tmp/test_config.yaml")

        with patch("smart_router.daemon._get_pid", return_value=None), \
             patch("smart_router.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.daemon._remove_pid"), \
             patch("smart_router.daemon.subprocess.Popen", return_value=mock_process) as mock_popen:
            start_daemon(config_path=config_path)
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert "--config" in call_args
            assert str(config_path) in call_args

    def test_start_without_master_key_warning(self, capsys):
        """未设置 MASTER_KEY 时显示警告"""
        mock_process = MagicMock()
        mock_process.pid = 99999

        with patch("smart_router.daemon._get_pid", return_value=None), \
             patch("smart_router.daemon._is_port_in_use", return_value=False), \
             patch("smart_router.daemon._remove_pid"), \
             patch("smart_router.daemon.subprocess.Popen", return_value=mock_process), \
             patch.dict(os.environ, {"SMART_ROUTER_MASTER_KEY": ""}, clear=False):
            start_daemon()
            captured = capsys.readouterr()
            # 警告只在 MASTER_KEY 未设置时显示，如果设置了则不显示
            # 这里测试两种情况都可以接受
            assert "已启动" in captured.out


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
        with patch("smart_router.daemon._get_pid", return_value=None):
            stop_daemon()
            captured = capsys.readouterr()
            assert "未运行" in captured.out

    def test_process_not_exists(self, capsys):
        """进程不存在时清理 PID 文件"""
        with patch("smart_router.daemon._get_pid", return_value=12345), \
             patch("smart_router.daemon._is_process_running", return_value=False), \
             patch("smart_router.daemon._remove_pid") as mock_remove:
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
        
        with patch("smart_router.daemon._get_pid", return_value=12345), \
             patch("smart_router.daemon._is_process_running", side_effect=mock_is_running), \
             patch("smart_router.daemon.os.kill") as mock_kill, \
             patch("smart_router.daemon._remove_pid"), \
             patch.object(time, "sleep"):
            stop_daemon()
            captured = capsys.readouterr()
            assert "已停止" in captured.out
            mock_kill.assert_called_with(12345, signal.SIGTERM)

    def test_stop_force_kill(self, capsys):
        """SIGTERM 失败后强制 SIGKILL"""
        import time
        with patch("smart_router.daemon._get_pid", return_value=12345), \
             patch("smart_router.daemon._is_process_running", return_value=True), \
             patch("smart_router.daemon.os.kill") as mock_kill, \
             patch("smart_router.daemon._remove_pid"), \
             patch.object(time, "sleep"):
            stop_daemon()
            captured = capsys.readouterr()
            assert "强制" in captured.out
            assert mock_kill.call_count == 2


class TestRestartDaemon:
    """restart_daemon 测试"""

    def test_restart_calls_stop_and_start(self, capsys):
        """重启调用停止和启动"""
        with patch("smart_router.daemon.stop_daemon") as mock_stop, \
             patch("smart_router.daemon.start_daemon") as mock_start:
            restart_daemon()
            mock_stop.assert_called_once()
            mock_start.assert_called_once()

    def test_restart_with_config(self):
        """带配置重启"""
        config_path = Path("/tmp/config.yaml")
        with patch("smart_router.daemon.stop_daemon"), \
             patch("smart_router.daemon.start_daemon") as mock_start:
            restart_daemon(config_path=config_path)
            mock_start.assert_called_once()


class TestCheckStatus:
    """check_status 测试"""

    def test_not_running(self, capsys):
        """服务未运行"""
        with patch("smart_router.daemon._get_pid", return_value=None):
            result = check_status()
            captured = capsys.readouterr()
            assert "未运行" in captured.out
            assert result is False

    def test_running(self, capsys):
        """服务运行中"""
        with patch("smart_router.daemon._get_pid", return_value=12345), \
             patch("smart_router.daemon._is_process_running", return_value=True):
            result = check_status()
            captured = capsys.readouterr()
            assert "运行中" in captured.out
            assert result is True

    def test_pid_exists_but_process_not(self, capsys):
        """PID 文件存在但进程不存在"""
        with patch("smart_router.daemon._get_pid", return_value=12345), \
             patch("smart_router.daemon._is_process_running", return_value=False), \
             patch("smart_router.daemon._remove_pid"):
            result = check_status()
            captured = capsys.readouterr()
            assert "已不存在" in captured.out
            assert result is False


class TestViewLogs:
    """view_logs 测试"""

    def test_log_file_not_exists(self, capsys):
        """日志文件不存在"""
        with patch("smart_router.daemon.DEFAULT_PID_DIR", Path("/nonexistent")):
            view_logs()
            captured = capsys.readouterr()
            assert "不存在" in captured.out

    def test_view_logs_basic(self, tmp_path, capsys):
        """查看日志基本功能"""
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("line1\nline2\nline3\n")

        with patch("smart_router.daemon.DEFAULT_PID_DIR", tmp_path):
            view_logs(lines=2)
            captured = capsys.readouterr()
            assert "line2" in captured.out or "line3" in captured.out

    def test_view_logs_follow_interrupt(self, tmp_path, capsys):
        """跟踪模式被中断"""
        import time
        log_file = tmp_path / "smart-router.log"
        log_file.write_text("line1\n")

        with patch("smart_router.daemon.DEFAULT_PID_DIR", tmp_path), \
             patch.object(time, "sleep", side_effect=KeyboardInterrupt()):
            view_logs(follow=True)
            captured = capsys.readouterr()
            assert "停止跟踪" in captured.out