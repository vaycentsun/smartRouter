"""全局模型覆盖状态持久化存储

Dashboard 和 Proxy 运行在不同进程中，通过 JSON 文件共享 override 状态。
文件位置: ~/.smart-router/global_model_override.json
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_OVERRIDE_FILE = Path.home() / ".smart-router" / "global_model_override.json"


def load_override_state(path: Optional[Path] = None) -> dict:
    """从文件加载全局模型覆盖状态
    
    Returns:
        {"provider": str|None, "model": str|None, "enabled": bool}
    """
    override_file = path or DEFAULT_OVERRIDE_FILE
    if not override_file.exists():
        return {"provider": None, "model": None, "enabled": False}
    
    try:
        with open(override_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "provider": data.get("provider"),
            "model": data.get("model"),
            "enabled": data.get("enabled", False),
        }
    except (json.JSONDecodeError, IOError, KeyError) as e:
        logger.warning(f"Failed to load global model override state: {e}")
        return {"provider": None, "model": None, "enabled": False}


def save_override_state(provider: Optional[str], model: Optional[str], enabled: bool, path: Optional[Path] = None):
    """保存全局模型覆盖状态到文件"""
    override_file = path or DEFAULT_OVERRIDE_FILE
    override_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "provider": provider,
        "model": model,
        "enabled": enabled,
    }
    
    tmp = override_file.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, override_file)
    
    # 敏感数据文件权限设为 0o600
    try:
        os.chmod(override_file, 0o600)
    except OSError:
        pass
    
    logger.info(f"Global model override saved: provider={provider}, model={model}, enabled={enabled}")


def clear_override_state(path: Optional[Path] = None):
    """清除全局模型覆盖状态"""
    save_override_state(None, None, False, path=path)
