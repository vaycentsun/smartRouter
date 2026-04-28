#!/usr/bin/env python3
"""
Smart Router 服务入口（用于后台启动）
"""
import argparse
import sys
from pathlib import Path

from .server import start_server


def main():
    parser = argparse.ArgumentParser(description="Smart Router Server")
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="配置文件路径"
    )
    
    args = parser.parse_args()
    
    try:
        start_server(config_path=args.config)
    except KeyboardInterrupt:
        print("\n服务已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
