import shutil
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config.loader import load_config, validate_config
from .classifier import TaskClassifier
from .selector.strategies import ModelSelector
from .utils.markers import parse_markers
from .daemon import start_daemon, stop_daemon, restart_daemon, check_status, view_logs
from .coffee_qr import (
    get_qr_code_path, QR_CODE_PATH,
    open_image_terminal, open_image_system, copy_to_clipboard
)

app = typer.Typer(name="smart-router", help="智能模型路由网关")
console = Console()

DEFAULT_CONFIG = Path(__file__).parent.parent.parent / "config" / "smart-router.yaml"


@app.command()
def init(
    path: Optional[Path] = typer.Option(
        Path("smart-router.yaml"),
        "--output", "-o",
        help="输出配置文件路径"
    )
):
    """在当前目录生成默认配置文件"""
    if path.exists():
        overwrite = typer.confirm(f"{path} 已存在，是否覆盖？")
        if not overwrite:
            console.print("[yellow]已取消[/yellow]")
            raise typer.Exit()
    
    shutil.copy(DEFAULT_CONFIG, path)
    console.print(f"[green]✓[/green] 配置文件已生成: {path}")
    console.print("[dim]请编辑文件中的 API Key 环境变量名，然后运行 `smart-router serve`[/dim]")


@app.command()
def start(
    config: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="配置文件路径（默认向上查找 smart-router.yaml）"
    ),
    foreground: bool = typer.Option(
        False,
        "--foreground", "-f",
        help="前台运行（默认后台运行）"
    )
):
    """启动 Smart Router 服务（默认后台运行）"""
    if foreground:
        # 前台运行
        from .server import start_server
        start_server(config_path=config)
    else:
        # 后台运行
        start_daemon(config_path=config)


@app.command()
def stop():
    """停止 Smart Router 服务"""
    stop_daemon()


@app.command()
def uninstall(
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="直接卸载，不确认"
    )
):
    """卸载 Smart Router（停止服务并删除数据）"""
    if not force:
        confirm = typer.confirm("确定要卸载 Smart Router 吗？这将删除所有配置和日志")
        if not confirm:
            console.print("[yellow]已取消卸载[/yellow]")
            raise typer.Exit()
    
    # 停止服务
    stop_daemon()
    
    # 删除数据目录
    from .daemon import DEFAULT_PID_DIR
    if DEFAULT_PID_DIR.exists():
        import shutil
        shutil.rmtree(DEFAULT_PID_DIR)
        console.print(f"[green]✓[/green] 已删除数据目录: {DEFAULT_PID_DIR}")
    
    console.print("[green]✓[/green] 卸载完成")
    console.print("[dim]如需完全卸载，请手动运行: pip uninstall smart-router[/dim]")


@app.command()
def restart(
    config: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="配置文件路径"
    )
):
    """重启 Smart Router 服务"""
    restart_daemon(config_path=config)


@app.command()
def status():
    """查看 Smart Router 运行状态"""
    check_status()


@app.command()
def logs(
    lines: int = typer.Option(
        50,
        "--lines", "-n",
        help="显示最后 N 行日志"
    ),
    follow: bool = typer.Option(
        False,
        "--follow", "-f",
        help="持续跟踪日志（类似 tail -f）"
    )
):
    """查看服务日志"""
    view_logs(lines=lines, follow=follow)


@app.command()
def serve(
    config: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="配置文件路径（默认向上查找 smart-router.yaml）"
    )
):
    """启动代理服务（前台运行，保留用于兼容）"""
    from .server import start_server
    start_server(config_path=config)


@app.command()
def validate(
    config: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="配置文件路径"
    )
):
    """验证配置文件的完整性"""
    try:
        cfg = load_config(config)
    except Exception as e:
        console.print(f"[red]配置加载失败: {e}[/red]")
        raise typer.Exit(1)
    
    errors = validate_config(cfg)
    
    if errors:
        console.print("[red]✗ 配置验证失败[/red]")
        for err in errors:
            console.print(f"  [red]-[/red] {err}")
        raise typer.Exit(1)
    else:
        console.print("[green]✓ 配置验证通过[/green]")
        console.print(f"  模型数: {len(cfg.model_list)}")
        console.print(f"  阶段数: {len(cfg.smart_router.stage_routing)}")
        console.print(f"  规则数: {len(cfg.smart_router.classification_rules)}")


@app.command()
def dry_run(
    prompt: str = typer.Argument(..., help="测试路由的提示文本"),
    config: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="配置文件路径"
    ),
    strategy: str = typer.Option(
        "auto",
        "--strategy", "-s",
        help="路由策略 (auto/speed/cost/quality)"
    )
):
    """测试路由决策（不实际调用模型）"""
    cfg = load_config(config)
    
    messages = [{"role": "user", "content": prompt}]
    markers = parse_markers(messages)
    
    classifier = TaskClassifier(
        rules=[r.model_dump() for r in cfg.smart_router.classification_rules],
        embedding_config=cfg.smart_router.embedding_match.model_dump()
    )
    selector = ModelSelector(
        routing_rules={k: v.model_dump() for k, v in cfg.smart_router.stage_routing.items()},
        fallback_chain=cfg.smart_router.fallback_chain
    )
    
    if markers.stage:
        from .classifier.types import ClassificationResult
        result = ClassificationResult(
            task_type=markers.stage,
            estimated_difficulty=markers.difficulty or "medium",
            confidence=1.0,
            source="stage_marker"
        )
    else:
        result = classifier.classify(messages)
    
    available = [m.model_name for m in cfg.model_list]
    selected = selector.select(
        task_type=result.task_type,
        difficulty=result.estimated_difficulty,
        strategy=strategy,
        model_list=available
    )
    
    table = Table(title="Smart Router 路由决策")
    table.add_column("项目", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("输入文本", prompt[:60] + "..." if len(prompt) > 60 else prompt)
    table.add_row("识别标记", f"stage={markers.stage}, difficulty={markers.difficulty}")
    table.add_row("任务类型", result.task_type)
    table.add_row("预估难度", result.estimated_difficulty)
    table.add_row("置信度", f"{result.confidence:.2f}")
    table.add_row("分类来源", result.source)
    table.add_row("策略", strategy)
    table.add_row("选中模型", selected)
    
    console.print(table)


@app.command()
def doctor():
    """运行健康检查，诊断常见问题"""
    import sys
    import os
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    console.print(Panel.fit("🔍 Smart Router 健康检查", style="bold blue"))
    
    checks_passed = 0
    checks_failed = 0
    warnings = []
    
    # 检查 1: Python 版本
    with console.status("[bold green]检查 Python 版本..."):
        py_version = sys.version_info
        if py_version >= (3, 9):
            console.print(f"[green]✓[/green] Python 版本: {py_version.major}.{py_version.minor}.{py_version.micro}")
            checks_passed += 1
        else:
            console.print(f"[red]✗[/red] Python 版本: {py_version.major}.{py_version.minor}.{py_version.micro} (需要 3.9+)")
            checks_failed += 1
    
    # 检查 2: 核心模块导入
    with console.status("[bold green]检查核心模块..."):
        try:
            from .utils.markers import parse_markers, strip_markers
            from .classifier import TaskClassifier
            from .selector.strategies import ModelSelector
            from .config.schema import Config
            console.print("[green]✓[/green] 核心模块导入正常")
            checks_passed += 1
        except Exception as e:
            console.print(f"[red]✗[/red] 模块导入失败: {e}")
            checks_failed += 1
    
    # 检查 3: 功能测试
    with console.status("[bold green]测试核心功能..."):
        try:
            # 测试标记解析
            result = parse_markers([{'role': 'user', 'content': '[stage:code_review] 测试'}])
            assert result.stage == 'code_review'
            
            # 测试分类器
            classifier = TaskClassifier(rules=[], embedding_config={'enabled': False, 'custom_types': []})
            result = classifier.classify([{'role': 'user', 'content': '测试'}])
            assert result.task_type == 'chat'
            
            # 测试选择器
            selector = ModelSelector(routing_rules={'chat': {'easy': ['gpt-4o']}}, fallback_chain={})
            selected = selector.select('chat', 'easy', 'auto', ['gpt-4o'])
            assert selected == 'gpt-4o'
            
            console.print("[green]✓[/green] 核心功能测试通过")
            checks_passed += 1
        except Exception as e:
            console.print(f"[red]✗[/red] 功能测试失败: {e}")
            checks_failed += 1
    
    # 检查 4: 配置文件
    with console.status("[bold green]检查配置文件..."):
        config_files = ['smart-router.yaml', '../config/smart-router.yaml']
        found_config = None
        for config_file in config_files:
            if Path(config_file).exists():
                found_config = config_file
                break
        
        if found_config:
            console.print(f"[green]✓[/green] 配置文件存在: {found_config}")
            checks_passed += 1
            
            # 尝试加载配置
            try:
                cfg = load_config(Path(found_config))
                console.print(f"[green]✓[/green] 配置加载成功 ({len(cfg.model_list)} 个模型)")
                checks_passed += 1
            except Exception as e:
                console.print(f"[red]✗[/red] 配置加载失败: {e}")
                checks_failed += 1
        else:
            console.print("[yellow]⚠[/yellow] 未找到配置文件，运行 `smart-router init` 生成")
            warnings.append("未找到配置文件")
            checks_passed += 1  # 这不是致命错误
    
    # 检查 5: 环境变量
    with console.status("[bold green]检查环境变量..."):
        required_envs = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'DEEPSEEK_API_KEY', 
                        'DASHSCOPE_API_KEY', 'MOONSHOT_API_KEY']
        found_envs = [env for env in required_envs if os.environ.get(env)]
        
        if found_envs:
            console.print(f"[green]✓[/green] 找到 {len(found_envs)} 个 API Key 环境变量")
            checks_passed += 1
        else:
            console.print("[yellow]⚠[/yellow] 未找到 API Key 环境变量，配置后将无法调用模型")
            warnings.append("未配置 API Key 环境变量")
            checks_passed += 1  # 这不是致命错误
    
    # 检查 6: 服务状态
    with console.status("[bold green]检查服务状态..."):
        from .daemon import _get_pid, _is_process_running
        pid = _get_pid()
        if pid and _is_process_running(pid):
            console.print(f"[green]✓[/green] 服务运行中 (PID: {pid})")
            checks_passed += 1
        else:
            console.print("[dim]○ 服务未运行[/dim]")
            # 服务未运行不是错误
    
    # 总结
    console.print("")
    if checks_failed == 0:
        console.print(Panel(
            f"[green]✓ 所有检查通过 ({checks_passed} 项)[/green]" + 
            (f"\n[yellow]⚠ 警告: {', '.join(warnings)}[/yellow]" if warnings else ""),
            title="健康检查完成",
            border_style="green"
        ))
        sys.exit(0)
    else:
        console.print(Panel(
            f"[red]✗ {checks_failed} 项检查失败[/red]\n"
            f"[green]✓ {checks_passed} 项检查通过[/green]",
            title="健康检查完成",
            border_style="red"
        ))
        sys.exit(1)


@app.command()
def coffee(
    link: Optional[str] = typer.Option(
        None,
        "--link", "-l",
        help="自定义赞助链接（用于生成二维码）"
    ),
    ascii: bool = typer.Option(
        False,
        "--ascii", "-a",
        help="纯文字模式（不显示图片）"
    ),
    open: bool = typer.Option(
        False,
        "--open", "-o",
        help="使用系统默认程序打开图片"
    )
):
    """☕ 请作者喝一杯咖啡，支持项目持续发展"""
    from rich.panel import Panel
    from rich.align import Align
    from rich.text import Text
    from rich import box
    import os
    
    # 获取二维码路径
    qr_path = get_qr_code_path()
    
    # 如果指定了链接，生成新的二维码
    if link:
        from .coffee_qr import generate_qr_code
        qr_path = generate_qr_code(link)
    
    # 显示方式选择
    if ascii:
        # ASCII 模式：纯文字提示（无图片）
        content = Text()
        content.append("感谢您的使用！\n\n", style="bold cyan")
        content.append("Smart Router 是一个免费开源项目\n", style="dim")
        content.append("您的支持将帮助项目持续改进和维护\n\n", style="dim")
        
        # 显示文字提示，而不是假二维码
        content.append("\n")
        content.append("─" * 40 + "\n", style="dim")
        content.append("\n")
        content.append("  ☕ 喜欢这个项目？请支持作者！\n\n", style="bold yellow")
        content.append("  运行以下命令查看微信收款二维码:\n", style="dim")
        content.append("\n")
        content.append("    ", style="dim")
        content.append("smr coffee --open\n", style="bold cyan")
        content.append("\n")
        
    elif open:
        # 使用系统打开图片
        content = Text()
        content.append("感谢您的使用！\n\n", style="bold cyan")
        content.append("Smart Router 是一个免费开源项目\n", style="dim")
        content.append("您的支持将帮助项目持续改进和维护\n\n", style="dim")
        
        if qr_path and qr_path.exists():
            if open_image_system(qr_path):
                content.append(f"\n[green]✅ 已打开二维码图片[/green]\n")
                content.append(f"[dim]图片路径: {qr_path}[/dim]\n")
            else:
                content.append(f"\n[yellow]⚠️ 无法自动打开，请手动打开图片:[/yellow]\n")
                content.append(f"[cyan]{qr_path}[/cyan]\n")
        else:
            content.append("\n[red]❌ 未找到二维码图片[/red]\n")
            
    else:
        # 默认：先输出所有文字，最后显示图片
        if qr_path and qr_path.exists():
            # 构建文字内容（不包含图片）
            content = Text()
            content.append("感谢您的使用！\n\n", style="bold cyan")
            content.append("Smart Router 是一个免费开源项目\n", style="dim")
            content.append("您的支持将帮助项目持续改进和维护\n\n", style="dim")
            
            # 添加赞助方式说明（在图片之前）
            content.append("\n")
            content.append("─" * 40 + "\n", style="dim")
            content.append("💚 赞助方式:\n", style="bold green")
            content.append("   • 微信支付: 扫描下方二维码\n", style="dim")
            content.append("   • GitHub Sponsors: github.com/sponsors\n", style="dim")
            content.append("   • 分享给更多朋友使用\n", style="dim")
            
            # 创建面板并显示（只有文字）
            panel = Panel(
                Align.center(content),
                title="[bold yellow]☕ Buy Me a Coffee[/bold yellow]",
                subtitle="[dim]每一份支持都是前进的动力[/dim]",
                border_style="bright_yellow",
                box=box.ROUNDED,
                padding=(1, 4)
            )
            console.print(panel)
            
            # 面板输出后，再显示图片
            from .coffee_qr import display_image_terminal
            console.print("\n")
            console.print("请使用微信扫描下方二维码:", style="dim")
            console.print("")
            
            if not display_image_terminal(qr_path, width=150):
                # 终端不支持图片显示，显示提示
                console.print("")
                console.print("┌" + "─" * 38 + "┐", style="yellow")
                console.print("│" + " " * 38 + "│", style="yellow")
                console.print("│  📱 请运行以下命令查看二维码:" + " " * 7 + "│", style="bold yellow")
                console.print("│" + " " * 38 + "│", style="yellow")
                console.print("│     ", style="yellow", end="")
                console.print("smr coffee --open", style="bold cyan reverse", end="")
                console.print(" " * 16 + "│", style="yellow")
                console.print("│" + " " * 38 + "│", style="yellow")
                console.print("└" + "─" * 38 + "┘", style="yellow")
                console.print("")
                console.print("其他方式:", style="dim")
                console.print(f"  • 图片路径: {qr_path}", style="dim")
                
                # 尝试复制到剪贴板
                if copy_to_clipboard(str(qr_path)):
                    console.print("  • 路径已复制到剪贴板", style="dim")
                
                console.print("  • 终端工具: brew install chafa (可选)", style="dim")
            
            # 已经直接输出过了，不需要再创建面板
            return
            
        else:
            # 没有二维码图片，显示友好提示
            content = Text()
            content.append("感谢您的使用！\n\n", style="bold cyan")
            content.append("Smart Router 是一个免费开源项目\n", style="dim")
            content.append("您的支持将帮助项目持续改进和维护\n\n", style="dim")
            
            content.append("\n")
            content.append("─" * 40 + "\n", style="dim")
            content.append("\n")
            content.append("  ☕ 喜欢这个项目？请支持作者！\n\n", style="bold yellow")
            content.append("  运行以下命令查看微信收款二维码:\n", style="dim")
            content.append("\n")
            content.append("    ", style="dim")
            content.append("smr coffee --open\n", style="bold cyan")
            content.append("\n")
    
    # 添加赞助方式说明
    content.append("\n")
    content.append("─" * 40 + "\n", style="dim")
    content.append("💚 赞助方式:\n", style="bold green")
    content.append("   • 微信支付: 扫描上方二维码\n", style="dim")
    content.append("   • GitHub Sponsors: github.com/sponsors\n", style="dim")
    content.append("   • 分享给更多朋友使用\n", style="dim")
    
    # 创建面板
    panel = Panel(
        Align.center(content),
        title="[bold yellow]☕ Buy Me a Coffee[/bold yellow]",
        subtitle="[dim]每一份支持都是前进的动力[/dim]",
        border_style="bright_yellow",
        box=box.ROUNDED,
        padding=(1, 4)
    )
    
    console.print(panel)


def main():
    app()


if __name__ == "__main__":
    main()
