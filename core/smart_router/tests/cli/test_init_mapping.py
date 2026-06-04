"""init 命令生成 model_mappings.yaml 的测试"""

import pytest
from typer.testing import CliRunner
from pathlib import Path
import tempfile
import yaml
from smart_router.cli import app
from smart_router.config.mapping_loader import ModelMappingLoader
from smart_router.config.mapping_schema import ModelMappingConfig

runner = CliRunner()


class TestInitModelMapping:
    """init 命令生成 model_mappings.yaml 的测试"""

    def test_init_generates_model_mappings_yaml(self):
        """场景 1: init 生成 model_mappings.yaml，验证文件存在、可加载、默认 enabled=false"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", "--output", str(tmpdir), "--force"])

            assert result.exit_code == 0
            mapping_file = Path(tmpdir) / "model_mappings.yaml"
            assert mapping_file.exists(), "model_mappings.yaml 应该被生成"

            loader = ModelMappingLoader(Path(tmpdir))
            config = loader.load()
            assert isinstance(config, ModelMappingConfig)
            assert config.enabled is False, "默认 enabled 应为 false"
            assert config.mappings == [], "默认 mappings 应为空列表"

    def test_init_safe_does_not_overwrite_existing(self):
        """场景 2: init --safe 不覆盖已有 model_mappings.yaml"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_content = """enabled: true
mappings:
  - id: custom-rule
    enabled: true
    from_model: gpt-4
    to_provider: aliyun
    to_model: qwen-max
    to_base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    to_api_key: os.environ/DASHSCOPE_API_KEY
"""
            mapping_file = Path(tmpdir) / "model_mappings.yaml"
            mapping_file.write_text(custom_content, encoding="utf-8")

            result = runner.invoke(app, ["init", "--output", str(tmpdir), "--safe"])

            # safe 模式下，由于 model_mappings.yaml 已存在，不应被覆盖
            # 但其他文件（如 providers.yaml、routing.yaml、models/）可能缺失，
            # 所以命令可能成功生成缺失项，model_mappings.yaml 应保持原样
            assert result.exit_code == 0
            assert mapping_file.read_text(encoding="utf-8") == custom_content

    def test_init_generated_file_loads_correctly(self):
        """场景 3: 生成的文件内容可通过 ModelMappingLoader.load() 正确加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", "--output", str(tmpdir), "--force"])
            assert result.exit_code == 0

            loader = ModelMappingLoader(Path(tmpdir))
            config = loader.load()

            assert isinstance(config, ModelMappingConfig)
            assert hasattr(config, "enabled")
            assert hasattr(config, "mappings")
            assert isinstance(config.mappings, list)
            assert config.enabled is False
