#!/bin/bash
# Smart Router 一键安装脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "🚀 正在安装 Smart Router..."

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.9"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ 需要 Python 3.9+，当前版本: $python_version"
    exit 1
fi

# 安装依赖
echo "📦 安装依赖..."
pip install -q -e ".[dev]"

# 验证安装
echo "✅ 验证安装..."
python3 script/verify.py

# 生成默认配置（如果不存在）
if [ ! -f "smart-router.yaml" ]; then
    echo "📝 生成默认配置文件..."
    smart-router init
fi

echo ""
echo "✨ Smart Router 安装成功！"
echo ""
echo "📖 快速开始："
echo "   1. 编辑 smart-router.yaml 配置 API Key"
echo "   2. 启动服务: smart-router start"
echo "   3. 查看状态: smart-router status"
echo ""
echo "🛠️  常用命令："
echo "   smart-router start     # 后台启动"
echo "   smart-router stop      # 停止服务"
echo "   smart-router status    # 查看状态"
echo "   smart-router logs      # 查看日志"
echo ""
