"""日志配置模块"""

import logging
from pathlib import Path
from typing import Optional, Union


def setup_logging(
    log_file: Union[Path, str],
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


def get_uvicorn_log_config(log_file: Union[Path, str]) -> dict:
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
