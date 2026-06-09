"""Smart Router 网关层

负责服务的生命周期管理：前台服务启动、后台守护进程、进程状态监控。
"""

from .daemon import check_status, restart_daemon, start_daemon, stop_daemon, view_logs
from .server import start_server

__all__ = [
    "check_status",
    "restart_daemon",
    "start_daemon",
    "start_server",
    "stop_daemon",
    "view_logs",
]
