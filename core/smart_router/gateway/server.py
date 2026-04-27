import os
import sys
import json
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


class SmartRouterMiddleware(BaseHTTPMiddleware):
    """智能路由中间件 — 在请求到达 LiteLLM 前注入模型选择逻辑
    
    使用 BaseHTTPMiddleware 子类而非 @app.middleware 装饰器，
    确保可以通过 app.add_middleware() 在条件分支内注册，防止重复添加。
    """
    
    def __init__(self, app, router: SmartRouter):
        super().__init__(app)
        self.router = router
    
    async def dispatch(self, request: Request, call_next):
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
                    
                    if should_route:
                        messages = data.get("messages", [])
                        
                        try:
                            result = self.router.select_model(
                                model_hint=original_model,
                                messages=messages
                            )
                            selected = result.model_name
                            
                            console.print(f"[green]智能路由: {original_model} -> {selected} ({result.task_type}, {result.difficulty})[/green]")
                            
                            # 修改请求体
                            data["model"] = selected
                            
                            # 保存到 request.state 供后续使用
                            request.state.smart_router_selected = selected
                            request.state.smart_router_original = original_model
                            request.state.smart_router_task = result.task_type
                            
                            # 重新构建请求体
                            modified_body = json.dumps(data).encode("utf-8")
                            
                            # 创建新的请求，使用修改后的 body
                            async def receive():
                                return {"type": "http.request", "body": modified_body, "more_body": False}
                            
                            request = Request(request.scope, receive, request._send)
                        except Exception as e:
                            console.print(f"[yellow]智能路由失败，使用原始模型: {e}[/yellow]")
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
        
        # 构建 fallback 链（只包含可用模型的 fallback）
        fallbacks = []
        for model_name in available_models:
            chain = config.get_fallback_chain(model_name)
            if chain:
                fallbacks.append({model_name: chain})
        
        litellm_config = {
            "model_list": model_list,
            "router_settings": {
                "routing_strategy": "simple-shuffle",
            },
        }
        if master_key:
            litellm_config["general_settings"] = {"master_key": master_key}
        if fallbacks:
            litellm_config["router_settings"]["fallbacks"] = fallbacks
        
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
        
        # 在应用启动时只添加一次中间件
        if not getattr(app.state, '_smart_router_middleware_added', False):
            app.add_middleware(SmartRouterMiddleware, router=router)
            app.state._smart_router_middleware_added = True
        
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
