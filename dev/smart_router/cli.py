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

DEFAULT_CONFIG = Path(__file__).parent.parent / "templates" / "smart-router.yaml"


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


def main():
    app()


if __name__ == "__main__":
    main()
