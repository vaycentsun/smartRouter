"""
Smart Router 守护进程管理
支持后台启动、停止、重启和状态检查
"""
import os
import signal
import sys
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

# PID 文件默认位置
DEFAULT_PID_DIR = Path.home() / ".smart-router"
DEFAULT_PID_FILE = DEFAULT_PID_DIR / "smart-router.pid"


def _ensure_pid_dir():
    """确保 PID 目录存在"""
    DEFAULT_PID_DIR.mkdir(parents=True, exist_ok=True)


def _get_pid() -> Optional[int]:
    """获取当前运行的进程 ID"""
    if DEFAULT_PID_FILE.exists():
        try:
            return int(DEFAULT_PID_FILE.read_text().strip())
        except (ValueError, IOError):
            return None
    return None


def _is_process_running(pid: int) -> bool:
    """检查进程是否正在运行"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _write_pid(pid: int):
    """写入 PID 文件"""
    _ensure_pid_dir()
    DEFAULT_PID_FILE.write_text(str(pid))


def _remove_pid():
    """删除 PID 文件"""
    if DEFAULT_PID_FILE.exists():
        DEFAULT_PID_FILE.unlink()


def start_daemon(config_path: Optional[Path] = None, log_file: Optional[Path] = None):
    """
    在后台启动 Smart Router 服务
    
    Args:
        config_path: 配置文件路径
        log_file: 日志文件路径（默认 ~/.smart-router/smart-router.log）
    """
    # 检查是否已在运行
    existing_pid = _get_pid()
    if existing_pid and _is_process_running(existing_pid):
        console.print(f"[yellow]Smart Router 已在运行 (PID: {existing_pid})[/yellow]")
        console.print(f"[dim]使用 `smart-router stop` 停止服务[/dim]")
        return
    
    # 清理旧的 PID 文件
    _remove_pid()
    
    # 设置日志文件
    if log_file is None:
        _ensure_pid_dir()
        log_file = DEFAULT_PID_DIR / "smart-router.log"
    
    # 构建启动命令
    cmd = [sys.executable, "-m", "smart_router.server_main"]
    if config_path:
        cmd.extend(["--config", str(config_path)])
    
    # 启动后台进程
    try:
        with open(log_file, "w") as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # 创建新会话，脱离终端
            )
        
        # 写入 PID 文件
        _write_pid(process.pid)
        
        console.print(f"[green]✓[/green] Smart Router 已启动")
        console.print(f"  PID: {process.pid}")
        console.print(f"  日志: {log_file}")
        console.print(f"  服务: http://127.0.0.1:4000")
        console.print(f"\n[dim]使用 `smart-router status` 查看状态[/dim]")
        console.print(f"[dim]使用 `smart-router stop` 停止服务[/dim]")
        
    except Exception as e:
        console.print(f"[red]启动失败: {e}[/red]")
        sys.exit(1)


def stop_daemon():
    """停止 Smart Router 服务"""
    pid = _get_pid()
    
    if not pid:
        console.print("[yellow]Smart Router 未运行[/yellow]")
        return
    
    if not _is_process_running(pid):
        console.print("[yellow]Smart Router 进程已不存在[/yellow]")
        _remove_pid()
        return
    
    # 尝试优雅终止
    try:
        console.print(f"[cyan]正在停止 Smart Router (PID: {pid})...[/cyan]")
        os.kill(pid, signal.SIGTERM)
        
        # 等待进程结束
        import time
        for _ in range(10):  # 最多等待 5 秒
            time.sleep(0.5)
            if not _is_process_running(pid):
                break
        
        # 如果还在运行，强制终止
        if _is_process_running(pid):
            os.kill(pid, signal.SIGKILL)
            console.print(f"[yellow]已强制终止进程[/yellow]")
        
        _remove_pid()
        console.print("[green]✓[/green] Smart Router 已停止")
        
    except Exception as e:
        console.print(f"[red]停止失败: {e}[/red]")
        sys.exit(1)


def restart_daemon(config_path: Optional[Path] = None):
    """重启 Smart Router 服务"""
    console.print("[cyan]正在重启 Smart Router...[/cyan]")
    stop_daemon()
    start_daemon(config_path)


def check_status():
    """检查 Smart Router 运行状态"""
    pid = _get_pid()
    
    if not pid:
        console.print("[yellow]●[/yellow] Smart Router 未运行")
        return False
    
    if _is_process_running(pid):
        # 获取日志文件路径
        log_file = DEFAULT_PID_DIR / "smart-router.log"
        
        console.print("[green]●[/green] Smart Router 运行中")
        console.print(f"  PID: {pid}")
        console.print(f"  服务: http://127.0.0.1:4000")
        console.print(f"  日志: {log_file}")
        
        # 显示最近日志
        if log_file.exists():
            try:
                lines = log_file.read_text().splitlines()
                if lines:
                    console.print(f"\n[dim]最近日志:[/dim]")
                    for line in lines[-3:]:
                        console.print(f"  {line}")
            except IOError:
                pass
        
        return True
    else:
        console.print("[red]●[/red] Smart Router 进程已不存在（可能异常退出）")
        _remove_pid()
        return False


def view_logs(lines: int = 50, follow: bool = False):
    """
    查看服务日志
    
    Args:
        lines: 显示最后 N 行
        follow: 是否持续跟踪（类似 tail -f）
    """
    log_file = DEFAULT_PID_DIR / "smart-router.log"
    
    if not log_file.exists():
        console.print("[yellow]日志文件不存在[/yellow]")
        return
    
    if follow:
        # 持续跟踪模式
        try:
            import time
            with open(log_file, "r") as f:
                # 跳到文件末尾
                f.seek(0, 2)
                
                console.print(f"[dim]正在跟踪日志 (按 Ctrl+C 退出)...[/dim]\n")
                while True:
                    line = f.readline()
                    if line:
                        console.print(line.rstrip())
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            console.print("\n[dim]已停止跟踪[/dim]")
    else:
        # 显示最后 N 行
        try:
            with open(log_file, "r") as f:
                all_lines = f.readlines()
                
            console.print(f"[dim]显示最后 {min(lines, len(all_lines))} 行日志:[/dim]\n")
            
            for line in all_lines[-lines:]:
                console.print(line.rstrip())
                
        except IOError as e:
            console.print(f"[red]读取日志失败: {e}[/red]")
