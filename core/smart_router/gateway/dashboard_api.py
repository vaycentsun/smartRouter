"""Dashboard API 路由与 App 构建

原本位于 core/smart_router/web/server.py，后因后台模式内联化被移除。
现将 API 路由逻辑提取到本模块，供 daemon.py 的前台/后台模式共用。
"""

import os
import signal
import socket
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from ..config.loader import ConfigLoader
from ..classifier.task_classifier import TaskTypeClassifier
from ..classifier.difficulty_classifier import DifficultyClassifier
from ..selector.v3_selector import V3ModelSelector
from ..utils.markers import parse_markers


# ==================== 进程管理工具（从 daemon.py 内联，避免循环导入）====================

DEFAULT_PID_DIR = Path.home() / ".smart-router"
DEFAULT_PID_FILE = DEFAULT_PID_DIR / "smart-router.pid"
START_TIME_FILE = DEFAULT_PID_DIR / "start_time"
DEFAULT_PORT = 4000


def _get_pid() -> Optional[int]:
    if DEFAULT_PID_FILE.exists():
        try:
            return int(DEFAULT_PID_FILE.read_text().strip())
        except (ValueError, IOError):
            return None
    return None


def _is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _is_port_in_use(port: int = DEFAULT_PORT) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            return result == 0
    except (OSError, socket.error):
        return False


def get_start_time() -> Optional[float]:
    if START_TIME_FILE.exists():
        try:
            return float(START_TIME_FILE.read_text().strip())
        except (ValueError, IOError):
            return None
    return None


def _remove_pid():
    if DEFAULT_PID_FILE.exists():
        DEFAULT_PID_FILE.unlink()


def _remove_start_time():
    if START_TIME_FILE.exists():
        START_TIME_FILE.unlink()


def stop_daemon():
    pid = _get_pid()
    if not pid:
        return
    if not _is_process_running(pid):
        _remove_pid()
        return
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.5)
            if not _is_process_running(pid):
                break
        if _is_process_running(pid):
            os.kill(pid, signal.SIGKILL)
        _remove_pid()
        _remove_start_time()
    except Exception:
        pass


# ==================== Pydantic 模型 ====================

class ProviderUpdate(BaseModel):
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    timeout: Optional[int] = None


class ProvidersUpdateRequest(BaseModel):
    providers: dict[str, ProviderUpdate]


class DryRunRequest(BaseModel):
    prompt: str
    strategy: str = "auto"


class LogsResponse(BaseModel):
    lines: list[str]
    offset: int
    total_size: int


LOG_FILE_MAP = {
    "service": DEFAULT_PID_DIR / "smart-router.log",
    "dashboard": DEFAULT_PID_DIR / "dashboard.log",
}


def read_log_lines(source: str, offset: int, limit: int = 500) -> LogsResponse:
    """读取日志文件指定偏移之后的新行

    Args:
        source: 日志源，"service" 或 "dashboard"
        offset: 已读取的字节数
        limit: 最大返回行数

    Returns:
        LogsResponse: 包含新行列表、新的 offset 和文件总大小
    """
    if source not in LOG_FILE_MAP:
        raise ValueError(f"Invalid log source: {source}")

    log_path = LOG_FILE_MAP[source]

    if not log_path.exists():
        return LogsResponse(lines=[], offset=0, total_size=0)

    content = log_path.read_bytes()
    total_size = len(content)

    # 文件被清空或轮转：offset 超出范围，从头开始
    if offset > total_size:
        offset = 0

    new_content = content[offset:]
    text = new_content.decode("utf-8", errors="replace")
    lines = text.splitlines()

    if len(lines) > limit:
        lines = lines[-limit:]

    return LogsResponse(lines=lines, offset=total_size, total_size=total_size)


# ==================== API 处理函数 ====================

async def health():
    return {"status": "ok", "version": "1.1.0"}


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


def mask_key(key: str) -> str:
    """对 API Key 进行脱敏：前4后4，中间用 ... 代替"""
    if len(key) <= 8:
        return "****"
    return key[:4] + "..." + key[-4:]


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
            masked_key = ""
        elif provider.api_key:
            has_key = True
            key_type = "direct"
            masked_key = mask_key(provider.api_key)
        else:
            has_key = False
            key_type = "direct"
            masked_key = ""

        result.append({
            "name": name,
            "api_base": provider.api_base,
            "timeout": provider.timeout,
            "key_type": key_type,
            "has_key": has_key,
            "masked_key": masked_key,
        })

    return {"providers": result}


async def update_providers(request: ProvidersUpdateRequest):
    config_dir = Path.home() / ".smart-router"
    loader = ConfigLoader(config_dir)

    try:
        current = loader._load_yaml("providers.yaml")
        providers_node = current.get("providers", {})

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


async def dry_run(request: DryRunRequest):
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
    except Exception as e:
        return {"error": str(e)}

    messages = [{"role": "user", "content": request.prompt}]
    markers = parse_markers(messages)

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


async def model_overrides():
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
    except Exception:
        return {"overrides": {}}

    overrides: dict[str, list[str]] = {}
    for name, model in cfg.models.items():
        if cfg.is_model_available(name):
            if model.provider not in overrides:
                overrides[model.provider] = []
            overrides[model.provider].append(name)
    return {"overrides": overrides}


async def stop():
    stop_daemon()
    return {"success": True, "message": "Smart Router stopped"}


async def get_logs(source: str = "service", offset: int = 0, limit: int = 500):
    try:
        result = read_log_lines(source, offset, limit)
        return {
            "lines": result.lines,
            "offset": result.offset,
            "total_size": result.total_size,
        }
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {e}")


async def token_stats():
    from ..utils.token_stats import TokenStats
    stats = TokenStats()
    data = stats.get_all()

    result = []
    total_prompt = 0
    total_completion = 0
    total_requests = 0

    for model, entry in data.items():
        result.append({
            "model": model,
            "prompt_tokens": entry.get("prompt_tokens", 0),
            "completion_tokens": entry.get("completion_tokens", 0),
            "total_tokens": entry.get("total_tokens", 0),
            "request_count": entry.get("request_count", 0),
        })
        total_prompt += entry.get("prompt_tokens", 0)
        total_completion += entry.get("completion_tokens", 0)
        total_requests += entry.get("request_count", 0)

    return {
        "stats": result,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_requests": total_requests,
    }


# ==================== App 构建 ====================

def build_dashboard_app(static_dir: Optional[Path] = None):
    """构建 Dashboard FastAPI app

    Args:
        static_dir: 前端静态文件目录。若为 None 或不存在，则仅提供 API。
    """
    app = FastAPI()

    app.get("/api/health")(health)
    app.get("/api/status")(status)
    app.get("/api/models")(models)
    app.get("/api/providers")(providers)
    app.put("/api/providers")(update_providers)
    app.get("/api/model-overrides")(model_overrides)
    app.post("/api/dry-run")(dry_run)
    app.post("/api/stop")(stop)
    app.get("/api/logs")(get_logs)
    app.get("/api/token-stats")(token_stats)

    if static_dir and static_dir.exists():
        # 将 Mount 追加到 routes 末尾，确保 API 路由优先匹配
        app.routes.append(
            Mount(
                "/",
                app=StaticFiles(directory=str(static_dir), html=True),
                name="static",
            )
        )

    return app
