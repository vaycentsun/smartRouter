#!/bin/bash
# Smart Router 一键卸载脚本 (V3) - 支持生产环境安装

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
CONFIG_DIR="$HOME/.smart-router"
VENV_DIR="$CONFIG_DIR/venv"

echo "🗑️  正在卸载 Smart Router..."

# 1. 使用系统命令停止服务（如果存在）
if command -v smr &> /dev/null; then
    echo "🛑 停止服务..."
    smr stop 2>/dev/null || true
fi

# 2. 使用虚拟环境的命令停止服务（如果生产环境 venv 存在）
if [ -f "$VENV_DIR/bin/smr" ]; then
    echo "🛑 停止服务 (生产环境)..."
    "$VENV_DIR/bin/smr" stop 2>/dev/null || true
fi

# 3. 使用项目目录 venv 停止服务（向后兼容）
PROJECT_VENV_SMR="$PROJECT_DIR/venv/bin/smr"
if [ -f "$PROJECT_VENV_SMR" ]; then
    echo "🛑 停止服务 (项目环境)..."
    "$PROJECT_VENV_SMR" stop 2>/dev/null || true
fi

# 4. 尝试从虚拟环境卸载
if [ -f "$VENV_DIR/bin/pip" ]; then
    echo "📦 从虚拟环境卸载 Python 包..."
    "$VENV_DIR/bin/pip" uninstall -q -y smart-router 2>/dev/null || true
fi

# 5. 删除配置文件和数据
echo "🧹 清理数据文件..."
rm -rf "$CONFIG_DIR"

# 6. 删除系统级 symlink
echo "🧹 清理系统命令..."
if [ -L "/usr/local/bin/smart-router" ]; then
    # 检查是否指向我们的 venv
    link_target=$(readlink "/usr/local/bin/smart-router")
    if [[ "$link_target" == *".smart-router"* ]]; then
        if [ -w "/usr/local/bin" ]; then
            rm -f "/usr/local/bin/smart-router"
            rm -f "/usr/local/bin/smr"
            echo "  ✓ 已移除系统命令"
        else
            echo "  ⚠️  需要管理员权限移除系统命令，请手动执行："
            echo "    sudo rm -f /usr/local/bin/smart-router"
            echo "    sudo rm -f /usr/local/bin/smr"
        fi
    fi
fi

# 7. 清理项目目录下的旧 venv（如果存在）
if [ -d "$PROJECT_DIR/venv" ]; then
    echo "🧹 清理项目目录下的旧虚拟环境..."
    rm -rf "$PROJECT_DIR/venv"
fi

echo ""
echo "✅ Smart Router 已卸载"
echo ""
