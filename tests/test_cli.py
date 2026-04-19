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
        """测试 init 生成配置文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test-config.yaml"
            
            result = runner.invoke(app, ["init", "--output", str(config_path)])
            
            assert result.exit_code == 0
            assert config_path.exists()
            assert "配置文件已生成" in result.stdout
    
    def test_init_prompts_on_existing(self):
        """测试已存在文件时提示"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test-config.yaml"
            config_path.write_text("dummy")
            
            # 输入 'n' 取消覆盖
            result = runner.invoke(app, ["init", "--output", str(config_path)], input="n\n")
            
            assert result.exit_code == 0
            assert "已取消" in result.stdout


class TestDoctorCommand:
    """doctor 命令测试"""
    
    def test_doctor_runs(self):
        """测试 doctor 能运行"""
        result = runner.invoke(app, ["doctor"])
        
        assert result.exit_code == 0
        assert "健康检查" in result.stdout
        assert "Python 版本" in result.stdout


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
