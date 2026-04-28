"""V3 Configuration Loader"""

from pathlib import Path
from typing import Optional
import yaml
from pydantic import ValidationError

from .schema import Config


class ConfigLoader:
    """Smart Router 配置加载器"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
    
    def load(self) -> Config:
        """从三文件加载配置"""
        providers = self._load_yaml("providers.yaml")
        models = self._load_yaml("models.yaml")
        routing = self._load_yaml("routing.yaml")
        
        try:
            config = Config(
                providers=providers.get("providers", {}),
                models=models.get("models", {}),
                routing=routing
            )
            return config
        except ValidationError as e:
            raise ConfigError(f"Configuration validation failed: {e}") from e
    
    def _load_yaml(self, filename: str) -> dict:
        """加载单个 YAML 文件"""
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise ConfigError(f"Configuration file not found: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    def validate(self) -> list[str]:
        """验证配置，返回错误列表（空表示通过）"""
        errors = []

        # 检查文件存在
        for filename in ["providers.yaml", "models.yaml", "routing.yaml"]:
            if not (self.config_dir / filename).exists():
                errors.append(f"Missing configuration file: {filename}")

        if errors:
            return errors

        # 尝试加载并验证
        try:
            self.load()
        except ConfigError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Unexpected error: {e}")

        return errors

    def save_providers(self, providers_raw: dict) -> None:
        """保存 providers 配置到 YAML 文件

        Args:
            providers_raw: 原始 provider 字典，直接序列化写入

        Raises:
            ConfigError: 写入或验证失败时抛出
        """
        filepath = self.config_dir / "providers.yaml"

        # 写入前备份原文件（简单备份）
        if filepath.exists():
            backup_path = filepath.with_suffix(".yaml.bak")
            try:
                backup_path.write_text(filepath.read_text(), encoding="utf-8")
            except IOError:
                pass  # 备份失败不影响主流程

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    {"providers": providers_raw},
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
        except Exception as e:
            raise ConfigError(f"Failed to write providers.yaml: {e}") from e

        # 写入后验证整体配置一致性
        errors = self.validate()
        if errors:
            # 验证失败，尝试恢复备份
            if backup_path.exists():
                try:
                    filepath.write_text(backup_path.read_text(), encoding="utf-8")
                except IOError:
                    pass
            raise ConfigError(f"Config validation failed after save: {'; '.join(errors)}")


class ConfigError(Exception):
    """配置错误"""
    pass


def load_config(config_dir: Optional[Path] = None) -> Config:
    """便捷函数：加载 V3 配置"""
    if config_dir is None:
        config_dir = Path.cwd()
    
    loader = ConfigLoader(config_dir)
    return loader.load()
