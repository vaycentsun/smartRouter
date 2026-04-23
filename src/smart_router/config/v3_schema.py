"""V3 Schema Compatibility Module

将现有的 schema.py 导出为 v3_schema 命名空间，
以保持与遗留测试的兼容性。
"""

from .schema import (
    Config as ConfigV3,
    ProviderConfig,
    ModelCapabilities,
    ModelConfig,
    TaskConfig,
    DifficultyConfig,
    StrategyConfig,
    FallbackConfig,
    RoutingConfig,
)

__all__ = [
    "ConfigV3",
    "ProviderConfig",
    "ModelCapabilities",
    "ModelConfig",
    "TaskConfig",
    "DifficultyConfig",
    "StrategyConfig",
    "FallbackConfig",
    "RoutingConfig",
]
