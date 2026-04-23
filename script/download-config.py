#!/usr/bin/env python3
"""
Smart Router 配置下载脚本
可通过 curl 直接调用下载默认配置

使用方法:
    curl -sSL https://raw.githubusercontent.com/vaycent/smartRouter/main/script/download-config.py | python3

或带参数:
    curl -sSL ... | python3 - --output /path/to/dir --force
"""

import argparse
import os
import sys
from pathlib import Path


def download_configs(output_dir: Path, force: bool = False) -> bool:
    """下载配置文件到指定目录"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # GitHub Raw URL
    repo_url = "https://raw.githubusercontent.com/vaycentsun/smartRouter/main"
    config_files = ["providers.yaml", "models.yaml", "routing.yaml"]
    
    downloaded = []
    skipped = []
    failed = []
    
    import urllib.request
    import urllib.error
    
    for filename in config_files:
        # Fetch from templates directory to align with new source of config
        url = f"{repo_url}/src/smart_router/templates/{filename}"
        filepath = output_dir / filename
        
        if filepath.exists() and not force:
            skipped.append(filename)
            continue
        
        try:
            urllib.request.urlretrieve(url, filepath)
            downloaded.append(filename)
        except urllib.error.HTTPError as e:
            print(f"✗ 下载失败 {filename}: HTTP {e.code}")
            failed.append(filename)
        except Exception as e:
            print(f"✗ 下载失败 {filename}: {e}")
            failed.append(filename)
    
    # 输出结果
    if downloaded:
        print(f"✓ 已下载: {', '.join(downloaded)}")
    if skipped:
        print(f"⚠ 已跳过 (文件存在): {', '.join(skipped)}")
    if failed:
        print(f"✗ 失败: {', '.join(failed)}")
    
    return len(failed) == 0


def main():
    parser = argparse.ArgumentParser(
        description="下载 Smart Router 默认配置文件"
    )
    parser.add_argument(
        "--output", "-o",
        default=os.path.expanduser("~/.smart-router"),
        help="配置文件输出目录 (默认: ~/.smart-router)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制覆盖已存在的配置文件"
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    print(f"📁 配置目录: {output_dir.absolute()}")
    print("⬇️  下载配置文件...")
    
    success = download_configs(output_dir, force=args.force)
    
    if success:
        print(f"\n✨ 完成！配置文件已保存到: {output_dir.absolute()}")
        print("\n📝 下一步:")
        print("   1. 编辑 providers.yaml 配置你的 API Key")
        print("   2. 运行 'smart-router start' 启动服务")
        return 0
    else:
        print("\n❌ 部分配置文件下载失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
