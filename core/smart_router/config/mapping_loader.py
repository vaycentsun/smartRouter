import os
from pathlib import Path

import yaml

from .loader import ConfigError
from .mapping_schema import ModelMappingConfig


class ModelMappingLoader:
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.filepath = self.config_dir / "model_mappings.yaml"

    def load(self) -> ModelMappingConfig:
        """加载 model_mappings.yaml，返回 ModelMappingConfig"""
        if not self.filepath.exists():
            return ModelMappingConfig(enabled=False, mappings=[])
        with open(self.filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return ModelMappingConfig(**data)

    def save(self, config: ModelMappingConfig) -> None:
        """保存配置到 YAML，带备份和回滚机制"""
        backup_path = self.filepath.with_suffix(".yaml.bak")
        if self.filepath.exists():
            try:
                backup_path.write_text(self.filepath.read_text(encoding="utf-8"), encoding="utf-8")
            except OSError:
                pass
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    config.model_dump(),
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
        except Exception as e:
            if backup_path.exists():
                try:
                    self.filepath.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
                except OSError:
                    pass
            raise ConfigError(f"Failed to write model_mappings.yaml: {e}") from e
        try:
            self.filepath.chmod(0o600)
        except OSError:
            pass

    def save_raw(self, raw_yaml_text: str) -> None:
        """保存原始 YAML 文本，先解析验证，失败则回滚"""
        try:
            data = yaml.safe_load(raw_yaml_text)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML: {e}") from e
        try:
            config = ModelMappingConfig(**data)
        except Exception as e:
            raise ConfigError(f"Config validation failed: {e}") from e
        self.save(config)

    @staticmethod
    def resolve_api_key(api_key: str) -> str:
        """解析 os.environ/KEY_NAME 格式为实际值"""
        if api_key.startswith("os.environ/"):
            env_var = api_key.replace("os.environ/", "")
            return os.environ.get(env_var, "")
        return api_key
