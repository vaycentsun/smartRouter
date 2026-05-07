"""Playground API - 交互式模型测试

支持单模型调用和多模型对比，结果保存到历史记录。
"""

import asyncio
import json
import re
import time
import uuid
from pathlib import Path
from typing import Literal, Optional

import litellm
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..classifier.difficulty_classifier import DifficultyClassifier
from ..classifier.task_classifier import TaskTypeClassifier
from ..config.loader import ConfigLoader
from ..selector.v3_selector import V3ModelSelector
from ..utils.markers import parse_markers
from ..utils.token_stats import TokenStats

playground_router = APIRouter()

HISTORY_FILE = Path.home() / ".smart-router" / "playground_history.json"
MAX_HISTORY = 50


class PlaygroundRequest(BaseModel):
    mode: Literal["single", "compare"]
    prompt: str = Field(..., max_length=10000)
    models: list[str] = Field(..., min_length=1, max_length=3)
    stream: bool = False


class PlaygroundResult(BaseModel):
    model: str
    provider: str
    response: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: Optional[float]
    error: Optional[str]
    routing_info: Optional[dict]


def _load_config():
    """加载 Smart Router 配置"""
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        return loader.load()
    except Exception:
        return None


def _calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int, config):
    """根据单价计算预估成本"""
    if config is None:
        return None
    model_cfg = config.models.get(model_name)
    if not model_cfg or not model_cfg.price:
        return None
    price = model_cfg.price
    cost = (prompt_tokens / 1000 * price.prompt_per_1k) + (completion_tokens / 1000 * price.completion_per_1k)
    return round(cost, 6)


def _get_routing_info(prompt: str, config):
    """获取路由决策信息"""
    if not config:
        return None

    messages = [{"role": "user", "content": prompt}]
    markers = parse_markers(messages)

    task_types_config = {
        task_id: {
            "name": task_config.name,
            "description": task_config.description,
            "capability_weights": task_config.capability_weights,
        }
        for task_id, task_config in config.routing.tasks.items()
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
            for diff_id, diff_config in config.routing.difficulties.items()
        ]
        difficulty_classifier = DifficultyClassifier(difficulty_config)
        diff_result = difficulty_classifier.classify(prompt, task_type=task_type)
        difficulty = diff_result.difficulty
        diff_confidence = diff_result.confidence

    available_models = config.get_available_models()
    selector = V3ModelSelector(config, available_models=available_models)

    try:
        selection_result = selector.select(
            task_type=task_type,
            difficulty=difficulty,
            strategy="auto",
        )
    except Exception:
        return None

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


async def _call_model(model_name: str, prompt: str, config):
    """调用单个模型，返回 PlaygroundResult"""
    model_cfg = config.models.get(model_name)
    if not model_cfg:
        return PlaygroundResult(
            model=model_name,
            provider="",
            response="",
            latency_ms=0,
            prompt_tokens=0,
            completion_tokens=0,
            estimated_cost=None,
            error=f"模型未找到: {model_name}",
            routing_info=None,
        )

    litellm_params = config.get_litellm_params(model_name)
    messages = [{"role": "user", "content": prompt}]

    start_time = time.time()
    try:
        response = await asyncio.wait_for(
            litellm.acompletion(
                model=litellm_params["model"],
                messages=messages,
                api_key=litellm_params.get("api_key"),
                api_base=litellm_params.get("api_base"),
            ),
            timeout=30.0,
        )
        latency_ms = int((time.time() - start_time) * 1000)

        content = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0)
        completion_tokens = getattr(usage, "completion_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens

        # 提取 reasoning_tokens 和 cached_tokens
        reasoning_tokens = 0
        completion_details = getattr(usage, "completion_tokens_details", None)
        if completion_details:
            reasoning_tokens = getattr(completion_details, "reasoning_tokens", 0) or 0

        cached_tokens = 0
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        if prompt_details:
            cached_tokens = getattr(prompt_details, "cached_tokens", 0) or 0

        await TokenStats().record(
            model_name, prompt_tokens, completion_tokens, total_tokens,
            reasoning_tokens=reasoning_tokens, cached_tokens=cached_tokens
        )

        cost = _calculate_cost(model_name, prompt_tokens, completion_tokens, config)

        return PlaygroundResult(
            model=model_name,
            provider=model_cfg.provider,
            response=content,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=cost,
            error=None,
            routing_info=None,
        )
    except asyncio.TimeoutError:
        latency_ms = int((time.time() - start_time) * 1000)
        return PlaygroundResult(
            model=model_name,
            provider=model_cfg.provider,
            response="",
            latency_ms=latency_ms,
            prompt_tokens=0,
            completion_tokens=0,
            estimated_cost=None,
            error="请求超时",
            routing_info=None,
        )
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        status_code = getattr(e, "status_code", None)
        if status_code is None:
            msg = str(e)
            match = re.search(r"(\d{3})", msg)
            if match:
                status_code = match.group(1)

        if status_code:
            error_msg = f"{status_code} {str(e)}"
        else:
            error_msg = str(e)

        return PlaygroundResult(
            model=model_name,
            provider=model_cfg.provider,
            response="",
            latency_ms=latency_ms,
            prompt_tokens=0,
            completion_tokens=0,
            estimated_cost=None,
            error=error_msg,
            routing_info=None,
        )


async def _call_model_with_stagger(model_name: str, prompt: str, config, delay: float):
    """带延迟的模型调用"""
    if delay > 0:
        await asyncio.sleep(delay)
    return await _call_model(model_name, prompt, config)


@playground_router.post("/completions")
async def completions(request: PlaygroundRequest):
    """执行模型调用（single 或 compare 模式）"""
    config = _load_config()
    if not config:
        raise HTTPException(status_code=500, detail="配置加载失败")

    # 验证模型
    for model_name in request.models:
        if model_name not in config.models:
            raise HTTPException(status_code=400, detail=f"未知模型: {model_name}")

    # 获取路由信息
    routing_info = _get_routing_info(request.prompt, config)

    # compare 模式：并发调用，带 stagger
    if request.mode == "compare":
        tasks = []
        for i, model_name in enumerate(request.models):
            delay = i * 0.5
            tasks.append(_call_model_with_stagger(model_name, request.prompt, config, delay))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results = []
        for i, res in enumerate(results):
            model_name = request.models[i]
            if isinstance(res, Exception):
                model_cfg = config.models.get(model_name)
                final_results.append(PlaygroundResult(
                    model=model_name,
                    provider=model_cfg.provider if model_cfg else "",
                    response="",
                    latency_ms=0,
                    prompt_tokens=0,
                    completion_tokens=0,
                    estimated_cost=None,
                    error=str(res),
                    routing_info=routing_info,
                ))
            else:
                res.routing_info = routing_info
                final_results.append(res)
    else:
        # single 模式
        result = await _call_model(request.models[0], request.prompt, config)
        result.routing_info = routing_info
        final_results = [result]

    # 保存历史记录
    _save_history(request.mode, request.prompt, request.models, final_results)

    return {"results": final_results}


@playground_router.get("/history")
async def get_history():
    """获取历史记录（最多50条）"""
    if not HISTORY_FILE.exists():
        return {"history": []}
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return {"history": data[-MAX_HISTORY:]}
    except Exception:
        return {"history": []}


@playground_router.delete("/history/{record_id}")
async def delete_history(record_id: str):
    """删除单条历史记录"""
    if not HISTORY_FILE.exists():
        return {"success": True}
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        data = [r for r in data if r.get("id") != record_id]
        HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _save_history(mode: str, prompt: str, models: list[str], results: list[PlaygroundResult]):
    """保存历史记录，FIFO 最多50条"""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if HISTORY_FILE.exists():
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        else:
            data = []

        record = {
            "id": str(uuid.uuid4()),
            "mode": mode,
            "prompt": prompt,
            "models": models,
            "results": [r.model_dump() for r in results],
            "created_at": time.time(),
        }
        data.append(record)

        if len(data) > MAX_HISTORY:
            data = data[-MAX_HISTORY:]

        HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # 历史记录保存失败不应影响主流程
        pass
