#!/bin/bash
# Smart Router 一键安装脚本 (V3) - 可移植版本
# 将 venv 和代码安装到 ~/.smart-router/，支持复制到其他同平台机器使用

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

echo "🚀 正在安装 Smart Router (可移植版本)..."

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
if pip3 show smartRouter &> /dev/null; then
    echo "  📦 发现系统 Python 中的旧版本，正在卸载..."
    pip3 uninstall -q -y smartRouter 2>/dev/null || true
fi

# 3. 配置目录
INSTALL_DIR="$HOME/.smart-router"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$INSTALL_DIR/bin"

# 4. 如果 ~/.smart-router 存在旧配置，备份
if [ -d "$INSTALL_DIR" ]; then
    echo "  🗑️  备份旧安装目录..."
    rm -rf "$INSTALL_DIR.backup" 2>/dev/null || true
    mv "$INSTALL_DIR" "$INSTALL_DIR.backup.$(date +%Y%m%d)"
fi

# ==================== 安装新版本 ====================

# 创建目录结构
echo "📦 创建目录结构..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# 创建虚拟环境
echo "📦 创建虚拟环境..."
python3 -m venv "$VENV_DIR"

# 创建临时目录复制源码进行安装（与开发目录完全分离）
echo "📦 准备安装包..."
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# 复制项目文件到临时目录
cp -r "$PROJECT_DIR/core" "$TEMP_DIR/"
cp -r "$PROJECT_DIR/script" "$TEMP_DIR/"
cp -r "$PROJECT_DIR/config" "$TEMP_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/pyproject.toml" "$TEMP_DIR/"
cp "$PROJECT_DIR/README.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/LICENSE" "$TEMP_DIR/" 2>/dev/null || true

# 使用虚拟环境的 pip 安装（非 editable 模式）
echo "📦 安装 Smart Router 到虚拟环境..."
cd "$TEMP_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -q ".[dev]"

# 验证安装
echo "✅ 验证安装..."
"$VENV_DIR/bin/python" -c "
from smart_router.classifier import TaskClassifier
from smart_router.selector import ModelSelector
from smart_router.utils.markers import parse_markers, strip_markers
from smart_router.config.loader import ConfigLoader
print('✓ 所有模块导入成功')
"

# 生成默认配置
echo "📝 生成默认配置文件..."
"$VENV_DIR/bin/smart-router" init -f --output "$INSTALL_DIR"

# ==================== 创建可移植启动脚本 ====================

echo "🔗 创建可移植启动脚本..."

# 创建 smr 启动脚本（使用相对路径）
cat > "$BIN_DIR/smr" << 'EOF'
#!/bin/bash
# Smart Router 可移植启动脚本
# 自动检测脚本所在位置，使用相对路径启动

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$ROOT_DIR/venv"

# 检查虚拟环境是否存在
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ 错误: 未找到虚拟环境: $VENV_DIR"
    exit 1
fi

# 使用虚拟环境的 Python 运行 smr
exec "$VENV_DIR/bin/python" -m smart_router.cli "$@"
EOF

chmod +x "$BIN_DIR/smr"

# 创建 smart-router 启动脚本（同上）
cp "$BIN_DIR/smr" "$BIN_DIR/smart-router"

# ==================== 创建系统级命令链接 ====================

echo "🔗 创建系统级命令链接..."

# 检查是否有权限写入 /usr/local/bin
if [ -w "/usr/local/bin" ]; then
    # 创建 symlink 指向我们的启动脚本
    ln -sf "$BIN_DIR/smr" /usr/local/bin/smr
    ln -sf "$BIN_DIR/smart-router" /usr/local/bin/smart-router
    echo "  ✓ 已创建: /usr/local/bin/smr"
    echo "  ✓ 已创建: /usr/local/bin/smart-router"
else
    echo "  ⚠️  需要管理员权限来创建系统级命令"
    echo "  请运行以下命令手动创建："
    echo "    sudo ln -sf $BIN_DIR/smr /usr/local/bin/smr"
    echo "    sudo ln -sf $BIN_DIR/smart-router /usr/local/bin/smart-router"
    echo ""
    echo "  或添加到用户 PATH（推荐）："
    echo "    echo 'export PATH=\"\$HOME/.smart-router/bin:\$PATH\"' >> ~/.zshrc"
fi

echo ""
echo "✨ Smart Router V3 安装成功！"
echo ""
echo "📁 安装位置:"
echo "   $INSTALL_DIR/"
echo "   ├── bin/"
echo "   │   ├── smr              # 启动脚本（相对路径）"
echo "   │   └── smart-router     # 同上"
echo "   ├── venv/                # 虚拟环境"
echo "   ├── providers.yaml       # 配置文件"
echo "   ├── models.yaml"
echo "   └── routing.yaml"
echo ""
echo "📖 快速开始："
echo "   1. 编辑 ~/.smart-router/providers.yaml 配置 API Key"
echo "   2. 启动服务: smr start"
echo "   3. 查看状态: smr status"
echo ""
echo "🛠️  常用命令："
echo "   smr start     # 后台启动"
echo "   smr stop      # 停止服务"
echo "   smr status    # 查看状态"
echo "   smr logs      # 查看日志"
echo "   smr doctor    # 健康检查"
echo ""
echo "📦 可移植特性:"
echo "   此安装使用相对路径启动脚本，理论上可以复制使用"
echo "   复制方法: cp -r ~/.smart-router ~/new-location/"
echo ""
echo "   ⚠️  macOS 系统 Python 限制:"
echo "       由于 macOS 系统 Python 使用 Framework 结构，"
echo "       venv 中的 Python 包含指向原始位置的动态链接。"
echo "       如需完全可移植，请使用 Homebrew Python 或 PyInstaller"
echo ""
echo "🗑️  卸载方法："
echo "   rm -rf ~/.smart-router"
echo "   sudo rm -f /usr/local/bin/smart-router /usr/local/bin/smr"
echo ""
