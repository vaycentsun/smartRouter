#!/bin/bash
# Smart Router 一键卸载脚本 (V3)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

echo "🗑️  正在卸载 Smart Router..."

# 使用虚拟环境的命令停止服务（如果存在）
VENV_SMR="$PROJECT_DIR/venv/bin/smr"
if [ -f "$VENV_SMR" ]; then
    echo "🛑 停止服务..."
    "$VENV_SMR" stop 2>/dev/null || true
fi

# 尝试从虚拟环境卸载
if [ -f "$PROJECT_DIR/venv/bin/pip" ]; then
    echo "📦 从虚拟环境卸载 Python 包..."
    "$PROJECT_DIR/venv/bin/pip" uninstall -q -y smart-router 2>/dev/null || true
fi

# 删除配置文件和数据
echo "🧹 清理数据文件..."
rm -rf ~/.smart-router

echo ""
echo "✅ Smart Router 已卸载"
echo ""
echo "📝 如需完全清除，请手动执行："
echo "   rm -rf $PROJECT_DIR/venv"
echo ""
