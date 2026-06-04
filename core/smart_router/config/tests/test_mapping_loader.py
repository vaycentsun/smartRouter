"""ModelMappingLoader 测试"""

import os
import pytest
from pathlib import Path

from smart_router.config.mapping_loader import ModelMappingLoader, ConfigError
from smart_router.config.mapping_schema import ModelMappingConfig, ModelMappingRule


class TestModelMappingLoaderLoad:
    """测试 load() 方法"""

    def test_load_existing_yaml(self, tmp_path):
        """场景 1: 加载存在的 YAML 文件"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        yaml_path = config_dir / "model_mappings.yaml"
        yaml_path.write_text("""
enabled: true
mappings:
  - id: "map-gpt4-to-qwen"
    enabled: true
    from_model: "gpt-4"
    to_provider: "aliyun"
    to_model: "qwen-max"
    to_litellm_provider: "openai"
    to_base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    to_api_key: "os.environ/DASHSCOPE_API_KEY"
""")

        loader = ModelMappingLoader(config_dir)
        config = loader.load()

        assert config.enabled is True
        assert len(config.mappings) == 1
        rule = config.mappings[0]
        assert rule.id == "map-gpt4-to-qwen"
        assert rule.from_model == "gpt-4"
        assert rule.to_provider == "aliyun"
        assert rule.to_model == "qwen-max"
        assert rule.to_base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert rule.to_api_key == "os.environ/DASHSCOPE_API_KEY"

    def test_load_file_not_found_returns_default(self, tmp_path):
        """场景 2: 文件不存在时返回默认空配置"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        loader = ModelMappingLoader(config_dir)
        config = loader.load()

        assert config.enabled is False
        assert config.mappings == []


class TestModelMappingLoaderSave:
    """测试 save() 方法"""

    def test_save_config_content_matches(self, tmp_path):
        """场景 3: 保存配置后文件内容与预期一致"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config = ModelMappingConfig(
            enabled=True,
            mappings=[
                ModelMappingRule(
                    id="map-test",
                    enabled=True,
                    from_model="gpt-4",
                    to_provider="test-provider",
                    to_model="test-model",
                    to_base_url="https://api.test.com/v1",
                    to_api_key="sk-test123",
                )
            ],
        )

        loader = ModelMappingLoader(config_dir)
        loader.save(config)

        yaml_path = config_dir / "model_mappings.yaml"
        assert yaml_path.exists()
        content = yaml_path.read_text()
        assert "enabled: true" in content
        assert "id: map-test" in content
        assert "from_model: gpt-4" in content
        assert "to_provider: test-provider" in content
        assert "to_model: test-model" in content
        assert "to_base_url: https://api.test.com/v1" in content
        assert "to_api_key: sk-test123" in content

    def test_save_file_permissions(self, tmp_path):
        """场景 8: save() 后文件权限为 0o600"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config = ModelMappingConfig(enabled=False, mappings=[])
        loader = ModelMappingLoader(config_dir)
        loader.save(config)

        yaml_path = config_dir / "model_mappings.yaml"
        stat = yaml_path.stat()
        # 检查权限位（只检查 owner read/write，忽略 group/other 和 sticky位等）
        assert oct(stat.st_mode)[-3:] == "600"


class TestModelMappingLoaderSaveRaw:
    """测试 save_raw() 方法"""

    def test_save_raw_valid_yaml(self, tmp_path):
        """场景 4: 保存有效 YAML 后配置正确"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        raw_yaml = """
enabled: true
mappings:
  - id: "raw-test"
    enabled: true
    from_model: "claude-3"
    to_provider: "anthropic"
    to_model: "claude-3-opus"
    to_base_url: "https://api.anthropic.com/v1"
    to_api_key: "sk-anthropic"
"""

        loader = ModelMappingLoader(config_dir)
        loader.save_raw(raw_yaml)

        config = loader.load()
        assert config.enabled is True
        assert len(config.mappings) == 1
        assert config.mappings[0].id == "raw-test"
        assert config.mappings[0].from_model == "claude-3"

    def test_save_raw_invalid_yaml_raises_and_preserves_file(self, tmp_path):
        """场景 5: 保存无效 YAML 时抛出 ConfigError 且原文件不被破坏"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # 先创建一个有效文件
        original_content = """
enabled: true
mappings:
  - id: "existing"
    enabled: true
    from_model: "gpt-4"
    to_provider: "openai"
    to_model: "gpt-4o"
    to_base_url: "https://api.openai.com/v1"
    to_api_key: "sk-original"
"""
        yaml_path = config_dir / "model_mappings.yaml"
        yaml_path.write_text(original_content)

        loader = ModelMappingLoader(config_dir)

        # 尝试保存无效 YAML（语法错误）
        with pytest.raises(ConfigError, match="Invalid YAML"):
            loader.save_raw("enabled: true\nmappings: [invalid: yaml: {{bad")

        # 验证原文件未被破坏
        assert yaml_path.read_text() == original_content

        # 尝试保存验证失败的 YAML（缺少必填字段）
        with pytest.raises(ConfigError, match="Config validation failed"):
            loader.save_raw("enabled: true\nmappings:\n  - id: bad\n    from_model: x\n    to_provider: y")

        # 验证原文件仍未被破坏
        assert yaml_path.read_text() == original_content


class TestModelMappingLoaderResolveApiKey:
    """测试 resolve_api_key() 静态方法"""

    def test_resolve_api_key_from_env(self, monkeypatch):
        """场景 6: 解析 os.environ/KEY_NAME"""
        monkeypatch.setenv("TEST_API_KEY", "secret-key-123")
        result = ModelMappingLoader.resolve_api_key("os.environ/TEST_API_KEY")
        assert result == "secret-key-123"

    def test_resolve_api_key_missing_env_returns_empty(self, monkeypatch):
        """环境变量不存在时返回空字符串"""
        monkeypatch.delenv("NONEXISTENT_KEY", raising=False)
        result = ModelMappingLoader.resolve_api_key("os.environ/NONEXISTENT_KEY")
        assert result == ""

    def test_resolve_api_key_plain_string(self):
        """场景 7: 返回普通字符串原值"""
        result = ModelMappingLoader.resolve_api_key("sk-plain-api-key")
        assert result == "sk-plain-api-key"

    def test_resolve_api_key_empty_string(self):
        """空字符串原样返回"""
        result = ModelMappingLoader.resolve_api_key("")
        assert result == ""

    def test_resolve_api_key_not_os_environ_prefix(self):
        """以 os.environ 开头但缺少斜杠时原样返回"""
        result = ModelMappingLoader.resolve_api_key("os.environXKEY")
        assert result == "os.environXKEY"
