"""Tests for CLI list command"""

import pytest
from typer.testing import CliRunner
from pathlib import Path
import tempfile
import yaml

from smart_router.cli import app

runner = CliRunner()


@pytest.fixture
def mock_config_dir():
    """Create a temporary config directory with test configurations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        
        # Create providers.yaml
        providers = {
            "providers": {
                "openai": {
                    "api_base": "https://api.openai.com/v1",
                    "api_key": "os.environ/OPENAI_API_KEY",
                    "timeout": 30
                },
                "anthropic": {
                    "api_base": "https://api.anthropic.com",
                    "api_key": "sk-ant-xxxxx",
                    "timeout": 30
                },
                "moonshot": {
                    "api_base": "https://api.moonshot.cn/v1",
                    "api_key": "sk-msk-xxxxx",
                    "timeout": 30
                }
            }
        }
        
        # Create models.yaml
        models = {
            "models": {
                "gpt-4o": {
                    "provider": "openai",
                    "litellm_model": "openai/gpt-4o",
                    "capabilities": {
                        "quality": 9,
                        "speed": 8,
                        "cost": 3,
                        "context": 128000
                    },
                    "supported_tasks": ["coding", "writing", "chat"],
                    "difficulty_support": ["easy", "medium", "hard"]
                },
                "claude-sonnet": {
                    "provider": "anthropic",
                    "litellm_model": "anthropic/claude-3-5-sonnet-20241022",
                    "capabilities": {
                        "quality": 9,
                        "speed": 7,
                        "cost": 4,
                        "context": 200000
                    },
                    "supported_tasks": ["coding", "writing", "chat"],
                    "difficulty_support": ["easy", "medium", "hard"]
                },
                "kimi-k2": {
                    "provider": "moonshot",
                    "litellm_model": "openai/moonshot-v1-8k",
                    "capabilities": {
                        "quality": 7,
                        "speed": 8,
                        "cost": 7,
                        "context": 8000
                    },
                    "supported_tasks": ["writing", "chat"],
                    "difficulty_support": ["easy", "medium"]
                }
            }
        }
        
        # Create routing.yaml
        routing = {
            "tasks": {
                "coding": {
                    "name": "代码生成",
                    "description": "编写代码",
                    "capability_weights": {"quality": 0.6, "speed": 0.3, "cost": 0.1}
                }
            },
            "difficulties": {
                "easy": {"description": "简单任务", "max_tokens": 2000}
            },
            "strategies": {
                "auto": {"description": "自动选择"}
            },
            "fallback": {"mode": "auto", "similarity_threshold": 2}
        }
        
        (config_dir / "providers.yaml").write_text(yaml.dump(providers))
        (config_dir / "models.yaml").write_text(yaml.dump(models))
        (config_dir / "routing.yaml").write_text(yaml.dump(routing))
        
        yield config_dir


def test_list_command_exists():
    """Test that list command exists"""
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
    assert "列出" in result.output or "list" in result.output.lower()


def test_list_command_shows_providers(mock_config_dir, monkeypatch):
    """Test that list command displays configured providers"""
    # Use --config option instead of mocking Path.home()
    result = runner.invoke(app, ["list", "--config", str(mock_config_dir)])
    
    assert result.exit_code == 0
    # Check providers are shown
    assert "openai" in result.output.lower() or "OpenAI" in result.output
    assert "anthropic" in result.output.lower() or "Anthropic" in result.output
    assert "moonshot" in result.output.lower() or "Moonshot" in result.output


def test_list_command_shows_models(mock_config_dir, monkeypatch):
    """Test that list command displays available models"""
    # Use --config option instead of mocking Path.home()
    result = runner.invoke(app, ["list", "--config", str(mock_config_dir)])
    
    assert result.exit_code == 0
    # Check models are shown
    assert "gpt-4o" in result.output
    assert "claude" in result.output.lower() or "Claude" in result.output
    assert "kimi" in result.output.lower() or "Kimi" in result.output


def test_list_command_with_config_option(mock_config_dir):
    """Test list command with --config option"""
    result = runner.invoke(app, ["list", "--config", str(mock_config_dir)])
    
    assert result.exit_code == 0
    assert "provider" in result.output.lower() or "提供商" in result.output or "服务商" in result.output


def test_list_command_handles_missing_config():
    """Test list command handles missing configuration gracefully"""
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_dir = Path(tmpdir)
        result = runner.invoke(app, ["list", "--config", str(empty_dir)])
        
        assert result.exit_code != 0 or "错误" in result.output or "error" in result.output.lower() or "未找到" in result.output or "not found" in result.output.lower()
