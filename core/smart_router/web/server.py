"""Web Dashboard 静态文件服务与 API"""

import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..gateway.daemon import (
    _get_pid,
    _is_process_running,
    _is_port_in_use,
    DEFAULT_PID_FILE,
    DEFAULT_PORT,
    get_start_time,
    stop_daemon,
)
from ..config.loader import ConfigLoader
from ..classifier.task_classifier import TaskTypeClassifier
from ..classifier.difficulty_classifier import DifficultyClassifier
from ..selector.v3_selector import V3ModelSelector
from ..utils.markers import parse_markers

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI()


# ==================== API Endpoints ====================

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.1.0"}


@app.get("/api/status")
async def status():
    pid = _get_pid()
    running = bool(pid and _is_process_running(pid))
    
    uptime_seconds = None
    if running:
        start_ts = get_start_time()
        if start_ts:
            uptime_seconds = int(time.time() - start_ts)
    
    return {
        "running": running,
        "pid": pid,
        "uptime_seconds": uptime_seconds,
        "service_url": f"http://127.0.0.1:{DEFAULT_PORT}" if running else None,
        "version": "1.1.0",
    }


@app.get("/api/models")
async def models():
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
    except Exception:
        return {"models": [], "total": 0, "available": 0, "unavailable": 0}
    
    def is_provider_available(provider_name: str) -> bool:
        if provider_name not in cfg.providers:
            return False
        provider = cfg.providers[provider_name]
        if provider.api_key.startswith("os.environ/"):
            env_var = provider.api_key.replace("os.environ/", "")
            return os.environ.get(env_var) is not None
        return True
    
    result = []
    for name, model in cfg.models.items():
        caps = model.capabilities
        provider_available = is_provider_available(model.provider)
        result.append({
            "name": name,
            "provider": model.provider,
            "available": provider_available,
            "quality": caps.quality,
            "cost": caps.cost,
            "context": caps.context,
            "supported_tasks": model.supported_tasks,
        })
    
    available_count = sum(1 for m in result if m["available"])
    return {
        "models": result,
        "total": len(result),
        "available": available_count,
        "unavailable": len(result) - available_count,
    }


@app.get("/api/providers")
async def providers():
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
    except Exception:
        return {"providers": []}

    result = []
    for name, provider in cfg.providers.items():
        if provider.api_key.startswith("os.environ/"):
            env_var = provider.api_key.replace("os.environ/", "")
            has_key = os.environ.get(env_var) is not None
            key_type = f"env:{env_var}"
        else:
            has_key = True
            key_type = "direct"

        result.append({
            "name": name,
            "api_base": provider.api_base,
            "timeout": provider.timeout,
            "key_type": key_type,
            "has_key": has_key,
        })

    return {"providers": result}


class ProviderUpdate(BaseModel):
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    timeout: Optional[int] = None


class ProvidersUpdateRequest(BaseModel):
    providers: dict[str, ProviderUpdate]


@app.put("/api/providers")
async def update_providers(request: ProvidersUpdateRequest):
    config_dir = Path.home() / ".smart-router"
    loader = ConfigLoader(config_dir)

    try:
        # 读取当前 providers.yaml 以保留其他顶层字段（如果有的话）
        current = loader._load_yaml("providers.yaml")
        providers_node = current.get("providers", {})

        # 用请求体中的非 None 字段逐个覆盖对应 provider
        for name, update in request.providers.items():
            if name not in providers_node:
                return {"success": False, "errors": [f"Provider not found: {name}"]}

            existing = providers_node[name]
            if update.api_base is not None:
                existing["api_base"] = update.api_base
            if update.api_key is not None:
                existing["api_key"] = update.api_key
            if update.timeout is not None:
                existing["timeout"] = update.timeout

        loader.save_providers(providers_node)
        return {"success": True}
    except Exception as e:
        return {"success": False, "errors": [str(e)]}


class DryRunRequest(BaseModel):
    prompt: str
    strategy: str = "auto"


@app.post("/api/dry-run")
async def dry_run(request: DryRunRequest):
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
    except Exception as e:
        return {"error": str(e)}
    
    messages = [{"role": "user", "content": request.prompt}]
    markers = parse_markers(messages)
    
    # 任务分类
    task_types_config = {
        task_id: {
            "name": task_config.name,
            "description": task_config.description,
            "capability_weights": task_config.capability_weights,
        }
        for task_id, task_config in cfg.routing.tasks.items()
    }
    task_classifier = TaskTypeClassifier(task_types_config)
    
    if markers.stage:
        task_type = markers.stage
        task_confidence = 1.0
    else:
        task_result = task_classifier.classify(messages)
        task_type = task_result.task_type
        task_confidence = task_result.confidence
    
    # 难度评估
    if markers.difficulty:
        difficulty = markers.difficulty
        diff_confidence = 1.0
    else:
        difficulty_config = [
            {
                "pattern": ".*",
                "difficulty": diff_id,
                "description": diff_config.description,
                "max_tokens": diff_config.max_tokens,
            }
            for diff_id, diff_config in cfg.routing.difficulties.items()
        ]
        difficulty_classifier = DifficultyClassifier(difficulty_config)
        diff_result = difficulty_classifier.classify(request.prompt, task_type=task_type)
        difficulty = diff_result.difficulty
        diff_confidence = diff_result.confidence
    
    # 模型选择
    available_models = cfg.get_available_models()
    selector = V3ModelSelector(cfg, available_models=available_models)
    
    selection_result = selector.select(
        task_type=task_type,
        difficulty=difficulty,
        strategy=request.strategy,
    )
    
    return {
        "task_type": task_type,
        "task_confidence": round(task_confidence, 2),
        "difficulty": difficulty,
        "difficulty_confidence": round(diff_confidence, 2),
        "selected_model": selection_result.model_name,
        "strategy": selection_result.strategy,
        "score": round(selection_result.score, 3),
        "reason": selection_result.reason,
    }


@app.post("/api/stop")
async def stop():
    stop_daemon()
    return {"success": True, "message": "Smart Router stopped"}


# ==================== Static Files ====================

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"detail": "Frontend not built. Run: make build-web"}
