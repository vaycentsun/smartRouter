import asyncio
import os
import sys
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Request
from rich.console import Console
from starlette.middleware.base import BaseHTTPMiddleware

from ..config.loader import ConfigLoader
from ..config.schema import Config
from ..config.watcher import ConfigWatcher
from ..router.plugin import SmartRouter


console = Console()


def _is_retryable_status(status_code: int) -> bool:
    """判断 HTTP 状态码是否可重试
    
    策略：任何非 2xx 状态码都值得尝试 fallback 换模型。
    因为不同 provider 的模型配置可能不同，404/401/403 等错误
    通过换 provider 或换模型都可能解决。
    """
    return status_code < 200 or status_code >= 300


def _is_auth_error(status_code: int) -> bool:
    """判断是否为认证/授权错误
    
    401/403 错误通常表示当前 provider 的 API Key 问题，
    fallback 时应优先尝试其他 provider 的模型。
    """
    return status_code in (401, 403)


def _is_retryable_exception(exc: Exception) -> bool:
    """判断异常是否可重试
    
    可重试：网络超时、连接断开等
    不可重试：配置错误、认证错误等
    """
    import asyncio
    if isinstance(exc, asyncio.TimeoutError):
        return True
    exc_name = type(exc).__name__.lower()
    retryable_names = (
        "connectionerror", "connectionrefusederror", "connectionreseterror",
        "connectionabortederror", "timeouterror", "oserror", "ioerror",
    )
    return exc_name in retryable_names


class SmartRouterMiddleware(BaseHTTPMiddleware):
    """智能路由中间件 — 在请求到达 LiteLLM 前注入模型选择逻辑
    
    使用 BaseHTTPMiddleware 子类而非 @app.middleware 装饰器，
    确保可以通过 app.add_middleware() 在条件分支内注册，防止重复添加。
    """
    
    def __init__(self, app, router: SmartRouter):
        super().__init__(app)
        self.router = router
    
    async def dispatch(self, request: Request, call_next):
        routed = False  # 标记是否已由路由逻辑处理
        
        # 只处理 chat/completions 请求
        if request.url.path == "/v1/chat/completions" and request.method == "POST":
            try:
                # 读取请求体
                body = await request.body()
                if body:
                    data = json.loads(body)
                    original_model = data.get("model", "")
                    
                    # 检查是否有模型覆盖请求头
                    override_provider = request.headers.get("X-Smart-Router-Override-Provider")
                    override_model = request.headers.get("X-Smart-Router-Override-Model")
                    
                    if override_provider and override_model:
                        # 验证覆盖的模型是否有效
                        config = self.router.sr_config
                        model_name = override_model
                        
                        if model_name in config.models:
                            model_config = config.models[model_name]
                            if model_config.provider == override_provider and config.is_model_available(model_name):
                                # 有效覆盖：直接设置模型，跳过路由逻辑
                                data["model"] = model_name
                                
                                # 保存到 request.state 供后续使用
                                request.state.smart_router_selected = model_name
                                request.state.smart_router_override = True
                                request.state.smart_router_override_provider = override_provider
                                request.state.smart_router_override_model = model_name
                                request.state.smart_router_original = original_model
                                request.state.smart_router_task = "override"
                                
                                request_id = str(uuid.uuid4())[:8]
                                request.state.smart_router_request_id = request_id
                                request.state.smart_router_routing_info = {
                                    "request_id": request_id,
                                    "original_model": original_model,
                                    "selected_model": model_name,
                                    "task_type": "override",
                                    "difficulty": None,
                                    "strategy": "override",
                                    "fallback_chain": [],
                                }
                                
                                console.print(f"[cyan]模型覆盖: {original_model} -> {model_name} (provider: {override_provider})[/cyan]")
                                
                                # 重新构建请求体
                                modified_body = json.dumps(data).encode("utf-8")

                                # 直接修改原始 request 的缓存 body，确保下游能读取到修改后的内容
                                request._body = modified_body
                            else:
                                console.print(f"[yellow]模型覆盖无效: {override_provider}/{model_name} (不可用或 provider 不匹配)[/yellow]")
                        else:
                            console.print(f"[yellow]模型覆盖无效: 未知模型 {model_name}[/yellow]")
                    else:
                        # 检查全局模型覆盖（管理员通过 Dashboard 设置）
                        # 优先从文件读取，实现 Dashboard 与 Proxy 跨进程状态共享
                        from ..utils.model_override_store import load_override_state
                        global_override = load_override_state()
                        if not global_override.get('enabled'):
                            # 回退到内存状态（兼容旧逻辑）
                            global_override = getattr(request.app.state, 'global_model_override', None)
                        if global_override and global_override.get('enabled'):
                            config = self.router.sr_config
                            go_provider = global_override.get('provider')
                            go_model = global_override.get('model')
                            
                            if go_model in config.models:
                                model_config = config.models[go_model]
                                if model_config.provider == go_provider and config.is_model_available(go_model):
                                    # 全局覆盖生效：替换模型，但保留原始 model 供统计
                                    data["model"] = go_model
                                    
                                    request.state.smart_router_selected = go_model
                                    request.state.smart_router_original = original_model
                                    request.state.smart_router_task = "override"
                                    request.state.smart_router_override = True
                                    request.state.smart_router_override_provider = go_provider
                                    request.state.smart_router_override_model = go_model
                                    
                                    request_id = str(uuid.uuid4())[:8]
                                    request.state.smart_router_request_id = request_id
                                    request.state.smart_router_routing_info = {
                                        "request_id": request_id,
                                        "original_model": original_model,
                                        "selected_model": go_model,
                                        "task_type": "override",
                                        "difficulty": None,
                                        "strategy": "override",
                                        "fallback_chain": [],
                                    }
                                    
                                    console.print(f"[cyan]全局模型覆盖: {original_model} -> {go_model} (provider: {go_provider})[/cyan]")
                                    
                                    modified_body = json.dumps(data).encode("utf-8")

                                    # 直接修改原始 request 的缓存 body，确保下游能读取到修改后的内容
                                    request._body = modified_body
                                else:
                                    console.print(f"[yellow]全局模型覆盖无效: {go_provider}/{go_model} (不可用或 provider 不匹配)[/yellow]")
                            else:
                                console.print(f"[yellow]全局模型覆盖无效: 未知模型 {go_model}[/yellow]")
                        else:
                            # 没有覆盖请求头，走原有智能路由逻辑
                            should_route = (
                                original_model in ("auto", "smart-router", "default") or
                                original_model.startswith("stage:") or
                                original_model.startswith("strategy-")
                            )
                            
                            if should_route:
                                response = await self._route_with_retry(
                                    request, call_next, data, original_model
                                )
                                routed = True
            except Exception as e:
                console.print(f"[yellow]智能路由处理失败: {e}[/yellow]")
                import traceback
                console.print(traceback.format_exc())
        
        # 如果路由逻辑尚未产生响应，则调用下游
        if not routed:
            response = await call_next(request)

        # 记录错误率
        if hasattr(request.app.state, 'error_counter'):
            request.app.state.error_counter.record(not (200 <= response.status_code < 300))

        console.print(f"[dim]Middleware: path={request.url.path} method={request.method} selected={getattr(request.state, 'smart_router_selected', None)}[/dim]")
        
        # 添加响应头
        if hasattr(request.state, 'smart_router_selected'):
            response.headers["X-Smart-Router-Model"] = request.state.smart_router_selected
            response.headers["X-Smart-Router-Original"] = request.state.smart_router_original
            response.headers["X-Smart-Router-Task"] = request.state.smart_router_task
        
        if hasattr(request.state, 'smart_router_override'):
            response.headers["X-Smart-Router-Override-Active"] = "true"
            response.headers["X-Smart-Router-Override-Provider"] = request.state.smart_router_override_provider
            response.headers["X-Smart-Router-Override-Model"] = request.state.smart_router_override_model
        
        # Token 统计：拦截 chat/completions 响应
        if request.url.path == "/v1/chat/completions" and request.method == "POST":
            console.print(f"[cyan]✓ Attempting token stats for POST /v1/chat/completions[/cyan]")
            content_type = response.headers.get("content-type", "")
            console.print(f"[dim]Content-Type: {content_type}[/dim]")
            
            try:
                # 确定统计模型名（按优先级）
                model_name = getattr(request.state, 'smart_router_selected', None)
                if not model_name:
                    model_name = getattr(request.state, 'smart_router_override_model', None)
                if not model_name:
                    # 回退：从请求体解析原始 model 字段
                    try:
                        req_body = await request.body()
                        if req_body:
                            req_data = json.loads(req_body)
                            model_name = req_data.get("model", None)
                    except Exception as e:
                        console.print(f"[yellow]Failed to parse request body: {e}[/yellow]")
                
                console.print(f"[dim]Model name resolved: {model_name}[/dim]")
                
                if model_name:
                    # 消费响应 body
                    body_bytes = b""
                    if hasattr(response, "body_iterator"):
                        async for chunk in response.body_iterator:
                            body_bytes += chunk
                    else:
                        body_bytes = response.body
                    
                    console.print(f"[dim]Response body size: {len(body_bytes)} bytes[/dim]")
                    
                    # 解析 usage（支持普通 JSON 和 SSE 流式格式）
                    usage = {}
                    is_sse = "text/event-stream" in content_type
                    
                    if is_sse:
                        # 解析 SSE 格式，从 data: 行中提取包含 usage 的 JSON
                        try:
                            text = body_bytes.decode("utf-8", errors="replace")
                            for line in text.splitlines():
                                line = line.strip()
                                if line.startswith("data: "):
                                    data = line[6:]  # 去掉 "data: " 前缀
                                    if data == "[DONE]":
                                        continue
                                    try:
                                        chunk = json.loads(data)
                                        if chunk.get("usage"):
                                            usage = chunk["usage"]
                                    except json.JSONDecodeError:
                                        continue
                            console.print(f"[dim]SSE usage extracted: {usage}[/dim]")
                        except Exception as e:
                            console.print(f"[yellow]Error parsing SSE response: {e}[/yellow]")
                    else:
                        try:
                            resp_data = json.loads(body_bytes)
                            usage = resp_data.get("usage", {})
                            console.print(f"[dim]Usage field: {usage}[/dim]")
                        except json.JSONDecodeError as e:
                            console.print(f"[red]Failed to parse response JSON: {e}[/red]")
                            console.print(f"[dim]Body preview: {body_bytes[:200]}[/dim]")
                        except Exception as e:
                            console.print(f"[yellow]Error parsing response: {e}[/yellow]")
                    
                    if usage:
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                        total_tokens = usage.get("total_tokens", 0)
                        
                        # 提取 reasoning_tokens 和 cached_tokens（OpenAI 等格式）
                        reasoning_tokens = 0
                        completion_details = usage.get("completion_tokens_details", {})
                        if completion_details:
                            reasoning_tokens = completion_details.get("reasoning_tokens", 0)
                        
                        cached_tokens = 0
                        prompt_details = usage.get("prompt_tokens_details", {})
                        if prompt_details:
                            cached_tokens = prompt_details.get("cached_tokens", 0)
                        
                        console.print(f"[green]✓ Recording tokens: {model_name} - prompt:{prompt_tokens} completion:{completion_tokens} total:{total_tokens} reasoning:{reasoning_tokens} cached:{cached_tokens}[/green]")
                        
                        token_stats = request.app.state.token_stats
                        await token_stats.record(
                            model_name, prompt_tokens, completion_tokens, total_tokens,
                            reasoning_tokens=reasoning_tokens, cached_tokens=cached_tokens
                        )
                    else:
                        console.print("[yellow]No usage data in response[/yellow]")
                    
                    # 在解析 usage 后，增加 actual_model 解析
                    actual_model = None

                    if is_sse:
                        text = body_bytes.decode("utf-8", errors="replace")
                        for line in text.splitlines():
                            line = line.strip()
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    continue
                                try:
                                    chunk = json.loads(data)
                                    if chunk.get("model"):
                                        actual_model = chunk["model"]
                                        break
                                except json.JSONDecodeError:
                                    continue
                    else:
                        try:
                            resp_data = json.loads(body_bytes)
                            actual_model = resp_data.get("model")
                        except json.JSONDecodeError:
                            pass

                    # 组装并写入 RequestRoutingHistory
                    routing_info = getattr(request.state, 'smart_router_routing_info', None)
                    selected_model = getattr(request.state, 'smart_router_selected', None)

                    if routing_info and selected_model:
                        did_fallback = actual_model is not None and actual_model != selected_model
                        attempted_fallbacks = None
                        fallback_header = response.headers.get("x-litellm-attempted-fallbacks")
                        if fallback_header is not None:
                            try:
                                attempted_fallbacks = int(fallback_header)
                            except ValueError:
                                pass

                        from smart_router.utils.request_routing_history import RequestRoutingEntry
                        
                        retry_history = getattr(request.state, 'smart_router_retry_history', [])
                        error_info = None
                        final_error_type = None
                        if retry_history:
                            last_error = retry_history[-1]
                            if last_error.get("error"):
                                error_info = f"{last_error['model']}: {last_error['error']}"
                            elif last_error.get("status_code"):
                                error_info = f"{last_error['model']}: HTTP {last_error['status_code']}"
                            final_error_type = last_error.get("error_type")
                        
                        entry = RequestRoutingEntry(
                            request_id=routing_info["request_id"],
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            original_model=routing_info["original_model"],
                            selected_model=selected_model,
                            actual_model=actual_model,
                            task_type=routing_info.get("task_type"),
                            difficulty=routing_info.get("difficulty"),
                            strategy=routing_info.get("strategy"),
                            fallback_chain=routing_info.get("fallback_chain", []),
                            attempted_fallbacks=attempted_fallbacks,
                            did_fallback=did_fallback,
                            status_code=response.status_code,
                            prompt_tokens=usage.get("prompt_tokens", 0) if usage else 0,
                            completion_tokens=usage.get("completion_tokens", 0) if usage else 0,
                            total_tokens=usage.get("total_tokens", 0) if usage else 0,
                            error_info=error_info,
                            retry_history=retry_history,
                            reasoning_tokens=reasoning_tokens if usage else 0,
                            cached_tokens=cached_tokens if usage else 0,
                            final_error_type=final_error_type,
                        )

                        history = getattr(request.app.state, 'request_routing_history', None)
                        if history:
                            await history.record(entry)
                
                else:
                    console.print("[yellow]No model name resolved, skipping stats[/yellow]")
                
                # 重建 Response，确保下游正常消费
                if is_sse:
                    async def _stream_body():
                        yield body_bytes
                    from starlette.responses import StreamingResponse
                    response = StreamingResponse(
                        content=_stream_body(),
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )
                else:
                    from starlette.responses import Response
                    response = Response(
                        content=body_bytes,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )
            except Exception as e:
                import traceback
                console.print(f"[red]Token stats error: {e}[/red]")
                console.print(traceback.format_exc())
        
        return response
    
    async def _route_with_retry(
        self,
        request: Request,
        call_next,
        data: dict,
        original_model: str
    ):
        """统一路由重试逻辑（支持流式/非流式）
        
        核心策略：
        1. 任何非 2xx 错误都触发 fallback 换模型
        2. 401/403 认证错误优先跨 provider 重试
        3. 流式请求在首 token 返回前可重试
        4. 详细记录每次尝试的错误信息供后续分析
        """
        from starlette.responses import JSONResponse
        
        messages = data.get("messages", [])
        
        try:
            result = self.router.select_model(
                model_hint=original_model,
                messages=messages
            )
        except Exception as e:
            console.print(f"[yellow]智能路由失败: {e}[/yellow]")
            import traceback
            console.print(traceback.format_exc())
            
            # 对于保留模型名，尝试 fallback 到第一个可用模型
            if original_model in ("auto", "smart-router", "default"):
                try:
                    available = self.router.sr_config.get_available_models()
                    if available:
                        fallback_model = available[0]
                        data["model"] = fallback_model
                        request.state.smart_router_selected = fallback_model
                        request.state.smart_router_original = original_model
                        request.state.smart_router_task = "fallback"
                        
                        request_id = str(uuid.uuid4())[:8]
                        request.state.smart_router_request_id = request_id
                        request.state.smart_router_routing_info = {
                            "request_id": request_id,
                            "original_model": original_model,
                            "selected_model": fallback_model,
                            "task_type": "fallback",
                            "difficulty": None,
                            "strategy": "fallback",
                            "fallback_chain": [],
                            "retry_history": [],
                        }
                        
                        modified_body = json.dumps(data).encode("utf-8")
                        request._body = modified_body
                        
                        console.print(f"[yellow]智能路由异常降级: {original_model} -> {fallback_model}[/yellow]")
                        return await call_next(request)
                    else:
                        return JSONResponse(
                            status_code=400,
                            content={"error": {"message": "No model available for routing", "type": "invalid_request_error", "code": "400"}}
                        )
                except Exception as fallback_e:
                    return JSONResponse(
                        status_code=400,
                        content={"error": {"message": f"Routing failed: {fallback_e}", "type": "invalid_request_error", "code": "400"}}
                    )
            else:
                # stage: 前缀等，直接透传
                return await call_next(request)
        
        selected = result.model_name
        console.print(f"[green]智能路由: {original_model} -> {selected} ({result.task_type}, {result.difficulty})[/green]")
        
        # 保存基础路由信息
        request.state.smart_router_original = original_model
        request.state.smart_router_task = result.task_type
        request.state.smart_router_difficulty = result.difficulty
        request.state.smart_router_strategy = result.strategy
        
        request_id = str(uuid.uuid4())[:8]
        request.state.smart_router_request_id = request_id
        
        # 构建智能 fallback 候选列表（含 provider 信息）
        candidates = self._build_fallback_candidates(
            selected, result.ranked_models or [selected]
        )
        
        # fallback_chain 保持与 get_fallback_chain 一致（不包含 selected）
        fallback_chain = []
        if hasattr(self.router, 'get_fallback_chain') and selected:
            try:
                fallback_chain = self.router.get_fallback_chain(selected)
            except Exception:
                pass
        
        request.state.smart_router_routing_info = {
            "request_id": request_id,
            "original_model": original_model,
            "selected_model": selected,
            "task_type": result.task_type,
            "difficulty": result.difficulty,
            "strategy": result.strategy,
            "fallback_chain": fallback_chain,
        }
        
        # 判断是否为流式请求
        is_streaming = data.get("stream", False)
        max_attempts = self.router.sr_config.routing.fallback.max_attempts
        retry_history = []
        attempt = 0
        
        while attempt < len(candidates) and attempt < max_attempts:
            candidate = candidates[attempt]
            model_name = candidate["model"]
            provider = candidate["provider"]
            
            data["model"] = model_name
            modified_body = json.dumps(data).encode("utf-8")
            request._body = modified_body
            
            try:
                response = await call_next(request)
            except Exception as e:
                if _is_retryable_exception(e):
                    error_type = type(e).__name__
                    retry_history.append({
                        "model": model_name,
                        "provider": provider,
                        "status_code": 0,
                        "error_type": error_type,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    console.print(f"[yellow]模型 {model_name} (provider: {provider}) 调用异常 [{error_type}]: {e}[/yellow]")
                    if attempt < len(candidates) - 1 and attempt < max_attempts - 1:
                        console.print(f"[dim]等待 10 秒后重试下一个模型...[/dim]")
                        await asyncio.sleep(10)
                    attempt += 1
                    continue
                raise
            
            if _is_retryable_status(response.status_code):
                # 提取错误类型（从响应体或状态码推断）
                error_type = self._infer_error_type(response.status_code)
                retry_history.append({
                    "model": model_name,
                    "provider": provider,
                    "status_code": response.status_code,
                    "error_type": error_type,
                    "error": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                console.print(f"[yellow]模型 {model_name} (provider: {provider}) 返回 {response.status_code} ({error_type})，准备重试[/yellow]")
                
                # 401/403 时过滤掉同 provider 的剩余候选
                if _is_auth_error(response.status_code):
                    remaining = candidates[attempt + 1:]
                    filtered = [c for c in remaining if c["provider"] != provider]
                    if len(filtered) < len(remaining):
                        skipped = [c["model"] for c in remaining if c["provider"] == provider]
                        console.print(f"[dim]认证错误，跳过同 provider 候选: {skipped}[/dim]")
                        candidates = candidates[:attempt + 1] + filtered
                
                if attempt < len(candidates) - 1 and attempt < max_attempts - 1:
                    console.print(f"[dim]等待 10 秒后重试下一个模型...[/dim]")
                    await asyncio.sleep(10)
                attempt += 1
                continue
            
            # 成功
            request.state.smart_router_selected = model_name
            request.state.smart_router_retry_count = attempt
            request.state.smart_router_retry_history = retry_history
            console.print(f"[green]模型 {model_name} (provider: {provider}) 调用成功（尝试 {attempt + 1}/{max_attempts}）[/green]")
            return response
        
        # 所有候选耗尽
        console.print(f"[red]所有模型均失败，已尝试: {[r['model'] for r in retry_history]}[/red]")
        request.state.smart_router_retry_history = retry_history
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": "All models failed",
                    "type": "service_unavailable",
                    "code": "503",
                    "attempted_models": [r["model"] for r in retry_history],
                    "retry_history": retry_history,
                }
            }
        )
    
    def _build_fallback_candidates(self, selected: str, ranked_models: list) -> list[dict]:
        """构建带 provider 信息的 fallback 候选列表
        
        排序策略：
        1. 首选模型（selected）
        2. 策略排序的模型
        3. fallback 链中的模型（同 provider）
        4. 跨 provider 的可用模型兜底
        """
        config = self.router.sr_config
        candidates = []
        seen = set()
        
        # 0. 首选模型
        if selected and selected in config.models:
            model_config = config.models[selected]
            if config.is_model_available(selected):
                candidates.append({
                    "model": selected,
                    "provider": model_config.provider,
                    "source": "selected",
                })
                seen.add(selected)
        
        # 1. 策略排序的模型
        for model_name in ranked_models:
            if model_name in seen:
                continue
            if model_name not in config.models:
                continue
            model_config = config.models[model_name]
            if not config.is_model_available(model_name):
                continue
            candidates.append({
                "model": model_name,
                "provider": model_config.provider,
                "source": "ranked",
            })
            seen.add(model_name)
        
        # 2. fallback 链中的模型（同 provider）
        if hasattr(self.router, 'get_fallback_chain') and selected:
            try:
                fallback_chain = self.router.get_fallback_chain(selected)
                for model_name in fallback_chain:
                    if model_name in seen:
                        continue
                    if model_name not in config.models:
                        continue
                    model_config = config.models[model_name]
                    if not config.is_model_available(model_name):
                        continue
                    candidates.append({
                        "model": model_name,
                        "provider": model_config.provider,
                        "source": "fallback_chain",
                    })
                    seen.add(model_name)
            except Exception:
                pass
        
        # 3. 跨 provider 的可用模型兜底
        for model_name in config.get_available_models():
            if model_name in seen:
                continue
            model_config = config.models[model_name]
            candidates.append({
                "model": model_name,
                "provider": model_config.provider,
                "source": "cross_provider",
            })
            seen.add(model_name)
        
        return candidates
    
    @staticmethod
    def _infer_error_type(status_code: int) -> str:
        """根据 HTTP 状态码推断错误类型"""
        mapping = {
            400: "BadRequest",
            401: "AuthenticationError",
            403: "PermissionError",
            404: "NotFoundError",
            408: "TimeoutError",
            429: "RateLimitError",
            500: "InternalServerError",
            502: "BadGateway",
            503: "ServiceUnavailable",
            504: "GatewayTimeout",
        }
        return mapping.get(status_code, f"HTTPError_{status_code}")


def start_server(config_path: Optional[Path] = None):
    """启动 Smart Router 代理服务"""
    # config_path 是配置目录，不是单个文件
    if config_path is None:
        config_dir = Path.home() / ".smart-router"
    else:
        config_path = Path(config_path)
        if config_path.is_dir():
            config_dir = config_path
        else:
            config_dir = config_path.parent
    
    # 加载配置
    try:
        loader = ConfigLoader(config_dir)
        config = loader.load()
        console.print(f"[green]✓[/green] 配置已加载 ({len(config.models)} 个模型)")
    except Exception as e:
        console.print(f"[red]配置加载失败: {e}[/red]")
        sys.exit(1)
    
    # 验证配置
    errors = loader.validate()
    if errors:
        console.print("[red]配置验证失败:[/red]")
        for err in errors:
            console.print(f"  - {err}")
        sys.exit(1)
    
    # 从环境变量获取 master_key（可选，未设置时不启用认证）
    master_key = os.environ.get("SMART_ROUTER_MASTER_KEY")
    if master_key:
        os.environ["LITELLM_MASTER_KEY"] = master_key
    else:
        console.print("[yellow]警告: 未设置 SMART_ROUTER_MASTER_KEY，服务将无认证运行[/yellow]")
    
    console.print("[cyan]正在初始化智能路由...[/cyan]")
    router = SmartRouter(config=config)
    
    try:
        from litellm.proxy.proxy_server import ProxyConfig, initialize
        
        proxy_config = ProxyConfig()
        
        # 获取可用模型（API Key 已配置的模型）
        available_models = config.get_available_models()
        
        if not available_models:
            console.print("[red]错误: 没有可用的模型，请检查 API Key 配置[/red]")
            sys.exit(1)
        
        console.print(f"[dim]可用模型: {len(available_models)} / {len(config.models)}[/dim]")
        
        # 将配置转换为 LiteLLM 格式（只包含可用模型）
        model_list = []
        for model_name in available_models:
            litellm_params = config.get_litellm_params(model_name)
            model_list.append({
                "model_name": model_name,
                "litellm_params": litellm_params
            })
        
        # 禁用 LiteLLM 内置 fallback — Smart Router 已在中间件层实现策略排序重试
        # 保留注释以备未来需要恢复流式兜底
        # fallbacks = []
        # for model_name in available_models:
        #     chain = config.get_fallback_chain(model_name)
        #     if chain:
        #         fallbacks.append({model_name: chain})
        
        litellm_config = {
            "model_list": model_list,
            "router_settings": {
                "routing_strategy": "simple-shuffle",
            },
        }
        if master_key:
            litellm_config["general_settings"] = {"master_key": master_key}
        # 不传入 fallbacks，由 SmartRouterMiddleware 自行处理重试
        
        # 将配置写入临时文件
        import json
        import tempfile
        config_fd, config_path_temp = tempfile.mkstemp(suffix='.json')
        with os.fdopen(config_fd, 'w') as f:
            json.dump(litellm_config, f)
        
        # 初始化 LiteLLM Proxy 配置
        import asyncio
        asyncio.run(initialize(config=config_path_temp))
        
        # 安全删除临时配置文件（包含敏感信息）
        try:
            os.unlink(config_path_temp)
        except OSError:
            pass
        
        # 从环境变量获取 host/port
        host = os.environ.get("SMART_ROUTER_HOST", "127.0.0.1")
        port = int(os.environ.get("SMART_ROUTER_PORT", "4000"))
        
        console.print(f"[green]✓[/green] 配置加载完成，共 {len(config.models)} 个模型")
        console.print(f"[green]✓[/green] 启动服务于 http://{host}:{port}")
        
        import uvicorn
        from litellm.proxy.proxy_server import app
        
        app.state.smart_router = router
        
        # 初始化全局模型覆盖状态（优先从文件加载，实现 Dashboard 与 Proxy 跨进程共享）
        from ..utils.model_override_store import load_override_state
        app.state.global_model_override = load_override_state()
        
        # 初始化 Token 统计
        from ..utils.token_stats import TokenStats
        app.state.token_stats = TokenStats()

        # 初始化请求路由历史（使用文件持久化，支持 Dashboard 跨进程读取）
        from ..utils.request_routing_history import RequestRoutingHistory, DEFAULT_HISTORY_FILE
        app.state.request_routing_history = RequestRoutingHistory(
            max_size=100, persist_file=DEFAULT_HISTORY_FILE
        )

        # 初始化错误计数器
        from .error_counter import ErrorCounter
        app.state.error_counter = ErrorCounter()

        # 初始化告警系统
        from ..alerts.config import AlertConfig
        from ..alerts.checker import AlertChecker
        from ..alerts.notifier import AlertNotifier
        alerts_config = AlertConfig(config_dir / "alerts.yaml")
        app.state.alert_checker = AlertChecker(alerts_config, app.state.token_stats, app.state.error_counter)
        app.state.alert_notifier = AlertNotifier()
        app.state.alerts_config = alerts_config

        # 注册后台告警检查协程（通过 startup 事件）
        import asyncio
        from fastapi import BackgroundTasks

        @app.on_event("startup")
        async def _start_alert_background_task():
            alerts_history_path = config_dir / "alerts_history.json"
            async def _alert_background_task():
                """每 60 秒检查一次告警规则"""
                while True:
                    try:
                        await asyncio.sleep(60)
                        triggers = await app.state.alert_checker.check_all()
                        for trigger in triggers:
                            rule = alerts_config.get_rule(trigger.rule_id)
                            if not rule:
                                continue
                            for channel in rule.channels:
                                try:
                                    await app.state.alert_notifier.send(rule, trigger, channel)
                                except Exception as e:
                                    console.print(f"[yellow]Alert notification failed: {e}[/yellow]")

                            # 记录触发历史
                            try:
                                history = []
                                if alerts_history_path.exists():
                                    history = json.loads(alerts_history_path.read_text(encoding="utf-8"))
                                history.append({
                                    "rule_id": trigger.rule_id,
                                    "rule_name": trigger.rule_name,
                                    "severity": trigger.severity,
                                    "metric": trigger.metric,
                                    "current_value": trigger.current_value,
                                    "threshold": trigger.threshold,
                                    "timestamp": trigger.timestamp,
                                    "message": trigger.message,
                                })
                                # 最多保留 1000 条
                                if len(history) > 1000:
                                    history = history[-1000:]
                                alerts_history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
                                try:
                                    alerts_history_path.chmod(0o600)
                                except OSError:
                                    pass
                            except Exception as e:
                                console.print(f"[yellow]Failed to save alert history: {e}[/yellow]")
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        console.print(f"[yellow]Alert background task error: {e}[/yellow]")

            app.state._alert_task = asyncio.create_task(_alert_background_task())
        
        # 在应用启动时只添加一次中间件
        if not getattr(app.state, '_smart_router_middleware_added', False):
            app.add_middleware(SmartRouterMiddleware, router=router)
            app.state._smart_router_middleware_added = True
        
        # 注册 Dashboard API：获取可用的模型覆盖选项
        @app.get("/api/model-overrides")
        async def get_model_overrides():
            config = app.state.smart_router.sr_config
            overrides: dict[str, list[str]] = {}
            for name, model in config.models.items():
                if config.is_model_available(name):
                    if model.provider not in overrides:
                        overrides[model.provider] = []
                    overrides[model.provider].append(name)
            return {"overrides": overrides}
        
        # 注册 model-override API（供 Proxy 直接查询/设置，解决 Dashboard 与 Proxy 跨进程状态不同步）
        from ..utils.model_override_store import load_override_state, save_override_state, clear_override_state
        
        @app.get("/api/model-override")
        async def _get_model_override():
            state = load_override_state()
            return state
        
        @app.post("/api/model-override")
        async def _set_model_override(body: dict):
            provider = body.get("provider")
            model = body.get("model")
            if not provider or not model:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="provider 和 model 必填")
            config = app.state.smart_router.sr_config
            if model not in config.models:
                raise HTTPException(status_code=400, detail=f"未知模型: {model}")
            model_cfg = config.models[model]
            if model_cfg.provider != provider:
                raise HTTPException(status_code=400, detail=f"Provider 不匹配")
            if not config.is_model_available(model):
                raise HTTPException(status_code=400, detail=f"模型不可用: {model}")
            save_override_state(provider, model, True)
            app.state.global_model_override = {"provider": provider, "model": model, "enabled": True}
            return {"provider": provider, "model": model, "enabled": True}
        
        @app.delete("/api/model-override")
        async def _delete_model_override():
            clear_override_state()
            app.state.global_model_override = {"provider": None, "model": None, "enabled": False}
            return {"provider": None, "model": None, "enabled": False}
        
        # 注册错误统计 API（供 Dashboard 展示模型失败率）
        @app.get("/api/analytics/error-stats")
        async def _get_error_stats(days: int = 7):
            """获取模型错误统计
            
            返回每个模型的失败次数、成功率、常见错误类型分布。
            数据来源于 RequestRoutingHistory 中的 retry_history。
            """
            history = getattr(request.app.state, 'request_routing_history', None)
            if not history:
                return {
                    "models": [],
                    "error_types": [],
                    "provider_errors": [],
                    "total_requests": 0,
                    "total_failures": 0,
                }
            
            records = history.get_recent(limit=100)
            
            # 按模型聚合统计
            model_stats = {}
            error_type_counts = {}
            provider_error_counts = {}
            total_requests = len(records)
            total_failures = 0
            
            for record in records:
                retry_history = record.get("retry_history", [])
                
                # 统计最终是否成功（有 retry_history 但最终 status_code 不是 503 表示成功 fallback）
                is_failed = record.get("status_code", 200) >= 500 or record.get("error_info")
                if is_failed:
                    total_failures += 1
                
                # 统计每次重试的错误
                for retry in retry_history:
                    model_name = retry.get("model", "unknown")
                    provider = retry.get("provider", "unknown")
                    error_type = retry.get("error_type", "Unknown")
                    
                    # 模型统计
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
                    
                    # 全局错误类型统计
                    error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
                    
                    # Provider 错误统计
                    provider_key = f"{provider}:{error_type}"
                    provider_error_counts[provider_key] = provider_error_counts.get(provider_key, 0) + 1
            
            # 计算成功率
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
            
            # 按失败次数降序排列
            model_list.sort(key=lambda x: x["failures"], reverse=True)
            
            # 错误类型排行
            error_types_list = [
                {"error_type": k, "count": v}
                for k, v in sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True)
            ]
            
            # Provider 错误分布
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
        
        # 启动配置热重载监听
        watcher = ConfigWatcher(
            config_dir=config_dir,
            on_reload=router.reload_config
        )
        watcher.start()
        console.print("[dim]配置热重载已启用[/dim]")
        
        try:
            uvicorn.run(
                app,
                host=host,
                port=port,
            )
        finally:
            watcher.stop()
        
    except ImportError as e:
        console.print(f"[red]启动失败: {e}[/red]")
        console.print("[yellow]提示: 请确保已安装 litellm[proxy] 依赖[/yellow]")
        sys.exit(1)
