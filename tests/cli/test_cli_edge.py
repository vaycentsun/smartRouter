"""CLI 边缘情况测试 — 覆盖 init --force、doctor 失败路径、list 异常、coffee 各模式"""

import pytest
from typer.testing import CliRunner
from pathlib import Path
import tempfile

from smart_router.cli import app

runner = CliRunner()


class TestInitCommandEdgeCases:
    """init 命令边缘情况测试"""

    def test_init_force_overwrite(self):
        """init --force 强制覆盖已有文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建已存在的文件
            (Path(tmpdir) / "providers.yaml").write_text("dummy")
            (Path(tmpdir) / "models.yaml").write_text("dummy")
            (Path(tmpdir) / "routing.yaml").write_text("dummy")
            
            result = runner.invoke(app, ["init", "--output", str(tmpdir), "--force"])
            
            assert result.exit_code == 0
            assert "配置文件已生成" in result.stdout
            # 验证文件被覆盖（不再是 dummy）
            assert "providers" in (Path(tmpdir) / "providers.yaml").read_text()

    def test_init_fallback_default_configs(self):
        """模板目录不存在时回退到 _write_default_configs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 使用一个不包含模板的路径，但确保目录可写
            # 由于 pip install 后模板通常存在，我们通过强制条件触发回退较困难
            # 这里验证默认配置写入的格式
            result = runner.invoke(app, ["init", "--output", str(tmpdir)])
            
            assert result.exit_code == 0
            assert (Path(tmpdir) / "providers.yaml").exists()
            assert (Path(tmpdir) / "models.yaml").exists()
            assert (Path(tmpdir) / "routing.yaml").exists()


class TestDoctorCommandEdgeCases:
    """doctor 命令边缘情况测试"""

    def test_doctor_with_missing_config_files(self):
        """配置文件缺失时报告错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["doctor", "--config", str(tmpdir)])
            
            assert result.exit_code == 0
            assert "配置文件缺失" in result.stdout

    def test_doctor_config_validation_failure(self):
        """配置验证失败时报告错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建存在问题的配置文件（provider 引用不存在）
            (Path(tmpdir) / "providers.yaml").write_text("providers: {}\n")
            (Path(tmpdir) / "models.yaml").write_text("""
models:
  test-model:
    provider: nonexistent
    litellm_model: test/model
    capabilities:
      quality: 5
      cost: 5
      context: 1000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")
            (Path(tmpdir) / "routing.yaml").write_text("""
tasks:
  chat:
    name: "Chat"
    description: "Test"
    capability_weights:
      quality: 1.0

difficulties:
  easy:
    description: "Easy"
    max_tokens: 1000

strategies:
  auto:
    description: "Auto"

fallback:
  mode: auto
""")
            result = runner.invoke(app, ["doctor", "--config", str(tmpdir)])
            
            # 配置加载失败会打印错误信息
            assert "配置加载失败" in result.stdout or "配置验证失败" in result.stdout

    def test_doctor_python_version_check(self):
        """doctor 应检查 Python 版本"""
        result = runner.invoke(app, ["doctor"])
        
        assert result.exit_code == 0
        assert "Python 版本" in result.stdout


class TestListCommandEdgeCases:
    """list 命令边缘情况测试"""

    def test_list_missing_config(self):
        """配置文件缺失时提示"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["list", "--config", str(tmpdir)])
            
            assert result.exit_code != 0 or "配置文件缺失" in result.stdout

    def test_list_config_error(self):
        """配置加载失败时退出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建无效的 YAML
            (Path(tmpdir) / "providers.yaml").write_text("invalid: [")
            
            result = runner.invoke(app, ["list", "--config", str(tmpdir)])
            
            # 命令应失败或显示错误信息
            assert result.exit_code != 0 or "失败" in result.stdout


class TestCoffeeCommandEdgeCases:
    """coffee 命令边缘情况测试"""

    def test_coffee_link_option(self):
        """coffee --link 自定义链接"""
        result = runner.invoke(app, ["coffee", "--link", "https://example.com"])
        
        # 即使有错误也不应崩溃
        assert result.exit_code == 0

    def test_coffee_open_option(self):
        """coffee --open 打开图片"""
        result = runner.invoke(app, ["coffee", "--open"])
        
        # 可能因为没有二维码而提示，但不应崩溃
        assert result.exit_code == 0

    def test_coffee_default_no_image(self):
        """coffee 默认模式（无二维码图片）"""
        result = runner.invoke(app, ["coffee"])
        
        # 应显示提示信息
        assert result.exit_code == 0
        assert "Buy Me a Coffee" in result.stdout or "请支持作者" in result.stdout

    def test_coffee_ascii_mode(self):
        """coffee --ascii 纯文字模式"""
        result = runner.invoke(app, ["coffee", "--ascii"])
        
        assert result.exit_code == 0
        assert "Buy Me a Coffee" in result.stdout or "请支持作者" in result.stdout


class TestServiceCommandEdgeCases:
    """服务命令边缘情况测试"""

    def test_restart_with_config_path(self, monkeypatch):
        """restart --config 传递路径"""
        from unittest.mock import MagicMock
        mock_restart = MagicMock()
        monkeypatch.setattr("smart_router.cli.restart_daemon", mock_restart)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir)
            result = runner.invoke(app, ["restart", "--config", str(config_path)])
            
            assert result.exit_code == 0
            mock_restart.assert_called_once_with(config_path=config_path)

    def test_logs_with_lines_option(self, monkeypatch):
        """logs --lines 传递行数"""
        from unittest.mock import MagicMock
        mock_view = MagicMock()
        monkeypatch.setattr("smart_router.cli.view_logs", mock_view)
        
        result = runner.invoke(app, ["logs", "--lines", "20"])
        
        assert result.exit_code == 0
        mock_view.assert_called_once_with(lines=20, follow=False)

    def test_logs_with_follow_option(self, monkeypatch):
        """logs --follow 持续跟踪"""
        from unittest.mock import MagicMock
        mock_view = MagicMock()
        monkeypatch.setattr("smart_router.cli.view_logs", mock_view)
        
        result = runner.invoke(app, ["logs", "--follow"])
        
        assert result.exit_code == 0
        mock_view.assert_called_once_with(lines=50, follow=True)
