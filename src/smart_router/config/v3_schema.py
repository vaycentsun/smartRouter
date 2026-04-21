"""V3 Configuration Schema — 兼容别名模块

保留向后兼容，供引用 v3_schema 的代码和测试使用。
实际实现已合并到 schema.py 中。
"""

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

# 向后兼容别名
ConfigV3 = Config

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
    "ConfigV3",
]
