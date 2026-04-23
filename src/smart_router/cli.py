"""Smart Router CLI"""

import shutil
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich import box

from .config.loader import ConfigLoader, ConfigError, load_config
from .classifier.task_classifier import TaskTypeClassifier
from .classifier.difficulty_classifier import DifficultyClassifier
from .selector.v3_selector import V3ModelSelector
from .utils.markers import parse_markers
from .gateway.daemon import start_daemon, stop_daemon, restart_daemon, check_status, view_logs
from .misc.coffee_qr import (
    get_qr_code_path, QR_CODE_PATH,
    open_image_system, copy_to_clipboard
)

app = typer.Typer(name="smart-router", help="智能模型路由网关")
console = Console()

# 版本号
__version__ = "1.0.8"


@app.command()
def version(
    short: bool = typer.Option(False, "--short", "-s", help="仅显示版本号")
):
    """显示 Smart Router 版本信息"""
    if short:
        console.print(__version__)
    else:
        content = Text()
        content.append("Smart Router\n", style="bold cyan")
        content.append(f"版本: {__version__}\n", style="green")
        content.append("\n")
        content.append("智能模型路由网关\n", style="dim")
        content.append("统一 API 入口，自动路由到最优模型\n", style="dim")
        
        panel = Panel(
            content,
            title="[bold yellow]ℹ️ 版本信息[/bold yellow]",
            border_style="cyan",
            padding=(1, 4)
        )
        console.print(panel)


@app.command()
def init(
    output_dir: Path = typer.Option(
        Path.home() / ".smart-router",
        "--output", "-o",
        help="配置文件输出目录"
    ),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="强制覆盖已存在的配置文件"
    )
):
    """生成默认配置文件 (providers.yaml + models.yaml + routing.yaml)"""
    # 调用 download_config 逻辑，保持统一
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查文件是否已存在
    existing_files = []
    for filename in ["providers.yaml", "models.yaml", "routing.yaml"]:
        if (output_dir / filename).exists():
            existing_files.append(filename)
    
    if existing_files and not force:
        overwrite = typer.confirm(
            f"以下文件已存在: {', '.join(existing_files)}\n是否覆盖？"
        )
        if not overwrite:
            console.print("[yellow]已取消[/yellow]")
            raise typer.Exit()
    
    # 从包内模板复制配置（支持 pip install 和源码运行）
    try:
        from importlib.resources import files
        templates_dir = files("smart_router") / "templates"
        if templates_dir.exists() and (templates_dir / "models.yaml").exists():
            import shutil
            for filename in ["providers.yaml", "models.yaml", "routing.yaml"]:
                src = templates_dir / filename
                dst = output_dir / filename
                if src.exists():
                    shutil.copy2(str(src), dst)
            console.print(f"[green]✓[/green] 配置文件已生成: {output_dir.absolute()}")
        else:
            raise FileNotFoundError("模板目录不存在")
    except Exception:
        console.print("[yellow]⚠[/yellow] 未找到示例配置文件，使用默认配置...")
        _write_default_configs(output_dir)
    
    console.print("  - providers.yaml")
    console.print("  - models.yaml")
    console.print("  - routing.yaml")
    console.print("[dim]请编辑文件中的 API Key，然后运行 `smart-router start` 启动服务[/dim]")


def _write_default_configs(output_dir: Path):
    """写入默认配置文件（回退方案）"""
    # providers.yaml
    providers_content = '''# Providers Configuration
# API 服务商连接配置
# 取消注释你需要的 provider，并填写对应的 API Key

providers:
  # ==================== 国际服务商 ====================
  openai:
    api_base: https://api.openai.com/v1
    api_key: os.environ/OPENAI_API_KEY
    timeout: 30
    
  anthropic:
    api_base: https://api.anthropic.com
    api_key: os.environ/ANTHROPIC_API_KEY
    timeout: 30
    
  # ==================== 国产服务商 ====================
  # ------------------ Moonshot (月之暗面) ------------------
  moonshot-cn:
    api_base: https://api.moonshot.cn/v1
    api_key: os.environ/MOONSHOT_CN_API_KEY
    timeout: 30
    
  moonshot-ai:
    api_base: https://api.moonshot.ai/v1
    api_key: os.environ/MOONSHOT_AI_API_KEY
    timeout: 30
    
  # ------------------ 阿里通义千问 ------------------
  aliyun:
    api_base: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key: os.environ/DASHSCOPE_API_KEY
    timeout: 30
    
  zhipu:
    api_base: https://open.bigmodel.cn/api/paas/v4
    api_key: os.environ/ZHIPU_API_KEY
    timeout: 30
    
  minimax:
    api_base: https://api.minimax.chat/v1
    api_key: os.environ/MINIMAX_API_KEY
    timeout: 30
'''
    
    # models.yaml (默认基础模型)
    models_content = '''# Models Configuration
# 模型能力声明配置
# 请根据你的 API Key 配置启用或注释掉不需要的模型

models:
  # ------------------ OpenAI ------------------
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [coding, code_review, writing, chat]
    difficulty_support: [easy, medium, hard, expert]

  gpt-4o-mini:
    provider: openai
    litellm_model: openai/gpt-4o-mini
    capabilities:
      quality: 6
      cost: 9
      context: 128000
    supported_tasks: [coding, writing, chat]
    difficulty_support: [easy, medium]

  # ------------------ Anthropic ------------------
  claude-3-5-sonnet:
    provider: anthropic
    litellm_model: anthropic/claude-3-5-sonnet-20241022
    capabilities:
      quality: 10
      cost: 4
      context: 200000
    supported_tasks: [coding, code_review, writing, chat]
    difficulty_support: [easy, medium, hard, expert]

  # ------------------ 阿里通义千问 ------------------
  qwen-max:
    provider: aliyun
    litellm_model: openai/qwen-max
    capabilities:
      quality: 8
      cost: 6
      context: 32000
    supported_tasks: [coding, code_review, writing, chat]
    difficulty_support: [easy, medium, hard]

  qwen-turbo:
    provider: aliyun
    litellm_model: openai/qwen-turbo
    capabilities:
      quality: 6
      cost: 9
      context: 128000
    supported_tasks: [chat, writing]
    difficulty_support: [easy, medium]

  # ------------------ 智谱 GLM ------------------
  glm-4:
    provider: zhipu
    litellm_model: openai/glm-4
    capabilities:
      quality: 7
      cost: 6
      context: 128000
    supported_tasks: [coding, writing, chat]
    difficulty_support: [easy, medium, hard]

  glm-4-flash:
    provider: zhipu
    litellm_model: openai/glm-4-flash
    capabilities:
      quality: 5
      cost: 10
      context: 128000
    supported_tasks: [chat, writing]
    difficulty_support: [easy, medium]

  # ------------------ MiniMax ------------------
  minimax-text-01:
    provider: minimax
    litellm_model: openai/MiniMax-Text-01
    capabilities:
      quality: 7
      cost: 6
      context: 1000000
    supported_tasks: [coding, writing, chat]
    difficulty_support: [easy, medium, hard]

  # ------------------ 智能路由虚拟模型 ------------------
  auto:
    provider: aliyun
    litellm_model: openai/qwen-max
    capabilities:
      quality: 8
      cost: 6
      context: 32000
    supported_tasks: [coding, code_review, writing, chat]
    difficulty_support: [easy, medium, hard, expert]

  smart-router:
    provider: aliyun
    litellm_model: openai/qwen-max
    capabilities:
      quality: 8
      cost: 6
      context: 32000
    supported_tasks: [coding, code_review, writing, chat]
    difficulty_support: [easy, medium, hard, expert]
'''
    
    # routing.yaml
    routing_content = '''# Routing Configuration
# 任务路由策略配置

tasks:
  coding:
    name: "代码生成"
    description: "编写代码、实现功能"
    capability_weights:
      quality: 0.60
      cost: 0.40
    keywords: ["写代码", "实现", "function", "class", "算法", "debug", "重构"]
    examples:
      - "帮我写一个快速排序算法"
      - "实现一个单例模式"
      - "这段代码怎么优化"
      
  chat:
    name: "日常对话"
    description: "闲聊、简单问答"
    capability_weights:
      quality: 0.40
      cost: 0.60
    keywords: []
    examples: []

difficulties:
  easy:
    name: "简单"
    description: "基础问答"
    max_tokens: 2000
    
  medium:
    name: "中等"
    description: "多轮对话"
    max_tokens: 8000

strategies:
  auto:
    name: "智能自动"
    description: "根据任务类型和难度动态计算最佳模型"

fallback:
  mode: auto
  similarity_threshold: 2
  max_attempts: 3
'''
    
    # 写入文件
    (output_dir / "providers.yaml").write_text(providers_content)
    (output_dir / "models.yaml").write_text(models_content)
    (output_dir / "routing.yaml").write_text(routing_content)

@app.command()
def start(
    config: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="配置文件路径"
    ),
    foreground: bool = typer.Option(
        False,
        "--foreground", "-f",
        help="前台运行"
    )
):
    """启动 Smart Router 服务"""
    if foreground:
        from .gateway.server import start_server
        start_server(config_path=config)
    else:
        start_daemon(config_path=config)


@app.command()
def stop():
    """停止 Smart Router 服务"""
    stop_daemon()


@app.command()
def restart(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="配置文件路径")
):
    """重启 Smart Router 服务"""
    restart_daemon(config_path=config)


@app.command()
def status():
    """查看 Smart Router 运行状态"""
    check_status()


@app.command()
def logs(
    lines: int = typer.Option(50, "--lines", "-n", help="显示最后 N 行"),
    follow: bool = typer.Option(False, "--follow", "-f", help="持续跟踪")
):
    """查看服务日志"""
    view_logs(lines=lines, follow=follow)


@app.command()
def dry_run(
    prompt: str = typer.Argument(..., help="测试路由的提示文本"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="配置文件目录路径"),
    show_all: bool = typer.Option(False, "--all", "-a", help="显示所有候选模型"),
    strategy: str = typer.Option("auto", "--strategy", "-s", help="路由策略: auto(自动), quality(质量优先), cost(成本优先)")
):
    """测试路由决策（不实际调用模型）"""
    # V3 配置：config 是配置目录
    if config is None:
        config_dir = Path.home() / ".smart-router"
    else:
        config_path = Path(config)
        config_dir = config_path if config_path.is_dir() else config_path.parent
    
    loader = ConfigLoader(config_dir)
    cfg = loader.load()
    
    messages = [{"role": "user", "content": prompt}]
    markers = parse_markers(messages)
    
    # 1. 任务分类
    # 从 V3 routing.tasks 构建任务分类器配置
    task_types_config = {
        task_id: {
            "name": task_config.name,
            "description": task_config.description,
            "capability_weights": task_config.capability_weights
        }
        for task_id, task_config in cfg.routing.tasks.items()
    }
    task_classifier = TaskTypeClassifier(task_types_config)
    
    if markers.stage:
        task_result = type('obj', (object,), {
            'task_type': markers.stage,
            'confidence': 1.0,
            'source': 'stage_marker'
        })()
    else:
        task_result = task_classifier.classify(messages)
    
    # 2. 难度评估
    if markers.difficulty:
        difficulty_result = type('obj', (object,), {
            'difficulty': markers.difficulty,
            'confidence': 1.0,
            'source': 'stage_marker',
            'matched_rule': None
        })()
    else:
        # 从 V3 routing.difficulties 构建难度分类器配置
        difficulty_config = [
            {
                "pattern": ".*",  # 默认匹配所有
                "difficulty": diff_id,
                "description": diff_config.description,
                "max_tokens": diff_config.max_tokens
            }
            for diff_id, diff_config in cfg.routing.difficulties.items()
        ]
        difficulty_classifier = DifficultyClassifier(difficulty_config)
        difficulty_result = difficulty_classifier.classify(prompt, task_type=task_result.task_type)
    
    # 3. 模型选择（使用 V3 选择器）
    available_models = cfg.get_available_models()
    selector = V3ModelSelector(cfg, available_models=available_models)
    
    selection_result = selector.select(
        task_type=task_result.task_type,
        difficulty=difficulty_result.difficulty,
        strategy=strategy
    )
    
    # 显示结果
    table = Table(title=f"路由决策详情 [策略: {strategy}]")
    table.add_column("步骤", style="cyan")
    table.add_column("结果", style="green")
    table.add_column("详情", style="dim")
    
    table.add_row(
        "1. 任务分类",
        task_result.task_type,
        f"置信度: {task_result.confidence:.2f}"
    )
    table.add_row(
        "2. 难度评估",
        difficulty_result.difficulty,
        difficulty_result.matched_rule or "默认"
    )
    table.add_row(
        "3. 模型选择",
        selection_result.model_name,
        selection_result.reason
    )
    
    console.print(table)
    
    if show_all:
        candidates = selector.get_available_models(task_result.task_type, difficulty_result.difficulty)
        console.print(f"\n[dim]所有候选模型 ({len(candidates)} 个): {', '.join(candidates)}[/dim]")


@app.command()
def doctor(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="配置文件目录路径")
):
    """运行健康检查 - 支持 V3 三文件配置"""
    import os
    
    console.print(Panel.fit("🔍 Smart Router 健康检查", style="bold blue"))
    
    checks_passed = 0
    checks_failed = 0
    
    # 检查 1: Python 版本
    py_version = sys.version_info
    if py_version >= (3, 9):
        console.print(f"[green]✓[/green] Python 版本: {py_version.major}.{py_version.minor}.{py_version.micro}")
        checks_passed += 1
    else:
        console.print(f"[red]✗[/red] Python 版本: {py_version.major}.{py_version.minor} (需要 3.9+)")
        checks_failed += 1
    
    # 检查 2: V3 配置
    config_dir = Path(config) if config else Path.home() / ".smart-router"
    
    # 检查 V3 配置文件是否存在
    v3_files = ["providers.yaml", "models.yaml", "routing.yaml"]
    missing_files = [f for f in v3_files if not (config_dir / f).exists()]
    
    if missing_files:
        console.print(f"[red]✗[/red] V3 配置文件缺失: {', '.join(missing_files)}")
        console.print(f"[dim]  请运行 `smart-router init` 生成配置[/dim]")
        checks_failed += 2
    else:
        try:
            # 加载配置
            loader = ConfigLoader(config_dir)
            cfg = loader.load()
            console.print(f"[green]✓[/green] 配置加载成功 ({len(cfg.models)} 个模型)")
            checks_passed += 1
            
            # 验证配置
            errors = loader.validate()
            if errors:
                console.print(f"[red]✗[/red] 配置验证失败:")
                for err in errors:
                    console.print(f"  [red]-[/red] {err}")
                checks_failed += 1
            else:
                console.print("[green]✓[/green] 配置验证通过")
                checks_passed += 1
                
        except ConfigError as e:
            console.print(f"[red]✗[/red] 配置加载失败: {e}")
            checks_failed += 2
        except Exception as e:
            console.print(f"[red]✗[/red] 配置加载失败: {e}")
            checks_failed += 2
    
    # 检查 3: 服务状态
    from .gateway.daemon import _get_pid, _is_process_running
    pid = _get_pid()
    if pid and _is_process_running(pid):
        console.print(f"[green]✓[/green] 服务运行中 (PID: {pid})")
        checks_passed += 1
    else:
        console.print("[dim]○ 服务未运行[/dim]")
    
    # 总结
    console.print("")
    if checks_failed == 0:
        console.print(Panel(
            f"[green]✓ 所有检查通过 ({checks_passed} 项)[/green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[red]✗ {checks_failed} 项检查失败[/red]",
            border_style="red"
        ))


@app.command(name="list")
def list_models(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="配置文件目录路径")
):
    """列出已配置的 Provider 和可用模型"""
    config_dir = Path(config) if config else Path.home() / ".smart-router"
    
    # 检查配置文件是否存在
    v3_files = ["providers.yaml", "models.yaml", "routing.yaml"]
    missing_files = [f for f in v3_files if not (config_dir / f).exists()]
    
    if missing_files:
        console.print(f"[red]✗[/red] 配置文件缺失: {', '.join(missing_files)}")
        console.print(f"[dim]  请运行 `smart-router init` 生成配置[/dim]")
        raise typer.Exit(1)
    
    try:
        import os
        
        # 加载配置
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
        
        # 显示 Providers 表格
        console.print(Panel.fit("📡 已配置的 Providers", style="bold blue"))
        
        provider_table = Table(
            title="",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        provider_table.add_column("Provider", style="bold green", min_width=15)
        provider_table.add_column("API Base", style="dim", min_width=40)
        provider_table.add_column("Timeout", style="yellow", justify="right", width=10)
        provider_table.add_column("Auth", style="magenta", width=12)
        
        for name, provider in cfg.providers.items():
            # 检查 API Key 类型
            if provider.api_key.startswith("os.environ/"):
                env_var = provider.api_key.replace("os.environ/", "")
                if os.environ.get(env_var):
                    auth_status = "[green]✓ env[/green]"
                else:
                    auth_status = "[red]✗ missing[/red]"
            else:
                auth_status = "[green]✓ key[/green]"
            
            provider_table.add_row(
                name,
                provider.api_base,
                f"{provider.timeout}s",
                auth_status
            )
        
        console.print(provider_table)
        console.print("")
        
        # 预先检查每个 provider 是否有有效的 API Key
        def is_provider_available(provider_name: str) -> bool:
            """检查 provider 是否配置了有效的 API Key"""
            if provider_name not in cfg.providers:
                return False
            provider = cfg.providers[provider_name]
            if provider.api_key.startswith("os.environ/"):
                env_var = provider.api_key.replace("os.environ/", "")
                return os.environ.get(env_var) is not None
            return True  # 直接配置了 key
        
        # 显示 Models 表格
        console.print(Panel.fit("🤖 模型清单", style="bold blue"))
        
        model_table = Table(
            title="",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        model_table.add_column("模型名称", min_width=18)
        model_table.add_column("Provider", style="cyan", min_width=12)
        model_table.add_column("状态", justify="center", width=8)
        model_table.add_column("Quality", justify="center", width=8)
        model_table.add_column("Cost", justify="center", width=8)
        model_table.add_column("Context", justify="right", width=10)
        model_table.add_column("支持任务", style="dim", min_width=20)
        
        available_count = 0
        unavailable_count = 0
        
        for name, model in cfg.models.items():
            caps = model.capabilities
            provider_available = is_provider_available(model.provider)
            
            if provider_available:
                available_count += 1
                name_style = f"[bold green]{name}[/bold green]"
                status_text = "[green]✓[/green]"
            else:
                unavailable_count += 1
                name_style = f"[dim]{name}[/dim]"
                status_text = "[red]✗[/red]"
            
            # 使用表情符号表示评分
            quality_stars = "★" * (caps.quality // 2) + "☆" * (5 - caps.quality // 2)
            cost_stars = "★" * (caps.cost // 2) + "☆" * (5 - caps.cost // 2)  # cost 越高越便宜
            
            # 格式化 context
            context = caps.context
            if context >= 1000:
                context_str = f"{context // 1000}k"
            else:
                context_str = str(context)
            
            # 格式化任务列表（显示前3个）
            tasks = model.supported_tasks[:3]
            tasks_str = ", ".join(tasks)
            if len(model.supported_tasks) > 3:
                tasks_str += f" [dim]+{len(model.supported_tasks) - 3}[/dim]"
            
            model_table.add_row(
                name_style,
                model.provider,
                status_text,
                quality_stars,
                cost_stars,
                context_str,
                tasks_str
            )
        
        console.print(model_table)
        console.print("")
        
        # 显示统计信息
        total_providers = len(cfg.providers)
        total_models = len(cfg.models)
        
        # 统计 API Key 配置情况
        env_keys = sum(
            1 for p in cfg.providers.values()
            if p.api_key.startswith("os.environ/") and os.environ.get(p.api_key.replace("os.environ/", ""))
        )
        direct_keys = sum(
            1 for p in cfg.providers.values()
            if not p.api_key.startswith("os.environ/")
        )
        missing_keys = total_providers - env_keys - direct_keys
        
        stats_text = Text()
        stats_text.append(f"Providers: {total_providers} 个 | ", style="cyan")
        stats_text.append(f"模型: {available_count} 可用", style="green")
        if unavailable_count > 0:
            stats_text.append(f" / {unavailable_count} 不可用", style="red")
        stats_text.append(f" | ", style="dim")
        if missing_keys > 0:
            stats_text.append(f"API Key 缺失: {missing_keys} 个", style="red")
        else:
            stats_text.append("API Key 配置完整 ✓", style="green")
        
        console.print(Panel(stats_text, border_style="dim"))
        
        # 显示提示信息
        if unavailable_count > 0:
            console.print("[dim]提示: 灰色显示的模型因对应 Provider 未配置 API Key 而不可用[/dim]")
        
    except ConfigError as e:
        console.print(f"[red]✗[/red] 配置加载失败: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] 发生错误: {e}")
        raise typer.Exit(1)


@app.command()
def coffee(
    ascii: bool = typer.Option(False, "--ascii", "-a", help="纯文字模式"),
    open: bool = typer.Option(False, "--open", "-o", help="打开图片")
):
    """☕ 请作者喝一杯咖啡"""
    qr_path = get_qr_code_path()
    
    if ascii:
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
    elif open:
        content = Text()
        content.append("感谢您的使用！\n\n", style="bold cyan")
        content.append("Smart Router 是一个免费开源项目\n", style="dim")
        content.append("您的支持将帮助项目持续改进和维护\n\n", style="dim")
        
        if qr_path and qr_path.exists():
            if open_image_system(qr_path):
                content.append("\n[green]✅ 已打开二维码图片[/green]\n")
            else:
                content.append(f"\n[yellow]请手动打开: {qr_path}[/yellow]\n")
        else:
            content.append("\n[red]未找到二维码图片[/red]\n")
    else:
        if qr_path and qr_path.exists():
            content = Text()
            content.append("感谢您的使用！\n\n", style="bold cyan")
            content.append("Smart Router 是一个免费开源项目\n", style="dim")
            content.append("您的支持将帮助项目持续改进和维护\n\n", style="dim")
            content.append("\n")
            content.append("─" * 40 + "\n", style="dim")
            content.append("💚 赞助方式:\n", style="bold green")
            content.append("   • 微信支付: 扫描下方二维码\n", style="dim")
            content.append("   • GitHub Sponsors: github.com/sponsors\n", style="dim")
            content.append("\n")
            
            panel = Panel(
                Align.center(content),
                title="[bold yellow]☕ Buy Me a Coffee[/bold yellow]",
                border_style="bright_yellow",
                box=box.ROUNDED,
                padding=(1, 4)
            )
            console.print(panel)
            
            console.print("\n请使用微信扫描下方二维码:\n")
            
            from .misc.coffee_qr import display_image_terminal
            if not display_image_terminal(qr_path, width=150):
                console.print("┌" + "─" * 38 + "┐", style="yellow")
                console.print("│  📱 请运行: smr coffee --open" + " " * 5 + "│", style="bold yellow")
                console.print("└" + "─" * 38 + "┘", style="yellow")
            
            console.print(f"\n[dim]图片路径: {qr_path}[/dim]\n")
            return
        else:
            content = Text()
            content.append("感谢您的使用！\n\n", style="bold cyan")
            content.append("Smart Router 是一个免费开源项目\n", style="dim")
            content.append("\n")
            content.append("  ☕ 请支持作者: smr coffee --open\n", style="bold yellow")
    
    panel = Panel(
        Align.center(content),
        title="[bold yellow]☕ Buy Me a Coffee[/bold yellow]",
        border_style="bright_yellow",
        box=box.ROUNDED,
        padding=(1, 4)
    )
    console.print(panel)


def main():
    app()


if __name__ == "__main__":
    main()
