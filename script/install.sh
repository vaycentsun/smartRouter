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

# ==================== 清理旧版本 ====================
echo "🧹 检查并清理旧版本..."

# 1. 停止旧服务（如果运行中）
if command -v smart-router &> /dev/null; then
    echo "  🛑 停止旧服务..."
    smart-router stop 2>/dev/null || true
fi

# 2. 尝试从系统 Python 卸载旧版本
if pip3 show smart-router &> /dev/null; then
    echo "  📦 发现系统 Python 中的旧版本，正在卸载..."
    pip3 uninstall -q -y smart-router 2>/dev/null || true
fi

# 3. 清理旧的单文件配置（V1/V2 的 smart-router.yaml）
if [ -f "$PROJECT_DIR/smart-router.yaml" ]; then
    echo "  🗑️  备份并移除旧的 V1/V2 配置文件..."
    mv "$PROJECT_DIR/smart-router.yaml" "$PROJECT_DIR/smart-router.yaml.backup.$(date +%Y%m%d)"
    echo "    已备份为: smart-router.yaml.backup.$(date +%Y%m%d)"
fi

# 4. 如果 ~/.smart-router 存在旧配置，备份并清理
CONFIG_DIR="$HOME/.smart-router"
if [ -d "$CONFIG_DIR" ]; then
    # 检查是否有 V3 配置文件
    if [ ! -f "$CONFIG_DIR/providers.yaml" ] && [ ! -f "$CONFIG_DIR/models.yaml" ]; then
        echo "  🗑️  发现旧数据目录，备份到 ~/.smart-router.backup..."
        rm -rf "$CONFIG_DIR.backup" 2>/dev/null || true
        mv "$CONFIG_DIR" "$CONFIG_DIR.backup.$(date +%Y%m%d)"
        mkdir -p "$CONFIG_DIR"
    fi
fi

# 5. 清理旧的虚拟环境（如果存在且损坏）
VENV_DIR="$PROJECT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    echo "  🗑️  清理旧虚拟环境..."
    rm -rf "$VENV_DIR"
fi

# ==================== 安装新版本 ====================

# 创建虚拟环境
echo "📦 创建虚拟环境..."
python3 -m venv "$VENV_DIR"

# 使用虚拟环境的 pip 安装
echo "📦 安装依赖到虚拟环境..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -q -e ".[dev]"

# 验证安装
echo "✅ 验证安装..."
"$VENV_DIR/bin/python" script/verify.py

# 生成默认配置
echo "📝 生成默认配置文件..."
"$VENV_DIR/bin/smart-router" init

echo ""
echo "✨ Smart Router V3 安装成功！"
echo ""
echo "📁 配置文件位置: ~/.smart-router/"
echo "   - providers.yaml   # 配置 API Key"
echo "   - models.yaml      # 模型能力配置"
echo "   - routing.yaml     # 路由策略配置"
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

# 检查是否有旧版本残留
if command -v smart-router &> /dev/null; then
    SYSTEM_SMR=$(which smart-router)
    if [[ "$SYSTEM_SMR" != *"venv"* ]]; then
        echo "⚠️  警告: 检测到系统中还有其他 smart-router 命令:"
        echo "   $SYSTEM_SMR"
        echo "   请使用 ./venv/bin/smr 运行命令，或手动清理系统中的旧版本"
        echo ""
    fi
fi
