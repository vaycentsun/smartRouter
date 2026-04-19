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


def main():
    app()


if __name__ == "__main__":
    main()
