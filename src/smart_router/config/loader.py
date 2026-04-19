import os
from pathlib import Path
from typing import Optional, List

import yaml
from rich.console import Console

from .schema import Config

console = Console()

DEFAULT_CONFIG_NAME = "smart-router.yaml"


def find_config(start_path: Optional[Path] = None) -> Path:
    """从当前目录向上查找 smart-router.yaml"""
    if start_path is None:
        start_path = Path.cwd()
    
    current = start_path.resolve()
    while current != current.parent:
        config_file = current / DEFAULT_CONFIG_NAME
        if config_file.exists():
            return config_file
        current = current.parent
    
    raise FileNotFoundError(
        f"未找到 {DEFAULT_CONFIG_NAME}，请运行 `smart-router init` 生成默认配置"
    )


def load_config(config_path: Optional[Path] = None) -> Config:
    """加载并验证配置文件"""
    if config_path is None:
        config_path = find_config()
    else:
        config_path = Path(config_path)
    
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    
    config = Config.model_validate(raw)
    console.print(f"[green]✓[/green] 配置已加载: {config_path}")
    return config


def validate_config(config: Config) -> List[str]:
    """验证配置的完整性，返回错误列表（空表示通过）"""
    errors = []
    
    if not config.model_list:
        errors.append("model_list 为空，至少需要配置一个模型")
    
    # 检查 fallback_chain 中引用的模型是否都在 model_list 中
    model_names = {m.model_name for m in config.model_list}
    for source, targets in config.smart_router.fallback_chain.items():
        if source not in model_names:
            errors.append(f"fallback_chain 中的源模型 '{source}' 未在 model_list 中定义")
        for target in targets:
            if target not in model_names:
                errors.append(f"fallback_chain 中的目标模型 '{target}' 未在 model_list 中定义")
    
    # 检查 stage_routing 中引用的模型
    for stage, routing in config.smart_router.stage_routing.items():
        for level in ["easy", "medium", "hard"]:
            models = getattr(routing, level, [])
            for m in models:
                if m not in model_names:
                    errors.append(f"stage_routing['{stage}'].{level} 中的模型 '{m}' 未定义")
    
    return errors
