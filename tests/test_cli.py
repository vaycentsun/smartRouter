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
        assert "0.1.0" in result.stdout
    
    def test_version_full(self):
        """测试完整版本信息"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Smart Router" in result.stdout
        assert "0.1.0" in result.stdout


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
    def test_config_file(self):
        """创建测试配置文件"""
        config = {
            "server": {"port": 4000, "host": "127.0.0.1", "master_key": "sk-test"},
            "model_list": [
                {"model_name": "gpt-4o", "litellm_params": {"model": "openai/gpt-4o", "api_key": "test"}},
                {"model_name": "qwen3-122b", "litellm_params": {"model": "dashscope/qwen3-122b", "api_key": "test"}},
            ],
            "smart_router": {
                "task_types": {
                    "writing": {"keywords": ["写", "文章"]},
                    "chat": {"keywords": []}
                },
                "difficulty_rules": [
                    {"condition": "length < 30", "difficulty": "easy", "priority": 1}
                ],
                "model_pool": {
                    "capabilities": {
                        "gpt-4o": {"difficulties": ["hard"], "task_types": ["writing"], "priority": 1},
                        "qwen3-122b": {"difficulties": ["easy"], "task_types": ["writing"], "priority": 1}
                    },
                    "default_model": "gpt-4o"
                },
                "fallback_chain": {},
                "timeout": {"default": 30, "hard_tasks": 60},
                "max_fallback_retries": 2
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            return f.name
    
    def test_dry_run_basic(self, test_config_file):
        """测试基本 dry-run"""
        result = runner.invoke(app, ["dry-run", "帮我写篇文章", "--config", test_config_file])
        
        assert result.exit_code == 0
        assert "路由决策" in result.stdout
        assert "任务分类" in result.stdout
        assert "难度评估" in result.stdout
        assert "模型选择" in result.stdout
    
    def test_dry_run_with_all_flag(self, test_config_file):
        """测试 --all 参数显示候选模型"""
        result = runner.invoke(app, ["dry-run", "写", "--config", test_config_file, "--all"])
        
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
        import smart_router.server
        mock_server = MagicMock()
        monkeypatch.setattr(smart_router.server, "start_server", mock_server)
        
        result = runner.invoke(app, ["start", "--foreground"])
        assert result.exit_code == 0
        mock_server.assert_called_once_with(config_path=None)
    
    def test_start_foreground_with_config(self, monkeypatch):
        """测试 start --foreground --config 传递正确路径"""
        from unittest.mock import MagicMock
        import smart_router.server
        mock_server = MagicMock()
        monkeypatch.setattr(smart_router.server, "start_server", mock_server)
        
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
