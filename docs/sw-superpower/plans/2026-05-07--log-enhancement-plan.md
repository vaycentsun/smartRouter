# 日志功能增强 - 实现计划

## 任务概览

| 编号 | 任务 | 文件 | 类型 | 依赖 |
|------|------|------|------|------|
| 1 | 创建 logging_config.py | `core/smart_router/utils/logging_config.py` | 创建 | - |
| 2 | 编写 logging_config 测试 | `core/smart_router/utils/tests/test_logging_config.py` | 测试 | 1 |
| 3 | 创建 log_parser.py | `core/smart_router/utils/log_parser.py` | 创建 | - |
| 4 | 编写 log_parser 测试 | `core/smart_router/utils/tests/test_log_parser.py` | 测试 | 3 |
| 5 | 修改 server_main.py | `core/smart_router/gateway/server_main.py` | 修改 | 1 |
| 6 | 修改 daemon.py - start_daemon | `core/smart_router/gateway/daemon.py` | 修改 | 5 |
| 7 | 修改 daemon.py - start_dashboard_daemon | `core/smart_router/gateway/daemon.py` | 修改 | 1 |
| 8 | 修改 daemon.py - view_logs | `core/smart_router/gateway/daemon.py` | 修改 | 3 |
| 9 | 编写 daemon 日志测试 | `core/smart_router/gateway/tests/test_daemon.py` | 测试 | 6,7,8 |
| 10 | 修改 dashboard_api.py - read_log_lines | `core/smart_router/gateway/dashboard_api.py` | 修改 | 3 |
| 11 | 修改 dashboard_api.py - get_logs | `core/smart_router/gateway/dashboard_api.py` | 修改 | 10 |
| 12 | 编写 logs API 测试 | `core/smart_router/gateway/tests/test_logs_api.py` | 测试 | 10,11 |

---

### 任务 1: 创建 logging_config.py

**文件**: `core/smart_router/utils/logging_config.py`

**动作**: 创建日志配置模块，提供 setup_logging() 和 get_uvicorn_log_config() 函数

**详情**:
```python
import logging
from pathlib import Path
from typing import Optional

def setup_logging(
    log_file: Path | str,
    level: int = logging.INFO,
    logger_name: Optional[str] = None
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
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()
    
    # 清除已有 handler，避免重复
    logger.handlers.clear()
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(level)
    
    return logger


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
            "uvicorn": {"handlers": ["file", "console"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["file", "console"], "level": "INFO", "propagate": False},
        },
    }
```

**验证**:
- [ ] 文件存在
- [ ] 语法正确（import 无报错）
- [ ] `setup_logging()` 可调用并创建日志文件
- [ ] 日志格式符合预期（含时间戳和等级）

---

### 任务 2: 编写 logging_config 测试

**文件**: `core/smart_router/utils/tests/test_logging_config.py`

**动作**: 为 logging_config 模块编写单元测试

**详情**: 测试场景列表
- `test_setup_logging_creates_file`: 验证日志文件被创建
- `test_setup_logging_format`: 验证输出格式符合 `YYYY-MM-DD HH:MM:SS,mmm - name - LEVEL - message`
- `test_setup_logging_level`: 验证等级过滤（WARNING 级别不输出 INFO）
- `test_get_uvicorn_log_config`: 验证返回的字典结构正确
- `test_setup_logging_no_duplicate_handlers`: 多次调用不重复添加 handler

**验证**:
- [ ] 测试可运行 `pytest test_logging_config.py -v`
- [ ] 测试先失败（RED，任务1未实现时）
- [ ] 实现后通过（GREEN）

---

### 任务 3: 创建 log_parser.py

**文件**: `core/smart_router/utils/log_parser.py`

**动作**: 创建日志行解析器，支持新旧格式

**详情**:
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

def parse_log_line(line: str) -> LogEntry:
    """
    解析日志行，支持新旧格式
    
    新格式: 2026-05-07 14:23:01,234 - name - LEVEL - message
    旧格式: 任意文本（整个作为 message）
    
    Returns:
        LogEntry 对象
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

**验证**:
- [ ] 文件存在
- [ ] 语法正确
- [ ] `parse_log_line()` 可正确解析新格式
- [ ] `parse_log_line()` 可兼容旧格式

---

### 任务 4: 编写 log_parser 测试

**文件**: `core/smart_router/utils/tests/test_log_parser.py`

**动作**: 为 log_parser 模块编写单元测试

**详情**: 测试场景列表
- `test_parse_new_format`: 解析新格式日志行，验证所有字段
- `test_parse_old_format`: 解析旧格式（无时间戳/等级），验证 message 为整行
- `test_parse_invalid_line`: 解析格式错误的行，验证返回 INFO 级别
- `test_log_entry_dataclass`: 验证 LogEntry 字段可访问

**验证**:
- [ ] 测试可运行 `pytest test_log_parser.py -v`
- [ ] 测试先失败（RED）
- [ ] 实现后通过（GREEN）

---

### 任务 5: 修改 server_main.py

**文件**: `core/smart_router/gateway/server_main.py`

**动作**: 添加日志配置参数，调用 setup_logging()

**详情**: 在文件开头添加导入，在 main() 函数中添加参数和处理逻辑：

添加导入：
```python
from smart_router.utils.logging_config import setup_logging
from pathlib import Path
import os
import logging
```

修改 main() 函数，在 `args = parser.parse_args()` 之后添加：
```python
    # 确定日志文件路径
    if args.log_file:
        log_file = args.log_file
    else:
        config_dir = args.config.parent if args.config else Path.home() / ".smart-router"
        log_file = config_dir / "smart-router.log"
    
    # 配置日志
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    setup_logging(log_file, level=log_level)
```

在 parser 中添加参数：
```python
    parser.add_argument("--log-file", type=Path, help="日志文件路径")
    parser.add_argument("--log-level", default="INFO", help="日志等级 (DEBUG/INFO/WARNING/ERROR)")
```

**验证**:
- [ ] 文件修改正确
- [ ] `python -m smart_router.gateway.server_main --help` 显示新参数
- [ ] 启动后日志文件包含时间戳和等级

---

### 任务 6: 修改 daemon.py - start_daemon

**文件**: `core/smart_router/gateway/daemon.py`

**动作**: 修改 start_daemon() 函数，传递日志参数给子进程

**详情**: 在构建启动命令时添加 `--log-file` 和 `--log-level` 参数：

找到 `cmd = [python_exe, "-m", "smart_router.gateway.server_main"]` 这一行，在其后添加：
```python
    cmd = [python_exe, "-m", "smart_router.gateway.server_main"]
    cmd.extend(["--log-file", str(log_file)])
    cmd.extend(["--log-level", "INFO"])
    if config_path:
        cmd.extend(["--config", str(config_path)])
```

**验证**:
- [ ] 修改正确
- [ ] `smart-router start` 启动后日志格式正确

---

### 任务 7: 修改 daemon.py - start_dashboard_daemon

**文件**: `core/smart_router/gateway/daemon.py`

**动作**: 修改 start_dashboard_daemon() 函数，配置 uvicorn 日志

**详情**: 在前台模式分支中，配置 uvicorn 使用自定义日志格式：

在 `if foreground:` 分支内，在 `_write_pid_to_file(DASHBOARD_PID_FILE, os.getpid())` 之前添加：
```python
        # 配置 uvicorn 日志
        import uvicorn
        from smart_router.utils.logging_config import get_uvicorn_log_config
        
        log_config = get_uvicorn_log_config(DASHBOARD_LOG_FILE)
```

修改 `uvicorn.run()` 调用，添加 `log_config` 参数：
```python
        uvicorn.run(
            _dashboard_app,
            host=host,
            port=port,
            log_config=log_config,
        )
```

**验证**:
- [ ] 修改正确
- [ ] `smr dashboard` 启动后 dashboard.log 包含时间戳和等级

---

### 任务 8: 修改 daemon.py - view_logs

**文件**: `core/smart_router/gateway/daemon.py`

**动作**: 修改 view_logs() 函数，添加 --level 参数和筛选逻辑

**详情**: 

1. 修改函数签名，添加 `level` 参数：
```python
def view_logs(lines: int = 50, follow: bool = False, level: str = "ALL"):
```

2. 在函数开头添加 level 解析：
```python
    # 解析等级参数
    level_filter = None
    if level.upper() != "ALL":
        level_filter = getattr(logging, level.upper(), None)
        if level_filter is None:
            console.print(f"[red]无效的日志等级: {level}[/red]")
            return
```

3. 修改 else 分支（非 follow 模式）的日志读取逻辑，添加筛选：
```python
    else:
        # 显示最后 N 行
        try:
            from smart_router.utils.log_parser import parse_log_line
            
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
            
            # 解析并筛选
            filtered_lines = []
            for line in all_lines:
                parsed = parse_log_line(line)
                if level_filter is None:
                    filtered_lines.append(line.rstrip())
                elif parsed.levelno >= level_filter:
                    filtered_lines.append(line.rstrip())
                elif parsed.timestamp is None:
                    # 无法解析的行视为 INFO
                    if level_filter <= logging.INFO:
                        filtered_lines.append(line.rstrip())
            
            # 取最后 N 行
            display_lines = filtered_lines[-lines:] if lines > 0 else filtered_lines
            
            level_display = level if level_filter is None else logging.getLevelName(level_filter)
            console.print(f"[dim]显示最后 {len(display_lines)} 行日志 (level>={level_display}):[/dim]\n")
            for line in display_lines:
                console.print(line)
                
        except IOError as e:
            console.print(f"[red]读取日志失败: {e}[/red]")
```

**验证**:
- [ ] 修改正确
- [ ] `smart-router logs --level ERROR` 只显示 ERROR 日志
- [ ] `smart-router logs --level INFO` 显示 INFO 及以上

---

### 任务 9: 编写 daemon 日志测试

**文件**: `core/smart_router/gateway/tests/test_daemon.py`

**动作**: 在 TestLogs 类中添加日志等级筛选测试

**详情**: 测试场景列表
- `test_view_logs_with_level_error`: 创建包含不同等级的日志文件，验证 --level ERROR 只显示 ERROR
- `test_view_logs_with_level_info`: 验证 --level INFO 显示 INFO/WARNING/ERROR
- `test_view_logs_with_invalid_level`: 验证无效等级参数报错
- `test_view_logs_follow_with_level`: 验证 follow 模式也支持等级筛选（可选，较复杂可后补）

**验证**:
- [ ] 测试可运行
- [ ] 测试先失败（RED）
- [ ] 实现后通过（GREEN）

---

### 任务 10: 修改 dashboard_api.py - read_log_lines

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 修改 read_log_lines() 函数，添加 level 参数和结构化输出

**详情**: 

1. 在文件开头添加导入：
```python
from smart_router.utils.log_parser import parse_log_line
import logging
```

2. 修改 `read_log_lines()` 函数签名：
```python
def read_log_lines(source: str, offset: int = 0, limit: int = 500, level: str = "ALL"):
```

3. 在函数内添加 level 解析和结构化输出：
```python
    # 解析等级参数
    level_filter = None
    if level.upper() != "ALL":
        level_filter = getattr(logging, level.upper(), None)
    
    result_lines = []
    structured_lines = []
    
    with open(log_file, "r", encoding="utf-8") as f:
        f.seek(offset)
        
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

注意：需要确保 `LogReadResult` 类有 `structured_lines` 字段。

**验证**:
- [ ] 修改正确
- [ ] 返回数据包含 structured_lines 字段
- [ ] 等级筛选生效

---

### 任务 11: 修改 dashboard_api.py - get_logs

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 修改 get_logs() API 端点，添加 level 查询参数

**详情**: 

1. 修改 `get_logs()` 函数签名，添加 `level` 参数：
```python
async def get_logs(
    source: str = "service",
    offset: int = 0,
    limit: int = 500,
    level: str = "ALL",
):
```

2. 修改返回值，添加 `structured_lines`：
```python
    try:
        result = read_log_lines(source, offset, limit, level)
        return {
            "lines": result.lines,
            "structured_lines": result.structured_lines,
            "offset": result.offset,
            "total_size": result.total_size,
        }
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {e}")
```

**验证**:
- [ ] 修改正确
- [ ] `GET /api/logs?level=WARNING` 返回筛选后的日志
- [ ] `structured_lines` 字段包含正确数据

---

### 任务 12: 编写 logs API 测试

**文件**: `core/smart_router/gateway/tests/test_logs_api.py`

**动作**: 在 TestLogs 类中添加等级筛选测试

**详情**: 测试场景列表
- `test_logs_with_level_filter`: 创建包含不同等级的日志，验证 ?level=ERROR 只返回 ERROR
- `test_logs_structured_lines`: 验证 structured_lines 字段包含 timestamp、level、name、message
- `test_logs_invalid_level`: 验证无效 level 参数返回 400 错误
- `test_logs_level_all`: 验证默认 level=ALL 返回所有日志

**验证**:
- [ ] 测试可运行 `pytest test_logs_api.py -v`
- [ ] 测试先失败（RED）
- [ ] 实现后通过（GREEN）

---

## 验收标准覆盖检查

| 验收标准 | 对应任务 |
|----------|----------|
| 新启动的服务日志每行包含正确格式 | 1, 5, 6 |
| Dashboard 日志同样包含时间戳和等级 | 1, 7 |
| CLI `view_logs --level ERROR` 只显示 ERROR | 8, 9 |
| CLI `view_logs --level INFO` 显示 INFO 及以上 | 8, 9 |
| Web API `?level=WARNING` 返回筛选数据 | 10, 11, 12 |
| 旧日志文件仍可被读取 | 3, 4, 8, 10 |
| `structured_lines` 包含正确字段 | 3, 10, 12 |
| 单元测试覆盖 | 2, 4, 9, 12 |

---

## 预计总时间

约 120 分钟（12 个任务 × 10 分钟平均）
