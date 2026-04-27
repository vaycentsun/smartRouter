"""Smart Router 配置模块"""

from .schema import (
    ProviderConfig,
    ModelCapabilities,
    ModelConfig,
    TaskConfig,
    DifficultyConfig,
    StrategyConfig,
    FallbackConfig,
    RoutingConfig,
    Config,
)
from .loader import ConfigLoader, ConfigError, load_config
from ..exceptions import NoModelAvailableError, UnknownStrategyError

# 向后兼容别名
ConfigV3 = Config
ConfigV3Loader = ConfigLoader
ConfigV3Error = ConfigError
load_v3_config = load_config

__all__ = [
    "ProviderConfig",
    "ModelCapabilities",
    "ModelConfig",
    "TaskConfig",
    "DifficultyConfig",
    "StrategyConfig",
    "FallbackConfig",
    "RoutingConfig",
    "Config",
    "ConfigLoader",
    "ConfigError",
    "load_config",
    "NoModelAvailableError",
    "UnknownStrategyError",
    # 向后兼容别名
    "ConfigV3",
    "ConfigV3Loader",
    "ConfigV3Error",
    "load_v3_config",
]