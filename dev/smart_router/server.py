import os
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

from .config.loader import load_config, validate_config
from .config.schema import Config
from .plugin import SmartRouter

console = Console()


def start_server(config_path: Optional[Path] = None):
    """启动 Smart Router 代理服务"""
    config = load_config(config_path)
    
    errors = validate_config(config)
    if errors:
        console.print("[red]配置验证失败:[/red]")
        for err in errors:
            console.print(f"  - {err}")
        sys.exit(1)
    
    os.environ["LITELLM_MASTER_KEY"] = config.server.master_key
    
    console.print("[cyan]正在初始化智能路由...[/cyan]")
    router = SmartRouter(config=config)
    
    try:
        from litellm.proxy.proxy_server import ProxyConfig, initialize
        
        proxy_config = ProxyConfig()
        
        litellm_config = {
            "model_list": [m.model_dump() for m in config.model_list],
            "router_settings": {
                "routing_strategy": "simple-shuffle",
            },
            "general_settings": {
                "master_key": config.server.master_key,
            }
        }
        
        console.print(f"[green]✓[/green] 配置加载完成，共 {len(config.model_list)} 个模型")
        console.print(f"[green]✓[/green] 启动服务于 http://{config.server.host}:{config.server.port}")
        
        import uvicorn
        from litellm.proxy.proxy_server import app
        
        app.state.smart_router = router
        
        uvicorn.run(
            app,
            host=config.server.host,
            port=config.server.port,
        )
        
    except ImportError as e:
        console.print(f"[red]启动失败: {e}[/red]")
        console.print("[yellow]提示: 请确保已安装 litellm[proxy] 依赖[/yellow]")
        sys.exit(1)
