"""server_main 模块测试 — 覆盖后台启动入口"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock


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
