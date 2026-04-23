"""Smart Router 网关层

负责服务的生命周期管理：前台服务启动、后台守护进程、进程状态监控。
"""

from .server import start_server
from .daemon import start_daemon, stop_daemon, restart_daemon, check_status, view_logs

__all__ = [
    "start_server",
    "start_daemon",
    "stop_daemon",
    "restart_daemon",
    "check_status",
    "view_logs",
]
