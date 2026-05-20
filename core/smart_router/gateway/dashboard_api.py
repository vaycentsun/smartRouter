"""Dashboard API 路由与 App 构建

原本位于 core/smart_router/web/server.py，后因后台模式内联化被移除。
现将 API 路由逻辑提取到本模块，供 daemon.py 的前台/后台模式共用。
"""

import logging
import os
import signal
import socket
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel

from smart_router import __version__
from smart_router.utils.log_parser import parse_log_line
from ..config.loader import ConfigLoader
from ..classifier.task_classifier import TaskTypeClassifier
from ..classifier.difficulty_classifier import DifficultyClassifier
from ..selector.v3_selector import V3ModelSelector
from ..utils.markers import parse_markers
from ..utils.health_checker import ProviderHealthChecker
from .playground_api import playground_router
from ..alerts.config import AlertConfig, AlertRule, AlertCondition, AlertChannel


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


class FormulaUpdate(BaseModel):
    weights: dict[str, float]


class FormulaPreviewRequest(BaseModel):
    weights: dict[str, float]
    prompt: str = ""


class LogReadResult(BaseModel):
    lines: list[str]
    structured_lines: list[dict]
    offset: int
    total_size: int


class AlertRuleCreate(BaseModel):
    id: str
    name: str
    enabled: bool = True
    condition: AlertCondition
    severity: str = "warning"
    time_window: str = "1d"
    channels: list[AlertChannel] = []
    cooldown_minutes: int = 60


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    condition: Optional[AlertCondition] = None
    severity: Optional[str] = None
    time_window: Optional[str] = None
    channels: Optional[list[AlertChannel]] = None
    cooldown_minutes: Optional[int] = None


class ModelOverrideRequest(BaseModel):
    provider: str
    model: str


class ModelOverrideResponse(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    enabled: bool = False


class ModelToggleRequest(BaseModel):
    enabled: bool


class ProviderToggleRequest(BaseModel):
    enabled: bool


LOG_FILE_MAP = {
    "service": DEFAULT_PID_DIR / "smart-router.log",
    "dashboard": DEFAULT_PID_DIR / "dashboard.log",
}


def read_log_lines(source: str, offset: int = 0, limit: int = 500, level: str = "ALL") -> LogReadResult:
    """读取日志文件指定偏移之后的新行

    Args:
        source: 日志源，"service" 或 "dashboard"
        offset: 已读取的字节数
        limit: 最大返回行数
        level: 日志等级筛选，"ALL" 表示不过滤

    Returns:
        LogReadResult: 包含新行列表、结构化数据、新的 offset 和文件总大小
    """
    if source not in LOG_FILE_MAP:
        raise ValueError(f"Invalid log source: {source}")

    log_file = LOG_FILE_MAP[source]

    if not log_file.exists():
        return LogReadResult(lines=[], structured_lines=[], offset=0, total_size=0)

    total_size = log_file.stat().st_size

    # 文件被清空或轮转：offset 超出范围，从头开始
    if offset > total_size:
        offset = 0

    # 解析等级参数
    level_filter = None
    if level.upper() != "ALL":
        level_filter = getattr(logging, level.upper(), None)
        if level_filter is None:
            raise ValueError(f"Invalid log level: {level}")

    # 读取从 offset 到文件末尾的内容
    with open(log_file, "r", encoding="utf-8") as f:
        f.seek(offset)
        content = f.read()
        new_offset = f.tell()

    # 解析每一行
    lines = content.splitlines()
    result_lines = []
    structured_lines = []

    for line in lines:
        parsed = parse_log_line(line)

        # 等级筛选
        if level_filter is not None:
            if parsed.levelno < level_filter:
                continue

        result_lines.append(line.rstrip())
        structured_lines.append({
            "timestamp": parsed.timestamp,
            "level": parsed.level,
            "name": parsed.name,
            "message": parsed.message,
        })

    # 如果超过 limit，取最后 limit 行（保持旧行为）
    if len(result_lines) > limit:
        result_lines = result_lines[-limit:]
        structured_lines = structured_lines[-limit:]

    return LogReadResult(
        lines=result_lines,
        structured_lines=structured_lines,
        offset=new_offset,
        total_size=total_size,
    )


# ==================== API 处理函数 ====================

async def health():
    return {"status": "ok", "version": __version__}


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
        "version": __version__,
    }


async def models(request: Request):
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

    def get_health_status(model) -> str:
        """根据缓存的健康检查结果计算模型健康状态"""
        checker = getattr(request.app.state, "health_checker", None)
        if not checker:
            return "unknown"
        
        health = checker.get_cached(model.provider)
        if not health:
            return "unknown"
        
        if health.status != "healthy":
            return health.status
        
        # 提取 litellm_model 后半部分进行匹配
        litellm_model = model.litellm_model
        model_id = litellm_model.split("/")[-1] if "/" in litellm_model else litellm_model
        
        if model_id in health.models:
            return "available"
        return "not_found"

    result = []
    for name, model in cfg.models.items():
        caps = model.capabilities
        provider_available = is_provider_available(model.provider)
        result.append({
            "name": name,
            "provider": model.provider,
            "available": provider_available,
            "health_status": get_health_status(model),
            "quality": caps.quality,
            "cost": caps.cost,
            "context": caps.context,
            "supported_tasks": model.supported_tasks,
            "enabled": getattr(model, 'enabled', True),
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


async def providers(request: Request):
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
    except Exception:
        return {"providers": []}

    checker = getattr(request.app.state, "health_checker", None)

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

        health_data = None
        if checker:
            health = checker.get_cached(name)
            if health:
                health_data = {
                    "status": health.status,
                    "checked_at": health.checked_at,
                }

        result.append({
            "name": name,
            "api_base": provider.api_base,
            "timeout": provider.timeout,
            "key_type": key_type,
            "has_key": has_key,
            "masked_key": masked_key,
            "health": health_data,
            "enabled": getattr(provider, 'enabled', True),
        })

    return {"providers": result}


async def provider_health(request: Request, provider_name: str):
    """触发 Provider 健康检查（跳过缓存）"""
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置加载失败: {e}")

    if provider_name not in cfg.providers:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_name}")

    checker = getattr(request.app.state, "health_checker", None)
    if not checker:
        raise HTTPException(status_code=500, detail="Health checker not initialized")

    # 更新 checker 的配置为最新，避免用户修改 providers.yaml 后仍使用旧配置
    checker.config = cfg

    result = await checker.check(provider_name, force=True)

    return {
        "provider": provider_name,
        "status": result.status,
        "models": result.models,
        "checked_at": result.checked_at,
        "error": result.error,
    }


async def provider_models(request: Request, provider_name: str):
    """获取 Provider 上次健康检查结果（含模型清单）"""
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置加载失败: {e}")

    if provider_name not in cfg.providers:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_name}")

    checker = getattr(request.app.state, "health_checker", None)
    if not checker:
        raise HTTPException(status_code=500, detail="Health checker not initialized")

    # 更新 checker 的配置为最新，避免用户修改 providers.yaml 后仍使用旧配置
    checker.config = cfg

    result = checker.get_cached(provider_name)
    if not result:
        return {
            "provider": provider_name,
            "status": None,
            "configured_models": [],
            "provider_models": [],
            "checked_at": None,
        }

    # 构建配置的模型列表（带匹配状态）
    configured_models = []
    for name, model in cfg.models.items():
        if model.provider == provider_name:
            litellm_model = model.litellm_model
            model_id = litellm_model.split("/")[-1] if "/" in litellm_model else litellm_model
            configured_models.append({
                "name": name,
                "litellm_model": litellm_model,
                "found": model_id in result.models if result.status == "healthy" else None,
            })

    return {
        "provider": provider_name,
        "status": result.status,
        "configured_models": configured_models,
        "provider_models": result.models,
        "checked_at": result.checked_at,
        "error": result.error,
    }


async def toggle_model(request: Request, provider_name: str, model_name: str, body: ModelToggleRequest):
    """切换模型启用/禁用状态

    Args:
        provider_name: Provider 名称
        model_name: 模型名称
        body: { enabled: bool }

    Returns:
        { "success": True, "provider": str, "model": str, "enabled": bool }

    Raises:
        HTTPException(404): Provider 或 Model 不存在
        HTTPException(500): 保存或验证失败
    """
    config_dir = Path.home() / ".smart-router"
    loader = ConfigLoader(config_dir)

    try:
        cfg = loader.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置加载失败: {e}")

    if provider_name not in cfg.providers:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_name}")

    if model_name not in cfg.models:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")

    model = cfg.models[model_name]
    if model.provider != provider_name:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' does not belong to provider '{provider_name}'")

    try:
        loader.save_model(provider_name, model_name, body.enabled)
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 触发配置热重载
    router = getattr(request.app.state, "router", None)
    if router and hasattr(router, "reload_config"):
        try:
            router.reload_config()
        except Exception:
            pass  # 热重载失败不阻塞 API 响应

    return {
        "success": True,
        "provider": provider_name,
        "model": model_name,
        "enabled": body.enabled,
    }


async def toggle_provider(request: Request, provider_name: str, body: ProviderToggleRequest):
    """切换 Provider 启用/禁用状态

    Args:
        provider_name: Provider 名称
        body: { enabled: bool }

    Returns:
        { "success": True, "provider": str, "enabled": bool }

    Raises:
        HTTPException(404): Provider 不存在
        HTTPException(500): 保存或验证失败
    """
    config_dir = Path.home() / ".smart-router"
    loader = ConfigLoader(config_dir)

    try:
        cfg = loader.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置加载失败: {e}")

    if provider_name not in cfg.providers:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_name}")

    try:
        loader.save_provider_enabled(provider_name, body.enabled)
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 触发配置热重载
    router = getattr(request.app.state, "router", None)
    if router and hasattr(router, "reload_config"):
        try:
            router.reload_config()
        except Exception:
            pass  # 热重载失败不阻塞 API 响应

    return {
        "success": True,
        "provider": provider_name,
        "enabled": body.enabled,
    }


async def update_providers(request: ProvidersUpdateRequest):
    config_dir = Path.home() / ".smart-router"
    loader = ConfigLoader(config_dir)

    try:
        current = loader._load_yaml("providers.yaml")
        providers_node = current.get("providers", {})

        for name, update in request.providers.items():
            if name not in providers_node:
                raise HTTPException(status_code=404, detail=f"Provider not found: {name}")

            existing = providers_node[name]
            if update.api_base is not None:
                existing["api_base"] = update.api_base
            if update.api_key is not None:
                existing["api_key"] = update.api_key
            if update.timeout is not None:
                existing["timeout"] = update.timeout

        loader.save_providers(providers_node)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        "fallback_chain": cfg.get_fallback_chain(selection_result.model_name),
    }


async def get_formula(request: Request):
    """获取当前公式配置"""
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
        return {"weights": cfg.routing.formula.weights}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def update_formula(request: Request, body: FormulaUpdate):
    """更新公式配置并保存到 routing.yaml"""
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        
        # 验证权重
        from ..config.schema import FormulaConfig
        from pydantic import ValidationError
        try:
            FormulaConfig(weights=body.weights)
        except (ValueError, ValidationError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # 加载当前 routing.yaml
        current = loader._load_yaml("routing.yaml")
        current["formula"] = {"weights": body.weights}
        
        # 保存
        try:
            loader.save_routing(current)
            return {"success": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    except (HTTPException, ValidationError):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def preview_formula(request: Request, body: FormulaPreviewRequest):
    """预览公式效果：按传入的 weights 计算所有可用模型的得分"""
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
        
        # 验证权重
        from ..config.schema import FormulaConfig
        from pydantic import ValidationError
        try:
            FormulaConfig(weights=body.weights)
        except (ValueError, ValidationError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # 使用临时 evaluator
        temp_formula = FormulaConfig(weights=body.weights)
        from ..selector.formula_evaluator import FormulaEvaluator
        evaluator = FormulaEvaluator(temp_formula)
        
        # 计算所有可用模型的得分
        models = []
        for name, model in cfg.models.items():
            if cfg.is_model_available(name):
                score = evaluator.evaluate(model.capabilities)
                models.append({"name": name, "score": round(score, 2)})
        
        models.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "task_type": "chat",
            "difficulty": "medium",
            "models": models
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


async def get_model_override(request: Request):
    """获取当前全局模型覆盖状态（优先从文件读取，兼容跨进程共享）"""
    from ..utils.model_override_store import load_override_state
    state = load_override_state()
    if state.get('enabled'):
        return {
            "provider": state.get('provider'),
            "model": state.get('model'),
            "enabled": True,
        }
    return {"provider": None, "model": None, "enabled": False}


async def set_model_override(request: Request, body: ModelOverrideRequest):
    """设置全局模型覆盖"""
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置加载失败: {e}")

    model_name = body.model
    if model_name not in cfg.models:
        raise HTTPException(status_code=400, detail=f"未知模型: {model_name}")

    model_config = cfg.models[model_name]
    if model_config.provider != body.provider:
        raise HTTPException(
            status_code=400,
            detail=f"Provider 不匹配: 模型 {model_name} 属于 {model_config.provider}，而非 {body.provider}"
        )

    if not cfg.is_model_available(model_name):
        raise HTTPException(status_code=400, detail=f"模型不可用: {model_name}")

    # 同时更新内存状态和文件状态（供 Proxy 进程读取）
    request.app.state.global_model_override = {
        "provider": body.provider,
        "model": body.model,
        "enabled": True,
    }
    from ..utils.model_override_store import save_override_state
    save_override_state(body.provider, body.model, True)
    return {
        "provider": body.provider,
        "model": body.model,
        "enabled": True,
    }


async def delete_model_override(request: Request):
    """清除全局模型覆盖"""
    if hasattr(request.app.state, 'global_model_override'):
        request.app.state.global_model_override = {
            "provider": None,
            "model": None,
            "enabled": False,
        }
    from ..utils.model_override_store import clear_override_state
    clear_override_state()
    return {"provider": None, "model": None, "enabled": False}


async def stop():
    stop_daemon()
    return {"success": True, "message": "Smart Router stopped"}


async def get_logs(source: str = "service", offset: int = 0, limit: int = 500, level: str = "ALL"):
    try:
        result = read_log_lines(source, offset, limit, level)
        return {
            "lines": result.lines,
            "structured_lines": result.structured_lines,
            "offset": result.offset,
            "total_size": result.total_size,
        }
    except ValueError as e:
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
    total_reasoning = 0
    total_cached = 0
    total_requests = 0

    for model, entry in data.items():
        result.append({
            "model": model,
            "prompt_tokens": entry.get("prompt_tokens", 0),
            "completion_tokens": entry.get("completion_tokens", 0),
            "total_tokens": entry.get("total_tokens", 0),
            "reasoning_tokens": entry.get("reasoning_tokens", 0),
            "cached_tokens": entry.get("cached_tokens", 0),
            "request_count": entry.get("request_count", 0),
        })
        total_prompt += entry.get("prompt_tokens", 0)
        total_completion += entry.get("completion_tokens", 0)
        total_reasoning += entry.get("reasoning_tokens", 0)
        total_cached += entry.get("cached_tokens", 0)
        total_requests += entry.get("request_count", 0)

    return {
        "stats": result,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_reasoning_tokens": total_reasoning,
        "total_cached_tokens": total_cached,
        "total_requests": total_requests,
    }


# ==================== Analytics API ====================

def _load_config_for_analytics():
    """加载配置用于分析，失败时返回 None"""
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        return loader.load()
    except Exception:
        return None


def _clamp_days(days: int) -> int:
    """限制 days 最大 90"""
    if days < 1:
        return 1
    return min(days, 90)


def _compute_cost(prompt_tokens: int, completion_tokens: int, price) -> float:
    """根据单价计算成本"""
    if price is None:
        return 0.0
    return (prompt_tokens / 1000 * price.prompt_per_1k) + (completion_tokens / 1000 * price.completion_per_1k)


async def analytics_summary(days: int = 7):
    """汇总统计：总成本、请求数、token 数"""
    from ..utils.token_stats import TokenStats
    days = _clamp_days(days)
    stats = TokenStats()
    summary = stats.get_summary(days)
    config = _load_config_for_analytics()

    total_cost = 0.0
    incomplete = False
    model_breakdown = summary.get("model_breakdown", {})

    if config and model_breakdown:
        for model_name, entry in model_breakdown.items():
            model_config = config.models.get(model_name)
            price = getattr(model_config, "price", None) if model_config else None
            if price is None:
                incomplete = True
                continue
            total_cost += _compute_cost(
                entry.get("prompt_tokens", 0),
                entry.get("completion_tokens", 0),
                price,
            )
    elif model_breakdown:
        incomplete = True

    total_prompt_tokens = summary.get("total_prompt_tokens", 0)
    total_completion_tokens = summary.get("total_completion_tokens", 0)
    total_reasoning_tokens = summary.get("total_reasoning_tokens", 0)
    total_cached_tokens = summary.get("total_cached_tokens", 0)
    total_tokens = total_prompt_tokens + total_completion_tokens
    avg_daily_cost = total_cost / days if days > 0 else 0.0

    return {
        "total_cost": total_cost,
        "total_requests": summary.get("total_requests", 0),
        "total_tokens": total_tokens,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_reasoning_tokens": total_reasoning_tokens,
        "total_cached_tokens": total_cached_tokens,
        "avg_daily_cost": avg_daily_cost,
        "incomplete": incomplete,
    }


async def analytics_daily(days: int = 7):
    """每日趋势"""
    from ..utils.token_stats import TokenStats
    days = _clamp_days(days)
    stats = TokenStats()
    config = _load_config_for_analytics()
    # 获取最近 days 天的日期范围
    import time
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    result = []
    for i in range(days):
        date_obj = now - timedelta(days=i)
        date_str = date_obj.strftime("%Y-%m-%d")
        daily = stats.get_daily(date_str)
        if daily:
            day_cost = 0.0
            day_requests = 0
            day_tokens = 0
            day_reasoning = 0
            day_cached = 0
            for model_name, entry in daily.items():
                day_requests += entry.get("request_count", 0)
                day_tokens += entry.get("total_tokens", 0)
                day_reasoning += entry.get("reasoning_tokens", 0)
                day_cached += entry.get("cached_tokens", 0)
                model_config = config.models.get(model_name) if config else None
                price = getattr(model_config, "price", None) if model_config else None
                day_cost += _compute_cost(
                    entry.get("prompt_tokens", 0),
                    entry.get("completion_tokens", 0),
                    price,
                )
            result.append({
                "date": date_str,
                "cost": day_cost,
                "requests": day_requests,
                "tokens": day_tokens,
                "reasoning_tokens": day_reasoning,
                "cached_tokens": day_cached,
            })
    return result


async def analytics_by_model(days: int = 7):
    """按模型聚合（含成本）"""
    from ..utils.token_stats import TokenStats
    days = _clamp_days(days)
    stats = TokenStats()
    summary = stats.get_summary(days)
    config = _load_config_for_analytics()

    result = []
    for model_name, entry in summary.get("model_breakdown", {}).items():
        model_config = config.models.get(model_name) if config else None
        price = getattr(model_config, "price", None) if model_config else None
        cost = _compute_cost(
            entry.get("prompt_tokens", 0),
            entry.get("completion_tokens", 0),
            price,
        )
        result.append({
            "model": model_name,
            "prompt_tokens": entry.get("prompt_tokens", 0),
            "completion_tokens": entry.get("completion_tokens", 0),
            "total_tokens": entry.get("total_tokens", 0),
            "reasoning_tokens": entry.get("reasoning_tokens", 0),
            "cached_tokens": entry.get("cached_tokens", 0),
            "cost": cost,
            "request_count": entry.get("request_count", 0),
        })
    return result


async def analytics_top_models(limit: int = 10, days: int = 7):
    """TOP N 模型（按 request_count 降序）"""
    from ..utils.token_stats import TokenStats
    days = _clamp_days(days)
    limit = max(1, limit)
    stats = TokenStats()
    summary = stats.get_summary(days)
    config = _load_config_for_analytics()

    items = []
    for model_name, entry in summary.get("model_breakdown", {}).items():
        model_config = config.models.get(model_name) if config else None
        price = getattr(model_config, "price", None) if model_config else None
        cost = _compute_cost(
            entry.get("prompt_tokens", 0),
            entry.get("completion_tokens", 0),
            price,
        )
        items.append({
            "model": model_name,
            "prompt_tokens": entry.get("prompt_tokens", 0),
            "completion_tokens": entry.get("completion_tokens", 0),
            "total_tokens": entry.get("total_tokens", 0),
            "reasoning_tokens": entry.get("reasoning_tokens", 0),
            "cached_tokens": entry.get("cached_tokens", 0),
            "request_count": entry.get("request_count", 0),
            "cost": cost,
        })

    items.sort(key=lambda x: x["request_count"], reverse=True)
    return items[:limit]


async def analytics_recent_requests(request: Request, limit: int = 50):
    """获取最近 N 条请求路由记录"""
    history = getattr(request.app.state, 'request_routing_history', None)
    if not history:
        return {"requests": []}
    return {"requests": history.get_recent(limit)}


async def analytics_error_stats(request: Request, days: int = 7):
    """获取模型错误统计（供 Dashboard 展示模型失败率）"""
    history = getattr(request.app.state, 'request_routing_history', None)
    if not history:
        return {
            "models": [],
            "error_types": [],
            "provider_errors": [],
            "total_requests": 0,
            "total_failures": 0,
            "failure_rate": 0.0,
        }

    records = history.get_recent(limit=100)

    model_stats = {}
    error_type_counts = {}
    provider_error_counts = {}
    total_requests = len(records)
    total_failures = 0

    for record in records:
        retry_history = record.get("retry_history", [])
        is_failed = record.get("status_code", 200) >= 500 or record.get("error_info")
        if is_failed:
            total_failures += 1

        for retry in retry_history:
            model_name = retry.get("model", "unknown")
            provider = retry.get("provider", "unknown")
            error_type = retry.get("error_type", "Unknown")

            if model_name not in model_stats:
                model_stats[model_name] = {
                    "model": model_name,
                    "provider": provider,
                    "total_attempts": 0,
                    "failures": 0,
                    "error_types": {},
                }
            model_stats[model_name]["total_attempts"] += 1
            model_stats[model_name]["failures"] += 1

            err_types = model_stats[model_name]["error_types"]
            err_types[error_type] = err_types.get(error_type, 0) + 1

            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
            provider_key = f"{provider}:{error_type}"
            provider_error_counts[provider_key] = provider_error_counts.get(provider_key, 0) + 1

    model_list = []
    for model_name, stats in model_stats.items():
        total = stats["total_attempts"]
        failures = stats["failures"]
        success_rate = (total - failures) / total * 100 if total > 0 else 100.0
        model_list.append({
            "model": model_name,
            "provider": stats["provider"],
            "total_attempts": total,
            "failures": failures,
            "success_rate": round(success_rate, 1),
            "error_types": stats["error_types"],
        })

    model_list.sort(key=lambda x: x["failures"], reverse=True)

    error_types_list = [
        {"error_type": k, "count": v}
        for k, v in sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    provider_errors_list = [
        {"provider": k.split(":")[0], "error_type": k.split(":")[1], "count": v}
        for k, v in sorted(provider_error_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "models": model_list,
        "error_types": error_types_list,
        "provider_errors": provider_errors_list,
        "total_requests": total_requests,
        "total_failures": total_failures,
        "failure_rate": round(total_failures / total_requests * 100, 1) if total_requests > 0 else 0.0,
    }


# ==================== Alerts API ====================

ALERTS_CONFIG_PATH = DEFAULT_PID_DIR / "alerts.yaml"
ALERTS_HISTORY_PATH = DEFAULT_PID_DIR / "alerts_history.json"


def _get_alert_config() -> AlertConfig:
    """获取 AlertConfig 实例"""
    return AlertConfig(ALERTS_CONFIG_PATH)


def _load_alert_history(limit: int = 50) -> list[dict]:
    """加载告警历史"""
    if not ALERTS_HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(ALERTS_HISTORY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data[-limit:]
        return []
    except Exception:
        return []


async def get_alert_rules():
    """获取所有告警规则"""
    cfg = _get_alert_config()
    return {"rules": [r.model_dump() for r in cfg.rules]}


async def create_alert_rule(request: AlertRuleCreate):
    """创建告警规则"""
    cfg = _get_alert_config()
    if cfg.get_rule(request.id):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Rule ID already exists: {request.id}")

    rule = AlertRule(
        id=request.id,
        name=request.name,
        enabled=request.enabled,
        condition=request.condition,
        severity=request.severity,
        time_window=request.time_window,
        channels=request.channels,
        cooldown_minutes=request.cooldown_minutes,
    )
    cfg.add_rule(rule)
    return {"success": True, "rule": rule.model_dump()}


async def update_alert_rule(rule_id: str, request: AlertRuleUpdate):
    """更新告警规则"""
    from fastapi import HTTPException
    cfg = _get_alert_config()
    existing = cfg.get_rule(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    updated = AlertRule(
        id=rule_id,
        name=request.name if request.name is not None else existing.name,
        enabled=request.enabled if request.enabled is not None else existing.enabled,
        condition=request.condition if request.condition is not None else existing.condition,
        severity=request.severity if request.severity is not None else existing.severity,
        time_window=request.time_window if request.time_window is not None else existing.time_window,
        channels=request.channels if request.channels is not None else existing.channels,
        cooldown_minutes=request.cooldown_minutes if request.cooldown_minutes is not None else existing.cooldown_minutes,
    )
    cfg.update_rule(rule_id, updated)
    return {"success": True, "rule": updated.model_dump()}


async def delete_alert_rule(rule_id: str):
    """删除告警规则"""
    from fastapi import HTTPException
    cfg = _get_alert_config()
    if not cfg.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    return {"success": True}


async def get_alert_history(limit: int = 50):
    """获取告警历史"""
    history = _load_alert_history(limit)
    return {"history": history}


async def test_alert_rule(request: AlertRuleCreate):
    """测试告警规则（不保存）"""
    from fastapi import HTTPException
    from ..utils.token_stats import TokenStats
    from .error_counter import ErrorCounter
    from ..alerts.checker import AlertChecker

    cfg = AlertConfig(ALERTS_CONFIG_PATH)
    rule = AlertRule(
        id="test-rule",
        name=request.name,
        enabled=True,
        condition=request.condition,
        severity=request.severity,
        time_window=request.time_window,
        channels=request.channels,
        cooldown_minutes=0,  # 测试时无冷却期
    )
    cfg.rules = [rule]

    token_stats = TokenStats()
    error_counter = ErrorCounter()
    checker = AlertChecker(cfg, token_stats, error_counter)

    triggers = await checker.check_all()

    return {
        "triggered": len(triggers) > 0,
        "triggers": [
            {
                "rule_id": t.rule_id,
                "rule_name": t.rule_name,
                "severity": t.severity,
                "metric": t.metric,
                "current_value": t.current_value,
                "threshold": t.threshold,
                "message": t.message,
            }
            for t in triggers
        ],
    }


# ==================== App 构建 ====================

def build_dashboard_app(static_dir: Optional[Path] = None):
    """构建 Dashboard FastAPI app

    Args:
        static_dir: 前端静态文件目录。若为 None 或不存在，则仅提供 API。
    """
    app = FastAPI()

    # 初始化 Health Checker
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
        app.state.health_checker = ProviderHealthChecker(cfg)
    except Exception:
        app.state.health_checker = None

    # 初始化请求路由历史（使用文件持久化，与 Proxy 进程共享）
    from ..utils.request_routing_history import RequestRoutingHistory, DEFAULT_HISTORY_FILE
    app.state.request_routing_history = RequestRoutingHistory(
        max_size=50, persist_file=DEFAULT_HISTORY_FILE
    )

    app.get("/api/health")(health)
    app.get("/api/status")(status)
    app.get("/api/models")(models)
    app.get("/api/providers")(providers)
    app.get("/api/providers/{provider_name}/health")(provider_health)
    app.get("/api/providers/{provider_name}/models")(provider_models)
    app.put("/api/models/{provider_name}/{model_name}")(toggle_model)
    app.put("/api/providers/{provider_name}/toggle")(toggle_provider)
    app.put("/api/providers")(update_providers)
    app.get("/api/model-overrides")(model_overrides)
    app.get("/api/model-override")(get_model_override)
    app.post("/api/model-override")(set_model_override)
    app.delete("/api/model-override")(delete_model_override)
    app.post("/api/dry-run")(dry_run)
    app.get("/api/formula")(get_formula)
    app.put("/api/formula")(update_formula)
    app.post("/api/formula/preview")(preview_formula)
    app.post("/api/stop")(stop)
    app.get("/api/logs")(get_logs)
    app.get("/api/token-stats")(token_stats)

    # Analytics API
    app.get("/api/analytics/summary")(analytics_summary)
    app.get("/api/analytics/daily")(analytics_daily)
    app.get("/api/analytics/by-model")(analytics_by_model)
    app.get("/api/analytics/top-models")(analytics_top_models)
    app.get("/api/analytics/recent-requests")(analytics_recent_requests)
    app.get("/api/analytics/error-stats")(analytics_error_stats)

    # Alerts API
    app.get("/api/alerts/rules")(get_alert_rules)
    app.post("/api/alerts/rules")(create_alert_rule)
    app.put("/api/alerts/rules/{rule_id}")(update_alert_rule)
    app.delete("/api/alerts/rules/{rule_id}")(delete_alert_rule)
    app.get("/api/alerts/history")(get_alert_history)
    app.post("/api/alerts/test")(test_alert_rule)

    # Playground API
    app.include_router(playground_router, prefix="/api/playground")

    class SPAStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope) -> Response:
            try:
                return await super().get_response(path, scope)
            except StarletteHTTPException as exc:
                if exc.status_code == 404 and "." not in path:
                    return await super().get_response("index.html", scope)
                raise

    if static_dir and static_dir.exists():
        app.routes.append(
            Mount(
                "/",
                app=SPAStaticFiles(directory=str(static_dir), html=True),
                name="static",
            )
        )

    return app
