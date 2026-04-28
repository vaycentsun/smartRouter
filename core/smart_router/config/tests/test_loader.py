"""Tests for V3 Configuration Loader"""

import pytest
import tempfile
from pathlib import Path

from unittest.mock import patch
from smart_router.config import ConfigLoader, ConfigError, load_config


class TestConfigLoader:
    """Test V3 Config Loader"""
    
    @pytest.fixture
    def valid_config_dir(self):
        """创建临时有效配置目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # providers.yaml
            (config_dir / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: os.environ/OPENAI_API_KEY
""")
            
            # models.yaml
            (config_dir / "models.yaml").write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      speed: 8
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy, medium, hard]
""")
            
            # routing.yaml
            (config_dir / "routing.yaml").write_text("""
tasks:
  chat:
    name: "Chat"
    description: "General chat"
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
    description: "Auto select"

fallback:
  mode: auto
  similarity_threshold: 2
""")
            
            yield config_dir
    
    def test_load_valid_config(self, valid_config_dir):
        """Test loading valid configuration"""
        loader = ConfigLoader(valid_config_dir)
        config = loader.load()
        
        assert "openai" in config.providers
        assert "gpt-4o" in config.models
        assert "chat" in config.routing.tasks
    
    def test_missing_file(self):
        """Test error on missing config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(Path(tmpdir))
            
            with pytest.raises(ConfigError) as exc_info:
                loader.load()
            
            assert "not found" in str(exc_info.value)
    
    def test_invalid_provider_reference(self):
        """Test error on invalid provider reference"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            (config_dir / "providers.yaml").write_text("providers: {}")
            (config_dir / "models.yaml").write_text("""
models:
  test-model:
    provider: nonexistent
    litellm_model: test
    capabilities: {quality: 5, speed: 5, cost: 5, context: 1000}
    supported_tasks: [chat]
    difficulty_support: [easy]
""")
            (config_dir / "routing.yaml").write_text("""
tasks: {}
difficulties: {}
strategies: {}
fallback: {mode: auto}
""")
            
            loader = ConfigLoader(config_dir)
            
            with pytest.raises(ConfigError) as exc_info:
                loader.load()
            
            assert "unknown provider" in str(exc_info.value).lower()
    
    def test_fallback_derivation(self, valid_config_dir):
        """Test fallback chain derivation"""
        loader = ConfigLoader(valid_config_dir)
        config = loader.load()
        
        # 单模型场景，fallback 应为空
        chain = config.get_fallback_chain("gpt-4o")
        assert isinstance(chain, list)
    
    def test_validate_method(self, valid_config_dir):
        """Test validate method returns empty list for valid config"""
        loader = ConfigLoader(valid_config_dir)
        errors = loader.validate()
        
        assert errors == []
    
    def test_validate_with_missing_files(self):
        """Test validate returns errors for missing files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(Path(tmpdir))
            errors = loader.validate()
            
            assert len(errors) == 3
            assert all("Missing" in e for e in errors)
    
    def test_load_v3_config_convenience_function(self, valid_config_dir, monkeypatch):
        """Test load_v3_config convenience function"""
        monkeypatch.chdir(valid_config_dir)
        
        config = load_config()
        
        assert "openai" in config.providers
        assert "gpt-4o" in config.models

    def test_validate_unexpected_error(self):
        """validate 遇到非 ConfigError 异常时应捕获"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # 创建会导致非 ConfigError 的配置文件
            (config_dir / "providers.yaml").write_text("providers: {}\n")
            (config_dir / "models.yaml").write_text("models: {}\n")
            (config_dir / "routing.yaml").write_text(
                "tasks: {}\ndifficulties: {}\nstrategies: {}\nfallback: {}\n"
            )
            
            loader = ConfigLoader(config_dir)
            
            # 正常情况下不应有意外错误，这里通过 mock 模拟
            with patch.object(loader, 'load', side_effect=RuntimeError("Unexpected error")):
                errors = loader.validate()
                assert len(errors) == 1
                assert "Unexpected error" in errors[0]

    def test_load_with_speed_in_capabilities(self, valid_config_dir):
        """capabilities 中包含 speed 字段时应被忽略（schema 不校验未知字段）"""
        loader = ConfigLoader(valid_config_dir)
        config = loader.load()
        
        # 验证模型能正常加载，speed 字段作为额外字段存在
        assert "gpt-4o" in config.models
        # Pydantic v2 允许额外字段取决于配置，这里主要验证不崩溃
