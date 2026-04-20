#!/bin/bash
# Smart Router 一键安装脚本 (V3)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
cd "$PROJECT_DIR"

echo "🚀 正在安装 Smart Router..."

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.9"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ 需要 Python 3.9+，当前版本: $python_version"
    exit 1
fi

# 创建虚拟环境（如果不存在）
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

# 使用虚拟环境的 pip 安装
echo "📦 安装依赖到虚拟环境..."
"$VENV_DIR/bin/pip" install -q -e ".[dev]"

# 验证安装
echo "✅ 验证安装..."
"$VENV_DIR/bin/python" script/verify.py

# 生成默认配置（如果不存在）
CONFIG_DIR="$HOME/.smart-router"
if [ ! -f "$CONFIG_DIR/providers.yaml" ]; then
    echo "📝 生成默认配置文件..."
    "$VENV_DIR/bin/smart-router" init
fi

echo ""
echo "✨ Smart Router 安装成功！"
echo ""
echo "📁 配置文件位置: ~/.smart-router/"
echo "   - providers.yaml  # 配置 API Key"
echo "   - models.yaml     # 模型能力配置"
echo "   - routing.yaml    # 路由策略配置"
echo ""
echo "📖 快速开始："
echo "   1. 编辑 ~/.smart-router/providers.yaml 配置 API Key"
echo "   2. 启动服务: ./venv/bin/smr start"
echo "   3. 查看状态: ./venv/bin/smr status"
echo ""
echo "🛠️  常用命令："
echo "   ./venv/bin/smr start     # 后台启动"
echo "   ./venv/bin/smr stop      # 停止服务"
echo "   ./venv/bin/smr status    # 查看状态"
echo "   ./venv/bin/smr logs      # 查看日志"
echo "   ./venv/bin/smr doctor    # 健康检查"
echo ""
