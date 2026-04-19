#!/bin/bash
# Smart Router 一键卸载脚本

set -e

echo "🗑️  正在卸载 Smart Router..."

# 停止服务（如果正在运行）
if command -v smart-router &> /dev/null; then
    echo "🛑 停止服务..."
    smart-router stop 2>/dev/null || true
fi

# 卸载包
echo "📦 卸载 Python 包..."
pip uninstall -q -y smart-router 2>/dev/null || true

# 删除配置文件和日志
echo "🧹 清理数据文件..."
rm -rf ~/.smart-router

echo ""
echo "✅ Smart Router 已卸载"
echo ""
echo "📝 手动清理（如需完全清除）："
echo "   删除配置文件: rm smart-router.yaml"
echo "   删除虚拟环境: rm -rf venv"
echo ""
