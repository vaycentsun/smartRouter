#!/bin/bash
# Smart Router 制作可移植版本脚本
# 生成可以使用相对路径运行的版本，便于复制到其他同平台机器

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

# 输出目录
OUTPUT_DIR="${1:-$HOME/.smart-router-portable}"
VENV_DIR="$OUTPUT_DIR/venv"

echo "🔧 制作 Smart Router 可移植版本..."
echo "   输出目录: $OUTPUT_DIR"

# ==================== 清理旧版本 ====================
if [ -d "$OUTPUT_DIR" ]; then
    echo "🧹 清理旧版本..."
    rm -rf "$OUTPUT_DIR"
fi

# ==================== 创建目录结构 ====================
mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/bin"

# ==================== 创建虚拟环境（使用 --copies）====================
echo "📦 创建虚拟环境（复制模式）..."
python3 -m venv --copies "$VENV_DIR"

# ==================== 安装 Smart Router ====================
echo "📦 安装 Smart Router..."

# 创建临时目录复制源码
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

cp -r "$PROJECT_DIR/src" "$TEMP_DIR/"
cp -r "$PROJECT_DIR/script" "$TEMP_DIR/"
cp -r "$PROJECT_DIR/config" "$TEMP_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/pyproject.toml" "$TEMP_DIR/"
cp "$PROJECT_DIR/README.md" "$TEMP_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/LICENSE" "$TEMP_DIR/" 2>/dev/null || true

cd "$TEMP_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -q ".[dev]"

# ==================== 生成配置文件 ====================
echo "📝 生成配置文件..."
"$VENV_DIR/bin/smart-router" init -f --output "$OUTPUT_DIR"

# ==================== 创建可移植启动脚本 ====================
echo "🔗 创建可移植启动脚本..."

# 创建 smr 启动脚本（使用相对路径）
cat > "$OUTPUT_DIR/bin/smr" << 'EOF'
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

chmod +x "$OUTPUT_DIR/bin/smr"

# 创建 smart-router 启动脚本（同上）
cp "$OUTPUT_DIR/bin/smr" "$OUTPUT_DIR/bin/smart-router"

# ==================== 修复 pyvenv.cfg ====================
echo "🔧 修复 pyvenv.cfg..."
# 创建新的 pyvenv.cfg，使用相对路径
PYTHON_VERSION=$("$VENV_DIR/bin/python" --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

cat > "$VENV_DIR/pyvenv.cfg" << EOF
home = ./bin
include-system-site-packages = false
version = $PYTHON_VERSION
executable = /usr/bin/python$PYTHON_MAJOR.$PYTHON_MINOR
command = /usr/bin/python$PYTHON_MAJOR -m venv --copies $VENV_DIR
EOF

# ==================== 完成提示 ====================
echo ""
echo "✅ 可移植版本制作完成！"
echo ""
echo "📁 输出目录: $OUTPUT_DIR"
echo ""
echo "📂 目录结构:"
echo "   $OUTPUT_DIR/"
echo "   ├── bin/"
echo "   │   ├── smr              # 启动脚本（相对路径）"
echo "   │   └── smart-router     # 同上"
echo "   ├── venv/                # 虚拟环境（包含 Python）"
echo "   ├── providers.yaml       # 配置文件"
echo "   ├── models.yaml"
echo "   └── routing.yaml"
echo ""
echo "🚀 使用方法:"
echo "   1. 复制整个目录到其他机器（同平台同架构）"
echo "   2. 运行: $OUTPUT_DIR/bin/smr start"
echo "   3. 或添加到 PATH: export PATH=\"$OUTPUT_DIR/bin:\$PATH\""
echo ""
echo "⚠️  注意: 此版本仅可在同平台同架构的机器上运行"
echo "   例如: macOS ARM → macOS ARM ✅"
echo "         macOS → Linux ❌"
echo ""
