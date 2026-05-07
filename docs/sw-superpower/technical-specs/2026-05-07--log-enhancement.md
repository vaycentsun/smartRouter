# 日志功能增强 - 技术规格

## 架构概述

本方案通过 Python 标准库 `logging` 模块统一日志输出格式，并在查看层面提供等级筛选能力。

```
┌─────────────────────────────────────────────────────────┐
│                    Smart Router 服务                     │
│                                                         │
│  server_main.py ──► logging_config.setup_logging()     │
│       │                   │                             │
│       │                   ▼                             │
│       │         ┌─────────────────┐                    │
│       │         │  FileHandler    │──► smart-router.log│
│       │         │  (格式化日志)   │                    │
│       │         └─────────────────┘                    │
│       │                                                 │
│       ▼                                                 │
│  uvicorn (LiteLLM Proxy)                                │
│       │                                                 │
│       ▼                                                 │
│  SmartRouterMiddleware (console.print 输出)             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   Dashboard 服务                        │
│                                                         │
│  daemon.py ──► uvicorn.Config(log_config=...)          │
│       │                                                 │
│       ▼                                                 │
│  uvicorn (Dashboard) ──► dashboard.log                 │
└─────────────────────────────────────────────────────────┘

查看入口：
- CLI: view_logs() --level <LEVEL>
- Web API: GET /api/logs?level=<LEVEL>
```

## 组件设计

### 1. 日志配置模块 (`core/smart_router/utils/logging_config.py`)

**职责**：提供统一的 logging 配置接口

**接口**：
```python
def setup_logging(
    log_file: Path | str,
    level: int = logging.INFO,
    logger_name: str | None = None
) -> logging.Logger:
    """
    配置 logging 格式和处理器
    
    Args:
        log_file: 日志文件路径
        level: 日志等级（logging.DEBUG/INFO/WARNING/ERROR）
        logger_name: 如果指定，只配置该 logger；否则配置 root logger
    
    Returns:
        配置好的 logger
    """
```

**日志格式**：
```
%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s
```
实际输出示例：
```
2026-05-07 14:23:01,234 - smart_router.gateway.server - INFO - 配置已加载
```

**实现要点**：
- 使用 `logging.FileHandler` 写入文件
- 使用 `logging.StreamHandler` 输出到控制台（可选，用于 foreground 模式）
- 设置 `encoding='utf-8'` 避免中文乱码
- 如果 logger 已有 handler，先清除避免重复添加

### 2. 服务入口改造 (`core/smart_router/gateway/server_main.py`)

**变更**：
```python
# 新增导入
from smart_router.utils.logging_config import setup_logging
from pathlib import Path
import os

def main():
    parser = argparse.ArgumentParser(description="Smart Router Server")
    parser.add_argument("--config", "-c", type=Path, help="配置文件路径")
    parser.add_argument("--log-file", type=Path, help="日志文件路径")
    parser.add_argument("--log-level", default="INFO", help="日志等级")
    
    args = parser.parse_args()
    
    # 确定日志文件路径
    if args.log_file:
        log_file = args.log_file
    else:
        config_dir = args.config.parent if args.config else Path.home() / ".smart-router"
        log_file = config_dir / "smart-router.log"
    
    # 配置日志
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    setup_logging(log_file, level=log_level)
    
    # 继续原有启动逻辑...
```

**要点**：
- 日志文件路径通过命令行参数传入，默认 `~/.smart-router/smart-router.log`
- `daemon.py` 的 `start_daemon` 调用时需传递 `--log-file` 参数

### 3. 后台进程日志配置 (`core/smart_router/gateway/daemon.py`)

**变更 - `start_daemon` 函数**：
```python
def start_daemon(config_path: Optional[Path] = None, log_file: Optional[Path] = None):
    # ... 原有逻辑 ...
    
    # 构建启动命令 - 传递日志文件路径
    python_exe = _get_python_executable()
    cmd = [
        python_exe, "-m", "smart_router.gateway.server_main",
        "--log-file", str(log_file),
        "--log-level", "INFO",
    ]
    if config_path:
        cmd.extend(["--config", str(config_path)])
    
    # ... 后续启动逻辑 ...
```

**变更 - `start_dashboard_daemon` 函数**（前台模式）：
```python
def start_dashboard_daemon(host: str = "127.0.0.1", port: int = DASHBOARD_PORT, foreground: bool = True):
    if foreground:
        # 配置 uvicorn 日志
        import uvicorn
        from smart_router.utils.logging_config import get_uvicorn_log_config
        
        log_config = get_uvicorn_log_config(DASHBOARD_LOG_FILE)
        
        _write_pid_to_file(DASHBOARD_PID_FILE, os.getpid())
        # ... 信号处理 ...
        
        _dashboard_app = _build_dashboard_app()
        uvicorn.run(
            _dashboard_app,
            host=host,
            port=port,
            log_config=log_config,
        )
```

### 4. uvicorn 日志配置 (`core/smart_router/utils/logging_config.py` 新增)

```python
def get_uvicorn_log_config(log_file: Path | str) -> dict:
    """
    生成 uvicorn 的 log_config 字典
    
    Returns:
        符合 uvicorn 要求的 log_config 字典
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "formatter": "default",
                "filename": str(log_file),
                "encoding": "utf-8",
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["file", "console"], "level": "INFO"},
            "uvicorn.access": {"handlers": ["file", "console"], "level": "INFO"},
        },
    }
```

### 5. CLI 查看增强 (`core/smart_router/gateway/daemon.py` 的 `view_logs`)

**变更**：
```python
def view_logs(lines: int = 50, follow: bool = False, level: str = "ALL"):
    """
    查看服务日志
    
    Args:
        lines: 显示最后 N 行
        follow: 是否持续跟踪（类似 tail -f）
        level: 日志等级筛选（ALL/DEBUG/INFO/WARNING/ERROR）
    """
    log_file = DEFAULT_PID_DIR / "smart-router.log"
    
    if not log_file.exists():
        console.print("[yellow]日志文件不存在[/yellow]")
        return
    
    # 解析等级参数
    level_filter = None
    if level.upper() != "ALL":
        level_filter = getattr(logging, level.upper(), None)
        if level_filter is None:
            console.print(f"[red]无效的日志等级: {level}[/red]")
            return
    
    if follow:
        # 持续跟踪模式（原有逻辑 + 等级筛选）
        # ...
    else:
        # 显示最后 N 行（带等级筛选）
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
            
            # 解析并筛选
            filtered_lines = []
            for line in all_lines:
                parsed = parse_log_line(line)
                if level_filter is None:
                    filtered_lines.append(line.rstrip())
                elif parsed and parsed["levelno"] >= level_filter:
                    filtered_lines.append(line.rstrip())
                elif not parsed:
                    # 无法解析的行视为 INFO
                    if level_filter <= logging.INFO:
                        filtered_lines.append(line.rstrip())
            
            # 取最后 N 行
            display_lines = filtered_lines[-lines:]
            
            console.print(f"[dim]显示最后 {len(display_lines)} 行日志 (level>={level}):[/dim]\n")
            for line in display_lines:
                console.print(line)
                
        except IOError as e:
            console.print(f"[red]读取日志失败: {e}[/red]")
```

### 6. 日志行解析器 (`core/smart_router/utils/log_parser.py` 新文件)

```python
import re
import logging
from dataclasses import dataclass
from typing import Optional

@dataclass
class LogEntry:
    """解析后的日志条目"""
    timestamp: Optional[str]  # "2026-05-07 14:23:01,234"
    level: Optional[str]      # "INFO"
    levelno: int              # logging.INFO
    name: Optional[str]       # "smart_router.gateway.server"
    message: str              # 日志消息
    raw: str                  # 原始行

def parse_log_line(line: str) -> Optional[LogEntry]:
    """
    解析日志行，支持新旧格式
    
    新格式: 2026-05-07 14:23:01,234 - name - LEVEL - message
    旧格式: 任意文本（整个作为 message）
    
    Returns:
        LogEntry 或 None（解析失败）
    """
    # 尝试匹配新格式
    # 格式: YYYY-MM-DD HH:MM:SS,mmm - name - LEVEL - message
    pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^\s]+) - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - (.*)$'
    match = re.match(pattern, line.strip())
    
    if match:
        timestamp = match.group(1)
        name = match.group(2)
        level_str = match.group(3)
        message = match.group(4)
        levelno = getattr(logging, level_str, logging.INFO)
        
        return LogEntry(
            timestamp=timestamp,
            level=level_str,
            levelno=levelno,
            name=name,
            message=message,
            raw=line,
        )
    
    # 旧格式：整个行作为 message，标记为 INFO
    return LogEntry(
        timestamp=None,
        level="INFO",
        levelno=logging.INFO,
        name=None,
        message=line.strip(),
        raw=line,
    )
```

### 7. Web API 增强 (`core/smart_router/gateway/dashboard_api.py`)

**变更 - `read_log_lines` 函数**（需先找到该函数）：
```python
from smart_router.utils.log_parser import parse_log_line

def read_log_lines(source: str, offset: int = 0, limit: int = 500, level: str = "ALL"):
    """
    读取日志文件，返回结构化数据
    
    Args:
        source: 日志源（"service" 或 "dashboard"）
        offset: 从文件的第几个字节开始读取
        limit: 最多返回多少行
        level: 日志等级筛选
    
    Returns:
        LogReadResult 对象（包含 lines, structured_lines, offset, total_size）
    """
    log_file = LOG_FILE_MAP.get(source)
    if not log_file or not log_file.exists():
        return LogReadResult(lines=[], structured_lines=[], offset=0, total_size=0)
    
    # 解析等级参数
    level_filter = None
    if level.upper() != "ALL":
        level_filter = getattr(logging, level.upper(), None)
    
    result_lines = []
    structured_lines = []
    
    with open(log_file, "r", encoding="utf-8") as f:
        f.seek(offset)
        raw_lines = []
        current_offset = offset
        
        for line in f:
            parsed = parse_log_line(line)
            
            # 等级筛选
            if level_filter is not None:
                if parsed.levelno < level_filter:
                    continue
            
            result_lines.append(line.rstrip())
            structured_lines.append({
                "timestamp": parsed.timestamp,
                "level": parsed.level,
                "name": parsed.name,
                "message": parsed.message,
            })
            
            if len(result_lines) >= limit:
                break
        
        new_offset = f.tell()
    
    return LogReadResult(
        lines=result_lines,
        structured_lines=structured_lines,
        offset=new_offset,
        total_size=log_file.stat().st_size,
    )
```

**变更 - `get_logs` API 端点**：
```python
async def get_logs(
    source: str = "service",
    offset: int = 0,
    limit: int = 500,
    level: str = "ALL",  # 新增参数
):
    try:
        result = read_log_lines(source, offset, limit, level)
        return {
            "lines": result.lines,
            "structured_lines": result.structured_lines,  # 新增字段
            "offset": result.offset,
            "total_size": result.total_size,
        }
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {e}")
```

## 数据流

### 日志生成流程
```
代码调用 logger.info/warning/error()
    ↓
logging 模块根据 Formatter 格式化
    ↓
FileHandler 写入 smart-router.log 或 dashboard.log
    ↓
格式: 2026-05-07 14:23:01,234 - name - LEVEL - message
```

### 日志查看流程（CLI）
```
view_logs(lines=50, level="ERROR")
    ↓
打开日志文件，逐行读取
    ↓
parse_log_line(line) 解析每行
    ↓
根据 level_filter 筛选
    ↓
显示最后的 N 行
```

### 日志查看流程（Web API）
```
GET /api/logs?source=service&level=WARNING&limit=100
    ↓
read_log_lines(source, offset, limit, level)
    ↓
打开日志文件，解析并筛选
    ↓
返回 {lines, structured_lines, offset, total_size}
```

## 错误处理

| 场景 | 处理策略 |
|------|----------|
| 日志文件不存在 | CLI: 显示提示；API: 返回空列表和 offset=0 |
| 无效等级参数 | CLI: 报错并退出；API: 返回 400 错误 |
| 日志文件读取失败（权限） | CLI/API: 捕获 IOError，返回友好错误 |
| 日志行解析失败 | 视为旧格式，整个行作为 message，标记 INFO |
| logging 配置失败 | 捕获异常，输出错误但不阻止服务启动 |

## 安全考虑

- 日志文件权限：确保 `~/.smart-router/` 目录权限为 700，日志文件权限为 600
- 日志内容：不应包含 API Key 等敏感信息（需检查现有 logging 是否可能泄露）
- API 接口：`/api/logs` 需通过 Smart Router Master Key 认证（已有机制）
- 路径遍历：校验 source 参数只能是 "service" 或 "dashboard"，防止路径遍历攻击

## 测试计划

### 单元测试
1. `test_log_parser.py`:
   - `test_parse_new_format`: 解析新格式日志行
   - `test_parse_old_format`: 解析旧格式日志行（无时间戳/等级）
   - `test_parse_invalid_line`: 解析格式错误的行
   - `test_log_entry_dataclass`: 验证 LogEntry 字段

2. `test_logging_config.py`:
   - `test_setup_logging_creates_file`: 验证日志文件被创建
   - `test_log_format`: 验证输出格式符合预期
   - `test_log_level_filter`: 验证等级过滤生效

3. `test_daemon.py`:
   - `test_view_logs_with_level`: 测试 --level 参数
   - `test_view_logs_follow_with_level`: 测试 follow 模式 + 等级筛选

4. `test_logs_api.py`:
   - `test_logs_with_level_filter`: 测试 `?level=ERROR`
   - `test_logs_structured_lines`: 验证 structured_lines 字段
   - `test_logs_invalid_level`: 测试无效等级参数

### 集成测试
1. 启动服务，验证日志文件格式
2. 通过 CLI 和 API 查看日志，验证筛选功能

## 验收标准

- [ ] 新启动的服务日志每行包含 `YYYY-MM-DD HH:MM:SS,mmm - logger.name - LEVEL - message` 格式
- [ ] Dashboard 日志（uvicorn）同样包含时间戳和等级
- [ ] CLI `view_logs --level ERROR` 只显示 ERROR 级别日志
- [ ] CLI `view_logs --level INFO` 显示 INFO 及以上级别（INFO/WARNING/ERROR）
- [ ] Web API `GET /api/logs?level=WARNING` 返回结构化数据中只含 WARNING 及以上
- [ ] 旧日志文件（无时间戳/等级）仍可被读取，解析时标记为 INFO 级别
- [ ] `read_log_lines` 返回的 `structured_lines` 包含 timestamp、level、name、message 字段
- [ ] 单元测试覆盖：日志格式验证、等级筛选逻辑、旧格式兼容解析
