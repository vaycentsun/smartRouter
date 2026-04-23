"""V3 Configuration Loader — 兼容别名模块

保留向后兼容，供引用 v3_loader 的代码和测试使用。
实际实现已合并到 loader.py 中。
"""

from .loader import ConfigLoader, ConfigError, load_config

# 向后兼容别名
ConfigV3Loader = ConfigLoader
ConfigV3Error = ConfigError
load_v3_config = load_config

__all__ = [
    "ConfigLoader",
    "ConfigError",
    "load_config",
    "ConfigV3Loader",
    "ConfigV3Error",
    "load_v3_config",
]
