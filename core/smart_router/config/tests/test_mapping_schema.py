"""ModelMappingRule 和 ModelMappingConfig 的 Pydantic 模型测试"""

import pytest
from pydantic import ValidationError

# 先导入，运行测试时预期失败（因为文件尚未创建）
from smart_router.config.mapping_schema import ModelMappingConfig, ModelMappingRule


class TestModelMappingRule:
    """ModelMappingRule 单个规则的验证测试"""

    def test_valid_rule(self):
        """场景1: 正常配置加载和验证通过"""
        rule = ModelMappingRule(
            id="rule-001",
            from_model="gpt-4o",
            to_provider="openai",
            to_model="gpt-4o-mini",
            to_base_url="https://api.openai.com/v1",
            to_api_key="sk-test123",
        )
        assert rule.id == "rule-001"
        assert rule.enabled is True
        assert rule.to_litellm_provider == "openai"

    def test_env_format_api_key(self):
        """场景6: 环境变量格式的 to_api_key 通过验证（不做解析）"""
        rule = ModelMappingRule(
            id="rule_env",
            from_model="gpt-4",
            to_provider="azure",
            to_model="gpt-4",
            to_base_url="https://api.azure.com",
            to_api_key="os.environ/OPENAI_API_KEY",
        )
        assert rule.to_api_key == "os.environ/OPENAI_API_KEY"

    def test_invalid_id_chars(self):
        """场景4: id 包含非法字符时抛出 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ModelMappingRule(
                id="rule@001",
                from_model="gpt-4o",
                to_provider="openai",
                to_model="gpt-4o-mini",
                to_base_url="https://api.openai.com/v1",
                to_api_key="sk-test",
            )
        assert "Invalid id" in str(exc_info.value)

    def test_invalid_base_url(self):
        """场景3: to_base_url 不以 http/https 开头时抛出 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ModelMappingRule(
                id="rule-002",
                from_model="gpt-4o",
                to_provider="openai",
                to_model="gpt-4o-mini",
                to_base_url="ftp://api.openai.com/v1",
                to_api_key="sk-test",
            )
        assert "to_base_url must start with http:// or https://" in str(exc_info.value)


class TestModelMappingConfig:
    """ModelMappingConfig 全局配置的验证测试"""

    def test_valid_config(self):
        """场景1: 正常配置加载和验证通过"""
        config = ModelMappingConfig(
            enabled=True,
            mappings=[
                ModelMappingRule(
                    id="rule-001",
                    from_model="gpt-4o",
                    to_provider="openai",
                    to_model="gpt-4o-mini",
                    to_base_url="https://api.openai.com/v1",
                    to_api_key="sk-test",
                ),
            ],
        )
        assert config.enabled is True
        assert len(config.mappings) == 1

    def test_duplicate_ids(self):
        """场景2: 重复 id 时抛出 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ModelMappingConfig(
                enabled=True,
                mappings=[
                    ModelMappingRule(
                        id="same-id",
                        from_model="gpt-4o",
                        to_provider="openai",
                        to_model="gpt-4o-mini",
                        to_base_url="https://api.openai.com/v1",
                        to_api_key="sk-test",
                    ),
                    ModelMappingRule(
                        id="same-id",
                        from_model="gpt-4",
                        to_provider="openai",
                        to_model="gpt-4-turbo",
                        to_base_url="https://api.openai.com/v1",
                        to_api_key="sk-test2",
                    ),
                ],
            )
        assert "Duplicate mapping rule ids found" in str(exc_info.value)

    def test_empty_mappings(self):
        """场景5: 空规则列表通过验证"""
        config = ModelMappingConfig()
        assert config.enabled is False
        assert config.mappings == []

    def test_empty_mappings_explicit(self):
        """场景5: 显式传入空规则列表通过验证"""
        config = ModelMappingConfig(enabled=True, mappings=[])
        assert config.enabled is True
        assert config.mappings == []
