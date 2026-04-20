import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import Request
from rich.console import Console

from .config.loader import ConfigLoader
from .config.schema import Config
from .plugin import SmartRouter

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
        
        # 添加中间件设置响应头
        class SmartRouterHeaderMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                response = await call_next(request)
                # 添加实际使用的模型到响应头
                if hasattr(app.state, 'smart_router') and app.state.smart_router.last_selected_model:
                    response.headers["X-Smart-Router-Model-Used"] = app.state.smart_router.last_selected_model
                return response
        
        # 确保中间件只添加一次
        if not any(isinstance(m, SmartRouterHeaderMiddleware) for m in app.user_middleware):
            app.add_middleware(SmartRouterHeaderMiddleware)
        
        uvicorn.run(
            app,
            host=host,
            port=port,
        )
        
    except ImportError as e:
        console.print(f"[red]启动失败: {e}[/red]")
        console.print("[yellow]提示: 请确保已安装 litellm[proxy] 依赖[/yellow]")
        sys.exit(1)
