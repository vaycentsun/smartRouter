#!/usr/bin/env python3
"""
Smart Router 服务入口（用于后台启动）
"""
import argparse
import logging
import os
import sys
from pathlib import Path

from smart_router.utils.logging_config import setup_logging

from .server import start_server


def main():
    parser = argparse.ArgumentParser(description="Smart Router Server")
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="配置文件路径"
    )
    parser.add_argument("--log-file", type=Path, help="日志文件路径")
    parser.add_argument("--log-level", default="INFO", help="日志等级 (DEBUG/INFO/WARNING/ERROR)")
    
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
    
    try:
        start_server(config_path=args.config)
    except KeyboardInterrupt:
        print("\n服务已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
