"""server_main 模块测试 — 覆盖后台启动入口"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestServerMain:
    """server_main 入口测试"""

    def test_main_with_config_path(self):
        """测试带 --config 参数启动"""
        config_path = Path("/tmp/test-config")

        with patch("smart_router.gateway.server_main.start_server") as mock_start:
            from smart_router.gateway.server_main import main

            # 模拟命令行参数
            test_args = ["server_main", "--config", str(config_path)]
            with patch.object(sys, "argv", test_args):
                main()

            mock_start.assert_called_once_with(config_path=config_path)

    def test_main_without_config(self):
        """测试不带 --config 参数启动"""
        with patch("smart_router.gateway.server_main.start_server") as mock_start:
            from smart_router.gateway.server_main import main

            test_args = ["server_main"]
            with patch.object(sys, "argv", test_args):
                main()

            mock_start.assert_called_once_with(config_path=None)

    def test_main_keyboard_interrupt(self, capsys):
        """测试 KeyboardInterrupt 捕获"""
        with patch("smart_router.gateway.server_main.start_server", side_effect=KeyboardInterrupt):
            from smart_router.gateway.server_main import main

            test_args = ["server_main"]
            with patch.object(sys, "argv", test_args):
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0

    def test_main_import(self):
        """验证模块可以被正确导入"""
        from smart_router.gateway.server_main import main
        assert callable(main)

    def test_main_with_log_file_argument(self):
        """测试 --log-file 参数被正确解析"""
        log_file = Path("/tmp/test-smart-router.log")

        with patch("smart_router.gateway.server_main.start_server"), \
             patch("smart_router.gateway.server_main.setup_logging") as mock_setup_logging:
            from smart_router.gateway.server_main import main

            test_args = ["server_main", "--log-file", str(log_file)]
            with patch.object(sys, "argv", test_args):
                main()

            # 验证 setup_logging 被调用，且第一个参数是日志文件
            mock_setup_logging.assert_called_once()
            call_args = mock_setup_logging.call_args
            assert call_args[0][0] == log_file

    def test_main_with_log_level_argument(self):
        """测试 --log-level 参数被正确解析"""
        with patch("smart_router.gateway.server_main.start_server"), \
             patch("smart_router.gateway.server_main.setup_logging") as mock_setup_logging:
            from smart_router.gateway.server_main import main

            test_args = ["server_main", "--log-level", "DEBUG"]
            with patch.object(sys, "argv", test_args):
                main()

            # 验证 setup_logging 被调用，且日志级别为 DEBUG
            mock_setup_logging.assert_called_once()
            call_args = mock_setup_logging.call_args
            import logging
            assert call_args[1].get("level") == logging.DEBUG or \
                   (len(call_args[0]) > 1 and call_args[0][1] == logging.DEBUG)

    def test_main_default_log_file_path(self):
        """测试默认日志文件路径（当未指定 --log-file 时）"""
        with patch("smart_router.gateway.server_main.start_server"), \
             patch("smart_router.gateway.server_main.setup_logging") as mock_setup_logging:
            from smart_router.gateway.server_main import main

            test_args = ["server_main"]
            with patch.object(sys, "argv", test_args):
                main()

            # 验证 setup_logging 被调用
            mock_setup_logging.assert_called_once()

    def test_main_with_both_log_arguments(self):
        """测试同时指定 --log-file 和 --log-level 参数"""
        log_file = Path("/var/log/smart-router.log")

        with patch("smart_router.gateway.server_main.start_server"), \
             patch("smart_router.gateway.server_main.setup_logging") as mock_setup_logging:
            from smart_router.gateway.server_main import main

            test_args = ["server_main", "--log-file", str(log_file), "--log-level", "WARNING"]
            with patch.object(sys, "argv", test_args):
                main()

            mock_setup_logging.assert_called_once()
            import logging
            call_args = mock_setup_logging.call_args
            assert call_args[1].get("level") == logging.WARNING or \
                   (len(call_args[0]) > 1 and call_args[0][1] == logging.WARNING)
