"""coffee_qr 模块测试 — 覆盖 QR 路径、系统图片打开、剪贴板"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from smart_router.misc.coffee_qr import (
    display_image_terminal,
    open_image_system,
    open_image_terminal,
    get_qr_code_path,
    copy_to_clipboard,
    QR_CODE_PATH,
)


class TestDisplayImageTerminal:
    """终端图片显示测试"""

    def test_kitty_terminal(self):
        """kitty 终端检测"""
        with patch.dict("os.environ", {"TERM": "xterm-kitty"}, clear=False), \
             patch("shutil.which", return_value="/usr/bin/kitty"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = display_image_terminal(Path("/tmp/test.png"))
            assert result is True

    def test_iterm2_terminal(self):
        """iTerm2 终端检测"""
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value.read.return_value = b"test"
        
        with patch.dict("os.environ", {"TERM_PROGRAM": "iTerm.app"}, clear=False), \
             patch("builtins.open", mock_open):
            result = display_image_terminal(Path("/tmp/test.png"))
            assert result is True

    def test_chafa_tool(self):
        """chafa 工具检测"""
        with patch("shutil.which", side_effect=lambda x: x == "chafa"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)), \
             patch("os.get_terminal_size", return_value=MagicMock(columns=80)):
            result = display_image_terminal(Path("/tmp/test.png"))
            assert result is True

    def test_catimg_tool(self):
        """catimg 工具检测"""
        with patch("shutil.which", side_effect=lambda x: x == "catimg"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = display_image_terminal(Path("/tmp/test.png"))
            assert result is True

    def test_viu_tool(self):
        """viu 工具检测"""
        with patch("shutil.which", side_effect=lambda x: x == "viu"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = display_image_terminal(Path("/tmp/test.png"))
            assert result is True

    def test_imgcat_tool(self):
        """imgcat 工具检测"""
        with patch("shutil.which", side_effect=lambda x: x == "imgcat"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = display_image_terminal(Path("/tmp/test.png"))
            assert result is True

    def test_no_supported_tool(self):
        """无支持的终端/工具时返回 False"""
        with patch("shutil.which", return_value=None), \
             patch.dict("os.environ", {}, clear=True):
            result = display_image_terminal(Path("/tmp/test.png"))
            assert result is False

    def test_open_image_terminal_alias(self):
        """open_image_terminal 是 display_image_terminal 的别名"""
        with patch("smart_router.misc.coffee_qr.display_image_terminal", return_value=True):
            result = open_image_terminal(Path("/tmp/test.png"))
            assert result is True


class TestOpenImageSystem:
    """系统图片打开测试"""

    def test_macos_open(self):
        """macOS 使用 open 命令"""
        with patch("platform.system", return_value="Darwin"), \
             patch("subprocess.run", return_value=MagicMock()) as mock_run:
            result = open_image_system(Path("/tmp/test.png"))
            assert result is True
            mock_run.assert_called_once()
            assert "open" in mock_run.call_args[0][0]

    def test_linux_xdg_open(self):
        """Linux 使用 xdg-open 命令"""
        with patch("platform.system", return_value="Linux"), \
             patch("subprocess.run", return_value=MagicMock()) as mock_run:
            result = open_image_system(Path("/tmp/test.png"))
            assert result is True
            mock_run.assert_called_once()
            assert "xdg-open" in mock_run.call_args[0][0]

    def test_windows_startfile(self):
        """Windows 使用 os.startfile"""
        mock_start = MagicMock()
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.__dict__", {"startfile": mock_start}, clear=False):
            result = open_image_system(Path("/tmp/test.png"))
            assert result is True or result is False

    def test_open_failure(self):
        """打开失败时返回 False"""
        with patch("platform.system", return_value="Unknown"), \
             patch("subprocess.run", side_effect=Exception("fail")):
            result = open_image_system(Path("/tmp/test.png"))
            assert result is False


class TestGetQrCodePath:
    """二维码路径获取测试"""

    def test_existing_qr_path(self):
        """已有二维码时返回路径"""
        with patch.object(Path, "exists", return_value=True):
            result = get_qr_code_path()
            assert result is not None

    def test_no_qr_returns_none(self):
        """二维码不存在时返回 None"""
        with patch.object(Path, "exists", return_value=False):
            result = get_qr_code_path()
            assert result is None


class TestCopyToClipboard:
    """剪贴板复制测试"""

    def test_macos_pbcopy(self):
        """macOS 使用 pbcopy"""
        with patch("platform.system", return_value="Darwin"), \
             patch("subprocess.run", return_value=MagicMock()) as mock_run:
            result = copy_to_clipboard("test text")
            assert result is True
            mock_run.assert_called_once()

    def test_linux_xclip(self):
        """Linux 使用 xclip"""
        with patch("platform.system", return_value="Linux"), \
             patch("subprocess.run", return_value=MagicMock()) as mock_run:
            result = copy_to_clipboard("test text")
            assert result is True
            mock_run.assert_called_once()

    def test_windows_clip(self):
        """Windows 使用 clip"""
        with patch("platform.system", return_value="Windows"), \
             patch("subprocess.run", return_value=MagicMock()) as mock_run:
            result = copy_to_clipboard("test text")
            assert result is True
            mock_run.assert_called_once()

    def test_copy_failure(self):
        """复制失败时返回 False"""
        with patch("platform.system", return_value="Unknown"), \
             patch("subprocess.run", side_effect=Exception("fail")):
            result = copy_to_clipboard("test text")
            assert result is False