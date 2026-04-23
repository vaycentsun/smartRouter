"""V3 Loader Compatibility Module

将现有的 loader.py 导出为 v3_loader 命名空间，
以保持与遗留测试的兼容性。
"""

from .loader import ConfigLoader as ConfigV3Loader, ConfigError as ConfigV3Error, load_config as load_v3_config

__all__ = [
    "ConfigV3Loader",
    "ConfigV3Error",
    "load_v3_config",
]
