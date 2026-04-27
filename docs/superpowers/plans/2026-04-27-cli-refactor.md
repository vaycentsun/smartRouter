# CLI 模块化重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 823 行的单一 cli.py 拆分为 cli/ 子模块，实现命令级模块化

**Architecture:** 使用 Typer 的命令分组模式，将 10 个命令拆分到独立文件，通过 cli/__init__.py 统一导出。保持向后兼容：from smart_router.cli import app 仍可用。

**Tech Stack:** Typer, Rich

---

## 当前结构与目标结构对比

### 当前 cli.py（823 行，10 个命令）

| 行号 | 命令函数 |
|------|---------|
| 34 | version |
| 58 | init |
| 328 | doctor |
| 329 | start |
| 349 | stop |
| 355 | restart |
| 363 | logs |
| 378 | list |
| 481 | dry-run |
| 734 | coffee |

### 目标结构

```
src/smart_router/cli/
├── __init__.py              # 统一导出 app, __version__, console
├── commands/
│   ├── __init__.py
│   ├── version.py          # version 命令
│   ├── init.py           # init 命令
│   ├── doctor.py         # doctor 命令
│   ├── service.py        # start/stop/restart/logs 命令
│   ├── list.py          # list 命令
│   ├── dry_run.py      # dry-run 命令
│   └── coffee.py       # coffee 命令
└── options/
    ├── __init__.py
    └── config.py       # 通用选项（如 --config）
```

---

## Task 1: 创建 cli/ 目录结构

**Files:**
- Create: `src/smart_router/cli/__init__.py`
- Create: `src/smart_router/cli/commands/__init__.py`
- Create: `src/smart_router/cli/options/__init__.py`

- [ ] **Step 1: 创建 cli/ 目录和 __init__.py**

```bash
mkdir -p src/smart_router/cli/commands src/smart_router/cli/options
touch src/smart_router/cli/__init__.py
touch src/smart_router/cli/commands/__init__.py
touch src/smart_router/cli/options/__init__.py
```

- [ ] **Step 2: 创建 cli/__init__.py 基础结构**

```python
"""Smart Router CLI — 模块化版本"""

from typing import Optional
import typer
from rich.console import Console

app = typer.Typer(name="smart-router", help="智能模型路由网关")
console = Console()
__version__ = "1.1.0"

__all__ = ["app", "console", "__version__"]
```

- [ ] **Step 3: 提交**

```bash
git add src/smart_router/cli/
git commit -m "refactor(cli): 创建 cli/ 子模块目录结构"
```

---

## Task 2: 拆分 version 命令

**Files:**
- Create: `src/smart_router/cli/commands/version.py`
- Modify: `src/smart_router/cli/__init__.py`

- [ ] **Step 1: 创建 version.py 命令模块**

```python
"""version 命令"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .. import app, console, __version__

@app.command()
def version(short: bool = typer.Option(False, "--short", "-s", help="仅显示版本号")):
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
```

- [ ] **Step 2: 在 cli/__init__.py 导入 version 命令**

在 `src/smart_router/cli/__init__.py` 末尾添加：
```python
from .commands.version import version
```

- [ ] **Step 3: 验证测试**

```bash
pytest src/smart_router/tests/cli/test_cli.py::TestVersionCommand -v
```

- [ ] **Step 4: 提交**

```bash
git add src/smart_router/cli/commands/version.py src/smart_router/cli/__init__.py
git commit -m "refactor(cli): 拆分 version 命令到独立模块"
```

---

## Task 3: 拆分 init 命令

**Files:**
- Create: `src/smart_router/cli/commands/init.py`
- Modify: `src/smart_router/cli/__init__.py`

- [ ] **Step 1: 读取 cli.py 中 init 命令的实现**

从 cli.py (line 58-140) 获取 init 命令完整代码，拆分到 init.py

- [ ] **Step 2: 创建 init.py 命令模块**

```python
"""init 命令"""

from pathlib import Path
import typer
import shutil
from importlib.resources import files

from .. import app, console

# 从原始 cli.py 复制的完整实现
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
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    try:
        templates_dir = files("smart_router") / "templates"
        if templates_dir.exists() and (templates_dir / "models.yaml").exists():
            for filename in ["providers.yaml", "models.yaml", "routing.yaml"]:
                src = templates_dir / filename
                dst = output_dir / filename
                if src.exists():
                    shutil.copy2(str(src), dst)
                    console.print(f"[green]✓[/green] {filename}")
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        raise typer.Exit(1)
    
    console.print(f"\n[green]✓[/green] 配置文件已生成到 {output_dir}")
```

- [ ] **Step 3: 更新 cli/__init__.py**

```python
from .commands.init import init
```

- [ ] **Step 4: 验证测试**

```bash
pytest src/smart_router/tests/cli/test_cli.py::TestInitCommand -v
```

- [ ] **Step 5: 提交**

```bash
git add src/smart_router/cli/commands/init.py src/smart_router/cli/__init__.py
git commit -m "refactor(cli): 拆分 init 命令到独立模块"
```

---

## Task 4: 拆分 service 命令组（start/stop/restart/logs）

**Files:**
- Create: `src/smart_router/cli/commands/service.py`
- Modify: `src/smart_router/cli/__init__.py`

- [ ] **Step 1: 创建 service.py 命令模块**

从 cli.py 合并 doctor + start + stop + restart + logs 命令到 service.py：

```python
"""service 命令组：doctor/start/stop/restart/logs"""

from pathlib import Path
from typing import Optional
import typer

from .. import app, console
from ...gateway.daemon import start_daemon, stop_daemon, restart_daemon, check_status, view_logs
from ...config.loader import ConfigLoader, ConfigError

@app.command()
def doctor(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="配置文件路径")
):
    """检查配置和依赖"""
    # 此处添加 doctor 命令完整实现
    ...

@app.command()
def start(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="配置文件路径"),
    foreground: bool = typer.Option(False, "--foreground", "-f", help="前台运行")
):
    """启动 Smart Router 服务"""
    if foreground:
        from ...gateway.server import start_server
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
def logs(
    lines: int = typer.Option(100, "--lines", "-n", help="显示行数"),
    follow: bool = typer.Option(False, "--follow", "-f", help="实时日志")
):
    """查看服务日志"""
    view_logs(lines=lines, follow=follow)
```

- [ ] **Step 2: 更新 cli/__init__.py**

```python
from .commands.service import doctor, start, stop, restart, logs
```

- [ ] **Step 3: 验证测试**

```bash
pytest src/smart_router/tests/cli/test_cli.py::TestServiceCommands -v
```

- [ ] **Step 4: 提交**

```bash
git add src/smart_router/cli/commands/service.py src/smart_router/cli/__init__.py
git commit -m "refactor(cli): 拆分 service 命令组到独立模块"
```

---

## Task 5: 拆分 list/dry_run/coffee 命令

**Files:**
- Create: `src/smart_router/cli/commands/list.py`
- Create: `src/smart_router/cli/commands/dry_run.py`
- Create: `src/smart_router/cli/commands/coffee.py`
- Modify: `src/smart_router/cli/__init__.py`

- [ ] **Step 1: 拆分 list 命令到 list.py**

- [ ] **Step 2: 拆分 dry-run 命令到 dry_run.py**

- [ ] **Step 3: 拆分 coffee 命令到 coffee.py**

- [ ] **Step 4: 更新 cli/__init__.py 导入所有命令**

- [ ] **Step 5: 验证测试**

```bash
pytest src/smart_router/tests/cli/ -v
```

- [ ] **Step 6: 提交**

```bash
git add src/smart_router/cli/commands/
git commit -m "refactor(cli): 拆分 list/dry_run/coffee 命令"
```

---

## Task 6: 更新入口点并验证

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/smart_router/cli/__init__.py`

- [ ] **Step 1: 验证向后兼容**

确保以下导入仍然可用：
```python
from smart_router.cli import app  # 应正常工作
```

- [ ] **Step 2: 更新 pyproject.toml（如需要）**

检查 [project.scripts] 是否需要更改：
```toml
[project.scripts]
smart-router = "smart_router.cli:main"
smr = "smart_router.cli:main"
```

如果 cli/__init__.py 导出 main 函数，则无需更改。

- [ ] **Step 3: 运行完整测试**

```bash
pytest -v 2>&1 | tail -20
```

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml src/smart_router/cli/
git commit -m "refactor(cli): 完成 CLI 模块化重构"
```

---

## 验证检查点

完成所有任务后，运行以下验证：

```bash
# 1. 所有测试通过
pytest -v --tb=short

# 2. CLI 命令可用
smart-router version
smr version --short

# 3. 向后兼容
python -c "from smart_router.cli import app; print(app)"
```

---

## 替代方案：保持 cli.py 单一文件

如果重构工作量过大，可选择最小改动方案：

```python
# src/smart_router/cli.py 开头添加
from .cli import commands  # 如果拆分命令到 commands/ 子模块
```

但这种方式不如完全重构清晰。

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-27-cli-refactor.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**