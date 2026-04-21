import os
import sys
import json
from pathlib import Path
from typing import Optional

from fastapi import Request
from rich.console import Console

from .config.loader import ConfigLoader
from .config.schema import Config
from .plugin import SmartRouter
from .utils.markers import parse_markers
from .utils.token_counter import estimate_messages_tokens

console = Console()


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
    
    # 从环境变量获取 master_key
    master_key = os.environ.get("SMART_ROUTER_MASTER_KEY", "sk-smart-router-local")
    os.environ["LITELLM_MASTER_KEY"] = master_key
    
    console.print("[cyan]正在初始化智能路由...[/cyan]")
    router = SmartRouter(config=config)
    
    try:
        from litellm.proxy.proxy_server import ProxyConfig, initialize
        
        proxy_config = ProxyConfig()
        
        # 将配置转换为 LiteLLM 格式
        model_list = []
        for model_name in config.models.keys():
            litellm_params = config.get_litellm_params(model_name)
            model_list.append({
                "model_name": model_name,
                "litellm_params": litellm_params
            })
        
        litellm_config = {
            "model_list": model_list,
            "router_settings": {
                "routing_strategy": "simple-shuffle",
            },
            "general_settings": {
                "master_key": master_key,
            }
        }
        
        # 将配置写入临时文件
        import json
        import tempfile
        config_fd, config_path_temp = tempfile.mkstemp(suffix='.json')
        with os.fdopen(config_fd, 'w') as f:
            json.dump(litellm_config, f)
        
        # 初始化 LiteLLM Proxy 配置
        import asyncio
        asyncio.run(initialize(config=config_path_temp))
        
        # 从环境变量获取 host/port
        host = os.environ.get("SMART_ROUTER_HOST", "127.0.0.1")
        port = int(os.environ.get("SMART_ROUTER_PORT", "4000"))
        
        console.print(f"[green]✓[/green] 配置加载完成，共 {len(config.models)} 个模型")
        console.print(f"[green]✓[/green] 启动服务于 http://{host}:{port}")
        
        import uvicorn
        from litellm.proxy.proxy_server import app
        from starlette.middleware.base import BaseHTTPMiddleware
        
        app.state.smart_router = router
        
        # 在应用启动时只添加一次中间件
        if not hasattr(app.state, '_smart_router_middleware_added'):
            app.state._smart_router_middleware_added = True
            
            # 添加智能路由中间件（在请求处理前）
            @app.middleware("http")
            async def smart_router_middleware(request: Request, call_next):
                # 只处理 chat/completions 请求
                if request.url.path == "/v1/chat/completions" and request.method == "POST":
                    try:
                        # 读取请求体
                        body = await request.body()
                        if body:
                            data = json.loads(body)
                            original_model = data.get("model", "")
                            
                            # 检查是否需要智能路由
                            should_route = (
                                original_model in ("auto", "smart-router", "default") or
                                original_model.startswith("stage:") or
                                original_model.startswith("strategy-")
                            )
                            
                            if should_route and hasattr(app.state, 'smart_router'):
                                messages = data.get("messages", [])
                                
                                # 解析阶段标记
                                markers = parse_markers(messages)
                                
                                # 确定任务类型和策略
                                strategy = "auto"  # 默认策略
                                
                                if original_model.startswith("strategy-"):
                                    # strategy-quality 或 strategy-cost
                                    strategy = original_model.replace("strategy-", "")
                                    if markers.stage:
                                        task_type = markers.stage
                                        difficulty = markers.difficulty or "medium"
                                    else:
                                        classification = app.state.smart_router.classifier.classify(messages)
                                        task_type = classification.task_type
                                        difficulty = classification.estimated_difficulty
                                elif original_model.startswith("stage:"):
                                    task_type = original_model.replace("stage:", "")
                                    difficulty = markers.difficulty or "medium"
                                elif markers.stage:
                                    task_type = markers.stage
                                    difficulty = markers.difficulty or "medium"
                                else:
                                    # 使用分类器
                                    classification = app.state.smart_router.classifier.classify(messages)
                                    task_type = classification.task_type
                                    difficulty = classification.estimated_difficulty
                                
                                # 估算所需上下文窗口
                                estimated_input = estimate_messages_tokens(messages)
                                required_context = estimated_input + 4000 if estimated_input > 0 else 0
                                
                                console.print(f"[cyan]智能路由: {original_model} -> 任务:{task_type}, 难度:{difficulty}, 策略:{strategy}, 需上下文:{required_context}[/cyan]")
                                
                                # 选择模型
                                selected_result = app.state.smart_router.selector.select(
                                    task_type=task_type,
                                    difficulty=difficulty,
                                    strategy=strategy,
                                    required_context=required_context
                                )
                                selected = selected_result.model_name if hasattr(selected_result, 'model_name') else str(selected_result)
                                
                                console.print(f"[green]智能路由: 选择模型 {selected}[/green]")
                                
                                # 修改请求体
                                data["model"] = selected
                                
                                # 保存到 request.state 供后续使用
                                request.state.smart_router_selected = selected
                                request.state.smart_router_original = original_model
                                request.state.smart_router_task = task_type
                                
                                # 重新构建请求体
                                modified_body = json.dumps(data).encode("utf-8")
                                
                                # 创建新的请求，使用修改后的 body
                                async def receive():
                                    return {"type": "http.request", "body": modified_body, "more_body": False}
                                
                                request = Request(request.scope, receive, request._send)
                    except Exception as e:
                        console.print(f"[yellow]智能路由处理失败: {e}[/yellow]")
                        import traceback
                        console.print(traceback.format_exc())
                
                response = await call_next(request)
                
                # 添加响应头
                if hasattr(request.state, 'smart_router_selected'):
                    response.headers["X-Smart-Router-Model"] = request.state.smart_router_selected
                    response.headers["X-Smart-Router-Original"] = request.state.smart_router_original
                    response.headers["X-Smart-Router-Task"] = request.state.smart_router_task
                
                return response
        
        uvicorn.run(
            app,
            host=host,
            port=port,
        )
        
    except ImportError as e:
        console.print(f"[red]启动失败: {e}[/red]")
        console.print("[yellow]提示: 请确保已安装 litellm[proxy] 依赖[/yellow]")
        sys.exit(1)
