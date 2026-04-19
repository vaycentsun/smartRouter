"""Smart Router CLI - v2 Only"""

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

from .config.loader import load_config, validate_config
from .classifier.task_classifier import TaskTypeClassifier
from .classifier.difficulty_classifier import DifficultyClassifier
from .selector.model_selector import ModelSelector
from .utils.markers import parse_markers
from .daemon import start_daemon, stop_daemon, restart_daemon, check_status, view_logs
from .coffee_qr import (
    get_qr_code_path, QR_CODE_PATH,
    open_image_system, copy_to_clipboard
)

app = typer.Typer(name="smart-router", help="智能模型路由网关")
console = Console()

DEFAULT_CONFIG = Path(__file__).parent.parent.parent / "config" / "smart-router.yaml"

# 版本号
__version__ = "0.1.0"


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
    )
):
    """生成默认配置文件 (providers.yaml + models.yaml + routing.yaml)"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查文件是否已存在
    existing_files = []
    for filename in ["providers.yaml", "models.yaml", "routing.yaml"]:
        if (output_dir / filename).exists():
            existing_files.append(filename)
    
    if existing_files:
        overwrite = typer.confirm(
            f"以下文件已存在: {', '.join(existing_files)}\n是否覆盖？"
        )
        if not overwrite:
            console.print("[yellow]已取消[/yellow]")
            raise typer.Exit()
    
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
  moonshot:
    api_base: https://api.moonshot.cn/v1
    api_key: os.environ/MOONSHOT_API_KEY
    timeout: 30
    
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
    
  # ------------------ 其他可选服务商 ------------------
  # deepseek:
  #   api_base: https://api.deepseek.com
  #   api_key: os.environ/DEEPSEEK_API_KEY
  #   timeout: 30
  #
  # baichuan:
  #   api_base: https://api.baichuan-ai.com/v1
  #   api_key: os.environ/BAICHUAN_API_KEY
  #   timeout: 30
'''
    
    # models.yaml
    models_content = '''# Models Configuration
# 模型能力声明配置
# 根据你实际拥有的 API Key，取消注释对应的模型

models:
  # ==================== OpenAI ====================
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      speed: 8
      cost: 3
      context: 128000
    supported_tasks: [coding, code_review, writing, creative, reasoning, analysis, explanation, translation, chat, brainstorming]
    difficulty_support: [easy, medium, hard, expert]
    
  gpt-4o-mini:
    provider: openai
    litellm_model: openai/gpt-4o-mini
    capabilities:
      quality: 6
      speed: 9
      cost: 9
      context: 128000
    supported_tasks: [writing, explanation, translation, chat, brainstorming]
    difficulty_support: [easy, medium]
    
  # ==================== Anthropic ====================
  claude-3-5-sonnet:
    provider: anthropic
    litellm_model: anthropic/claude-3-5-sonnet-20241022
    capabilities:
      quality: 9
      speed: 7
      cost: 4
      context: 200000
    supported_tasks: [coding, code_review, writing, creative, reasoning, analysis, explanation, translation, chat, brainstorming]
    difficulty_support: [easy, medium, hard, expert]
    
  claude-3-opus:
    provider: anthropic
    litellm_model: anthropic/claude-3-opus-20240229
    capabilities:
      quality: 10
      speed: 5
      cost: 2
      context: 200000
    supported_tasks: [code_review, writing, creative, reasoning, analysis]
    difficulty_support: [hard, expert]
    
  # ==================== Moonshot (月之暗面) ====================
  kimi-k2:
    provider: moonshot
    litellm_model: openai/moonshot-v1-8k
    capabilities:
      quality: 7
      speed: 8
      cost: 7
      context: 8000
    supported_tasks: [coding, writing, explanation, chat, brainstorming]
    difficulty_support: [easy, medium]
    
  kimi-k2-32k:
    provider: moonshot
    litellm_model: openai/moonshot-v1-32k
    capabilities:
      quality: 7
      speed: 8
      cost: 6
      context: 32000
    supported_tasks: [coding, code_review, writing, analysis, explanation, chat, brainstorming]
    difficulty_support: [easy, medium, hard]
    
  # ==================== 阿里通义千问 ====================
  qwen-max:
    provider: aliyun
    litellm_model: openai/qwen-max
    capabilities:
      quality: 8
      speed: 7
      cost: 6
      context: 32000
    supported_tasks: [coding, code_review, writing, creative, reasoning, analysis, explanation, translation, chat, brainstorming]
    difficulty_support: [easy, medium, hard]
    
  qwen-turbo:
    provider: aliyun
    litellm_model: openai/qwen-turbo
    capabilities:
      quality: 6
      speed: 9
      cost: 9
      context: 8000
    supported_tasks: [writing, explanation, chat, brainstorming]
    difficulty_support: [easy, medium]
    
  # ==================== 智谱 GLM ====================
  glm-4-plus:
    provider: zhipu
    litellm_model: openai/glm-4-plus
    capabilities:
      quality: 8
      speed: 7
      cost: 5
      context: 128000
    supported_tasks: [coding, code_review, writing, creative, reasoning, analysis, explanation, chat, brainstorming]
    difficulty_support: [easy, medium, hard]
    
  glm-4-flash:
    provider: zhipu
    litellm_model: openai/glm-4-flash
    capabilities:
      quality: 6
      speed: 9
      cost: 9
      context: 128000
    supported_tasks: [writing, explanation, chat, brainstorming]
    difficulty_support: [easy, medium]
    
  # ==================== MiniMax ====================
  minimax-text-01:
    provider: minimax
    litellm_model: openai/MiniMax-Text-01
    capabilities:
      quality: 7
      speed: 8
      cost: 7
      context: 8000
    supported_tasks: [coding, writing, explanation, chat, brainstorming]
    difficulty_support: [easy, medium]
    
  # ------------------ 其他可选模型 ------------------
  # deepseek-chat:
  #   provider: deepseek
  #   litellm_model: openai/deepseek-chat
  #   capabilities:
  #     quality: 8
  #     speed: 6
  #     cost: 8
  #     context: 64000
  #   supported_tasks: [coding, code_review, writing, reasoning, analysis, explanation, chat]
  #   difficulty_support: [easy, medium, hard]
  #
  # deepseek-reasoner:
  #   provider: deepseek
  #   litellm_model: openai/deepseek-reasoner
  #   capabilities:
  #     quality: 9
  #     speed: 4
  #     cost: 7
  #     context: 64000
  #   supported_tasks: [reasoning, analysis, code_review]
  #   difficulty_support: [medium, hard, expert]
'''
    
    # routing.yaml
    routing_content = '''# Routing Configuration
# 任务路由策略配置 - 适配多场景 AI 任务

tasks:
  # ==================== 编程开发类 ====================
  coding:
    name: "代码生成"
    description: "编写代码、实现功能、算法设计、Debug调试、代码重构"
    capability_weights:
      quality: 0.55    # 代码质量重要但不需要顶级
      speed: 0.35      # 编程交互需要快速响应
      cost: 0.10
      
  code_review:
    name: "代码审查"
    description: "代码质量审查、bug发现、架构评估、性能优化建议、安全审计"
    capability_weights:
      quality: 0.70    # 审查质量至关重要
      speed: 0.20
      cost: 0.10
      
  # ==================== 内容创作类 ====================
  writing:
    name: "内容写作"
    description: "文章撰写、邮件起草、报告编写、技术文档、商业文案"
    capability_weights:
      quality: 0.60    # 内容质量优先
      speed: 0.25
      cost: 0.15
      
  creative:
    name: "创意写作"
    description: "故事创作、诗歌、广告创意、营销文案、剧本"
    capability_weights:
      quality: 0.65    # 创意需要高质量
      speed: 0.20
      cost: 0.15
      
  # ==================== 分析推理类 ====================
  reasoning:
    name: "逻辑推理"
    description: "数学问题、逻辑谜题、证明推导、算法分析、复杂问题求解"
    capability_weights:
      quality: 0.75    # 推理任务质量最关键
      speed: 0.10
      cost: 0.15
      
  analysis:
    name: "数据分析"
    description: "数据解读、趋势分析、商业分析、技术评估、竞争分析"
    capability_weights:
      quality: 0.60
      speed: 0.20
      cost: 0.20
      
  # ==================== 学习辅助类 ====================
  explanation:
    name: "知识讲解"
    description: "概念解释、教程编写、答疑解惑、知识梳理、学习辅导"
    capability_weights:
      quality: 0.50
      speed: 0.35      # 讲解需要较快响应
      cost: 0.15
      
  translation:
    name: "翻译"
    description: "文本翻译、本地化、多语言转换、术语校对"
    capability_weights:
      quality: 0.60    # 翻译准确性重要
      speed: 0.25
      cost: 0.15
      
  # ==================== 通用交互类 ====================
  chat:
    name: "日常对话"
    description: "闲聊、简单问答、日常交流、情感陪伴"
    capability_weights:
      quality: 0.30    # 对话质量要求不高
      speed: 0.50      # 对话最看重速度
      cost: 0.20
      
  brainstorming:
    name: "头脑风暴"
    description: "想法生成、方案讨论、创意发散、问题解决"
    capability_weights:
      quality: 0.40
      speed: 0.40      # 需要快速产生想法
      cost: 0.20

# ==================== 难度等级定义 (4级) ====================
difficulties:
  easy:
    name: "简单"
    description: "基础问答、简单解释、短文本生成、单轮对话"
    max_tokens: 2000
    examples: "解释概念、写简短邮件、简单代码片段、日常问候"
    
  medium:
    name: "中等"
    description: "多轮对话、中等长度内容、标准编程任务、常规分析"
    max_tokens: 8000
    examples: "博客文章、功能模块实现、代码审查、数据报告"
    
  hard:
    name: "困难"
    description: "长文创作、复杂推理、架构设计、深度分析"
    max_tokens: 16000
    examples: "系统架构设计、复杂算法、深度技术文章、商业策略"
    
  expert:
    name: "专家"
    description: "研究级问题、深度分析、创新设计、复杂证明"
    max_tokens: 32000
    examples: "研究论文、复杂数学证明、创新性解决方案、博士级问题"

# ==================== 路由策略 ====================
strategies:
  auto:
    name: "智能自动"
    description: "根据任务类型和难度动态计算最佳模型"
    
  quality:
    name: "质量优先"
    description: "选择 capability.quality 最高的模型"
    
  speed:
    name: "速度优先"
    description: "选择 capability.speed 最高的模型"
    
  cost:
    name: "成本优先"
    description: "选择 capability.cost 最高的模型（最便宜）"
    
  balanced:
    name: "平衡模式"
    description: "quality和speed权重相等(各0.4)"

# ==================== Fallback 配置 ====================
fallback:
  mode: auto
  similarity_threshold: 2    # quality差异在2以内的模型可作为fallback
  max_attempts: 3           # 最多尝试3次fallback
'''
    
    # 写入文件
    (output_dir / "providers.yaml").write_text(providers_content)
    (output_dir / "models.yaml").write_text(models_content)
    (output_dir / "routing.yaml").write_text(routing_content)
    
    console.print(f"[green]✓[/green] 配置文件已生成到: {output_dir.absolute()}")
    console.print("  - providers.yaml")
    console.print("  - models.yaml")
    console.print("  - routing.yaml")
    console.print("[dim]请编辑文件中的 API Key，然后运行 `smart-router start` 启动服务[/dim]")

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
        from .server import start_server
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
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="配置文件路径"),
    show_all: bool = typer.Option(False, "--all", "-a", help="显示所有候选模型")
):
    """测试路由决策（不实际调用模型）"""
    cfg = load_config(config)
    
    messages = [{"role": "user", "content": prompt}]
    markers = parse_markers(messages)
    
    # 1. 任务分类
    task_classifier = TaskTypeClassifier({
        k: v.model_dump() if hasattr(v, 'model_dump') else v
        for k, v in cfg.smart_router.task_types.items()
    })
    
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
        difficulty_classifier = DifficultyClassifier([
            r.model_dump() if hasattr(r, 'model_dump') else r
            for r in cfg.smart_router.difficulty_rules
        ])
        difficulty_result = difficulty_classifier.classify(prompt, task_type=task_result.task_type)
    
    # 3. 模型选择
    selector = ModelSelector(
        cfg.smart_router.model_pool.model_dump() if hasattr(cfg.smart_router.model_pool, 'model_dump')
        else cfg.smart_router.model_pool
    )
    
    selection_result = selector.select(
        task_type=task_result.task_type,
        difficulty=difficulty_result.difficulty
    )
    
    # 显示结果
    table = Table(title="路由决策详情")
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
        candidates = selector.get_candidates(task_result.task_type, difficulty_result.difficulty)
        console.print(f"\n[dim]所有候选模型 ({len(candidates)} 个): {', '.join(candidates)}[/dim]")


@app.command()
def doctor(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="配置文件路径")
):
    """运行健康检查"""
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
    
    # 检查 2: 配置
    try:
        cfg = load_config(config)
        console.print(f"[green]✓[/green] 配置加载成功 ({len(cfg.model_list)} 个模型)")
        checks_passed += 1
        
        # 验证配置
        errors = validate_config(cfg)
        if errors:
            console.print(f"[red]✗[/red] 配置验证失败:")
            for err in errors:
                console.print(f"  [red]-[/red] {err}")
            checks_failed += 1
        else:
            console.print("[green]✓[/green] 配置验证通过")
            checks_passed += 1
    except Exception as e:
        console.print(f"[red]✗[/red] 配置加载失败: {e}")
        checks_failed += 2
    
    # 检查 3: 服务状态
    from .daemon import _get_pid, _is_process_running
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


@app.command()
def coffee(
    link: Optional[str] = typer.Option(None, "--link", "-l", help="自定义赞助链接"),
    ascii: bool = typer.Option(False, "--ascii", "-a", help="纯文字模式"),
    open: bool = typer.Option(False, "--open", "-o", help="打开图片")
):
    """☕ 请作者喝一杯咖啡"""
    qr_path = get_qr_code_path()
    
    if link:
        from .coffee_qr import generate_qr_code
        qr_path = generate_qr_code(link)
    
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
            
            from .coffee_qr import display_image_terminal
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
