"""V3 Configuration Loader"""

from pathlib import Path
from typing import Optional
import yaml
from pydantic import ValidationError

from .v3_schema import ConfigV3


class ConfigV3Loader:
    """V3 配置加载器"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
    
    def load(self) -> ConfigV3:
        """从三文件加载配置"""
        providers = self._load_yaml("providers.yaml")
        models = self._load_yaml("models.yaml")
        routing = self._load_yaml("routing.yaml")
        
        try:
            config = ConfigV3(
                providers=providers.get("providers", {}),
                models=models.get("models", {}),
                routing=routing
            )
            return config
        except ValidationError as e:
            raise ConfigV3Error(f"Configuration validation failed: {e}") from e
    
    def _load_yaml(self, filename: str) -> dict:
        """加载单个 YAML 文件"""
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise ConfigV3Error(f"Configuration file not found: {filepath}")
        
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
        except ConfigV3Error as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Unexpected error: {e}")
        
        return errors


class ConfigV3Error(Exception):
    """V3 配置错误"""
    pass


def load_v3_config(config_dir: Optional[Path] = None) -> ConfigV3:
    """便捷函数：加载 V3 配置"""
    if config_dir is None:
        config_dir = Path.cwd()
    
    loader = ConfigV3Loader(config_dir)
    return loader.load()
