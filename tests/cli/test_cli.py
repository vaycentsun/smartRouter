"""CLI 命令测试 - 使用 Typer 的测试工具"""

import pytest
from typer.testing import CliRunner
from pathlib import Path
import tempfile
import yaml

from smart_router.cli import app

runner = CliRunner()


class TestVersionCommand:
    """version 命令测试"""
    
    def test_version_short(self):
        """测试短版本号"""
        result = runner.invoke(app, ["version", "--short"])
        assert result.exit_code == 0
        assert "1.0.2" in result.stdout
    
    def test_version_full(self):
        """测试完整版本信息"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Smart Router" in result.stdout
        assert "1.0.2" in result.stdout


class TestInitCommand:
    """init 命令测试"""
    
    def test_init_creates_config(self):
        """测试 init 生成三文件配置到指定目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", "--output", str(tmpdir)])
            
            assert result.exit_code == 0
            assert (Path(tmpdir) / "providers.yaml").exists()
            assert (Path(tmpdir) / "models.yaml").exists()
            assert (Path(tmpdir) / "routing.yaml").exists()
            assert "配置文件已生成" in result.stdout
    
    def test_init_prompts_on_existing(self):
        """测试已存在文件时提示"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建已存在的文件
            (Path(tmpdir) / "providers.yaml").write_text("dummy")
            
            # 输入 'n' 取消覆盖
            result = runner.invoke(app, ["init", "--output", str(tmpdir)], input="n\n")
            
            assert result.exit_code == 0
            assert "已取消" in result.stdout
    
    def test_init_default_to_home_smart_router(self):
        """测试 init 默认输出目录是 ~/.smart-router/"""
        # 验证帮助信息中显示默认路径
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert ".smart-router" in result.stdout


class TestDoctorCommand:
    """doctor 命令测试"""
    
    def test_doctor_runs(self):
        """测试 doctor 能运行"""
        result = runner.invoke(app, ["doctor"])
        
        assert result.exit_code == 0
        assert "健康检查" in result.stdout
        assert "Python 版本" in result.stdout
    
    def test_doctor_v3_config_check(self):
        """测试 doctor 支持 V3 配置检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 V3 配置文件
            config_dir = Path(tmpdir)
            (config_dir / "providers.yaml").write_text("""
providers:
  test:
    api_base: http://test.com
    api_key: test-key
""")
            (config_dir / "models.yaml").write_text("""
models:
  test-model:
    provider: test
    litellm_model: test/model
    capabilities:
      quality: 5
      speed: 5
      cost: 5
      context: 1000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")
            (config_dir / "routing.yaml").write_text("""
tasks:
  chat:
    name: "Chat"
    description: "Test"
    capability_weights:
      quality: 0.5
      speed: 0.3
      cost: 0.2

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
            
            result = runner.invoke(app, ["doctor", "--config", str(config_dir)])
            
            assert result.exit_code == 0
            assert "V3 配置" in result.stdout or "配置加载成功" in result.stdout


class TestDryRunCommand:
    """dry-run 命令测试"""
    
    @pytest.fixture
    def test_config_dir(self):
        """创建 V3 三文件测试配置目录"""
        config_dir = Path(tempfile.mkdtemp())
        
        # providers.yaml
        (config_dir / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: sk-test
""")
        
        # models.yaml
        (config_dir / "models.yaml").write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [writing, chat]
    difficulty_support: [easy, medium, hard]
  
  qwen3-122b:
    provider: openai
    litellm_model: dashscope/qwen3-122b
    capabilities:
      quality: 8
      cost: 5
      context: 32000
    supported_tasks: [writing, chat]
    difficulty_support: [easy, medium]
""")
        
        # routing.yaml
        (config_dir / "routing.yaml").write_text("""
tasks:
  writing:
    name: "Writing"
    description: "Write articles"
    capability_weights:
      quality: 0.6
      cost: 0.4
    keywords: ["写", "文章"]
    examples: ["帮我写一篇文章"]
  
  chat:
    name: "Chat"
    description: "General chat"
    capability_weights:
      quality: 0.3
      cost: 0.7

difficulties:
  easy:
    description: "Easy"
    max_tokens: 1000
  medium:
    description: "Medium"
    max_tokens: 4000
  hard:
    description: "Hard"
    max_tokens: 8000

strategies:
  auto:
    description: "Auto"
  quality:
    description: "Quality"
  cost:
    description: "Cost"
  balanced:
    description: "Balanced"

fallback:
  mode: auto
  similarity_threshold: 2
""")
        
        yield config_dir
        
        # 清理
        import shutil
        shutil.rmtree(config_dir)
    
    def test_dry_run_basic(self, test_config_dir):
        """测试基本 dry-run"""
        result = runner.invoke(app, ["dry-run", "帮我写篇文章", "--config", str(test_config_dir)])
        
        assert result.exit_code == 0
        assert "路由决策" in result.stdout
        assert "任务分类" in result.stdout
        assert "难度评估" in result.stdout
        assert "模型选择" in result.stdout
    
    def test_dry_run_with_all_flag(self, test_config_dir):
        """测试 --all 参数显示候选模型"""
        result = runner.invoke(app, ["dry-run", "写", "--config", str(test_config_dir), "--all"])
        
        assert result.exit_code == 0
        assert "候选模型" in result.stdout


class TestServiceCommands:
    """服务相关命令测试 - 这些命令需要服务未运行才能测试"""
    
    def test_status(self):
        """测试 status 命令"""
        result = runner.invoke(app, ["status"])
        # 可能服务未运行，但命令应该正常执行
        assert result.exit_code in [0, 1]  # 0=运行中, 1=未运行
    
    def test_logs_help(self):
        """测试 logs 命令帮助"""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "查看服务日志" in result.stdout
    
    def test_start_calls_start_daemon(self, monkeypatch):
        """测试 start 命令调用 start_daemon"""
        from unittest.mock import MagicMock
        mock_start = MagicMock()
        monkeypatch.setattr("smart_router.cli.start_daemon", mock_start)
        
        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0
        mock_start.assert_called_once_with(config_path=None)
    
    def test_start_with_config(self, monkeypatch):
        """测试 start --config 传递正确路径"""
        from unittest.mock import MagicMock
        mock_start = MagicMock()
        monkeypatch.setattr("smart_router.cli.start_daemon", mock_start)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name
        
        result = runner.invoke(app, ["start", "--config", config_path])
        assert result.exit_code == 0
        mock_start.assert_called_once_with(config_path=Path(config_path))
    
    def test_start_foreground(self, monkeypatch):
        """测试 start --foreground 调用 start_server"""
        from unittest.mock import MagicMock
        import smart_router.gateway.server
        mock_server = MagicMock()
        monkeypatch.setattr(smart_router.gateway.server, "start_server", mock_server)
        
        result = runner.invoke(app, ["start", "--foreground"])
        assert result.exit_code == 0
        mock_server.assert_called_once_with(config_path=None)
    
    def test_start_foreground_with_config(self, monkeypatch):
        """测试 start --foreground --config 传递正确路径"""
        from unittest.mock import MagicMock
        import smart_router.gateway.server
        mock_server = MagicMock()
        monkeypatch.setattr(smart_router.gateway.server, "start_server", mock_server)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name
        
        result = runner.invoke(app, ["start", "--foreground", "--config", config_path])
        assert result.exit_code == 0
        mock_server.assert_called_once_with(config_path=Path(config_path))
    
    def test_stop_calls_stop_daemon(self, monkeypatch):
        """测试 stop 命令调用 stop_daemon"""
        from unittest.mock import MagicMock
        mock_stop = MagicMock()
        monkeypatch.setattr("smart_router.cli.stop_daemon", mock_stop)
        
        result = runner.invoke(app, ["stop"])
        assert result.exit_code == 0
        mock_stop.assert_called_once()
    
    def test_restart_calls_restart_daemon(self, monkeypatch):
        """测试 restart 命令调用 restart_daemon"""
        from unittest.mock import MagicMock
        mock_restart = MagicMock()
        monkeypatch.setattr("smart_router.cli.restart_daemon", mock_restart)
        
        result = runner.invoke(app, ["restart"])
        assert result.exit_code == 0
        mock_restart.assert_called_once_with(config_path=None)
    
    def test_restart_with_config(self, monkeypatch):
        """测试 restart --config 传递正确路径"""
        from unittest.mock import MagicMock
        mock_restart = MagicMock()
        monkeypatch.setattr("smart_router.cli.restart_daemon", mock_restart)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name
        
        result = runner.invoke(app, ["restart", "--config", config_path])
        assert result.exit_code == 0
        mock_restart.assert_called_once_with(config_path=Path(config_path))
    
    def test_logs_calls_view_logs(self, monkeypatch):
        """测试 logs 命令调用 view_logs 并传递默认参数"""
        from unittest.mock import MagicMock
        mock_view = MagicMock()
        monkeypatch.setattr("smart_router.cli.view_logs", mock_view)
        
        result = runner.invoke(app, ["logs"])
        assert result.exit_code == 0
        mock_view.assert_called_once_with(lines=50, follow=False)
    
    def test_logs_with_options(self, monkeypatch):
        """测试 logs 命令传递自定义参数"""
        from unittest.mock import MagicMock
        mock_view = MagicMock()
        monkeypatch.setattr("smart_router.cli.view_logs", mock_view)
        
        result = runner.invoke(app, ["logs", "--lines", "100", "--follow"])
        assert result.exit_code == 0
        mock_view.assert_called_once_with(lines=100, follow=True)


class TestCoffeeCommand:
    """coffee 命令测试"""
    
    def test_coffee_ascii(self):
        """测试 coffee --ascii"""
        result = runner.invoke(app, ["coffee", "--ascii"])
        assert result.exit_code == 0
        assert "请支持作者" in result.stdout or "Buy Me a Coffee" in result.stdout
    
    def test_coffee_help(self):
        """测试 coffee 帮助"""
        result = runner.invoke(app, ["coffee", "--help"])
        assert result.exit_code == 0
        assert "请作者喝一杯咖啡" in result.stdout


class TestConfigValidation:
    """配置验证测试"""
    
    def test_invalid_config(self):
        """测试无效配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            
            result = runner.invoke(app, ["doctor", "--config", f.name])
            
            # 应该失败
            assert result.exit_code != 0 or "失败" in result.stdout
