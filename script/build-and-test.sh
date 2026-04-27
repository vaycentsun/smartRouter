#!/bin/bash
# Smart Router 本地构建测试流水线
# 功能：环境检查 → 清理 → 测试 → 构建前端 → 构建 Python → 安装 → 验证 Dashboard

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_step() {
    echo -e "\n${YELLOW}Step $1/8: $2${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

echo "🚀 Smart Router 本地构建测试流水线"
echo "===================================="

# Step 1: 环境检查
log_step "1" "环境检查"
if ! command -v node &> /dev/null; then
    log_error "Node.js 未安装"
    exit 1
fi
if ! command -v python3 &> /dev/null; then
    log_error "Python3 未安装"
    exit 1
fi
echo "  Node.js: $(node --version)"
echo "  Python: $(python3 --version)"
log_success "环境检查通过"

# Step 2: 清理
log_step "2" "清理旧产物"
make clean
log_success "清理完成"

# Step 3: 运行测试
log_step "3" "运行 Python 测试"
pytest -v --tb=short
log_success "Python 测试通过"

# Step 4: 构建前端
log_step "4" "构建前端"
cd frontend
npm install
npm run build
cd ..
log_success "前端构建完成"

# Step 5: 嵌入 Python 包
log_step "5" "嵌入前端产物到 Python 包"
make build-web
log_success "前端产物已嵌入"

# Step 6: 构建 Python 包
log_step "6" "构建 Python 包"
python3 -m build
log_success "Python 包构建完成"

# Step 7: 本地安装
log_step "7" "本地安装"
pip3 install dist/smartrouter-*.whl --force-reinstall
log_success "安装完成"

# Step 8: 验证（含 Dashboard Smoke Test）
log_step "8" "验证安装"
VERSION=$(smart-router version --short 2>/dev/null || echo "unknown")
echo "  CLI 版本: $VERSION"

# 检查 Dashboard 前端是否存在
STATIC_DIR="$REPO_ROOT/core/smart_router/web/static"
if [ -f "$STATIC_DIR/index.html" ]; then
    echo "  Dashboard 前端: 已嵌入"
else
    log_error "Dashboard 前端未找到"
    exit 1
fi

# Smoke Test：启动 Dashboard 并验证可访问
log_step "8.1" "Dashboard Smoke Test"
echo "  启动 Dashboard..."
smart-router dashboard &
DASHBOARD_PID=$!
sleep 2

if curl -fsSL http://127.0.0.1:8080 > /dev/null 2>&1; then
    echo "  Dashboard 可访问: http://127.0.0.1:8080"
    log_success "Smoke Test 通过"
else
    log_error "Dashboard 无法访问"
    kill $DASHBOARD_PID 2>/dev/null || true
    exit 1
fi

kill $DASHBOARD_PID 2>/dev/null || true
sleep 1

echo -e "\n${GREEN}====================================${NC}"
echo -e "${GREEN}✅ 构建验证完成！${NC}"
echo ""
echo -e "${BLUE}📦 产物位置:${NC}"
echo "  Python wheel: dist/smartrouter-*.whl"
echo "  前端产物:     frontend/dist/"
echo ""
echo -e "${BLUE}🚀 使用方式:${NC}"
echo "  1. 启动 Dashboard:  smart-router dashboard"
echo "  2. 安装到系统:      ./script/install.sh"
echo "  3. 发布到 PyPI:     git tag v1.x.x && git push origin v1.x.x"
