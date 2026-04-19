#!/bin/bash
# Smart Router 远程一键安装脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/<user>/smartRouter/main/script/install-remote.sh | bash

set -e

REPO_URL="https://github.com/vaycentsun/smartRouter.git"
RAW_URL="https://raw.githubusercontent.com/vaycentsun/smartRouter/main"
INSTALL_DIR="$HOME/.smart-router"
BIN_DIR="$HOME/.local/bin"
PYTHON_MIN_VERSION="3.9"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warning() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查 Python 版本
check_python() {
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        error "未找到 Python，请先安装 Python ${PYTHON_MIN_VERSION}+"
        exit 1
    fi

    local version
    version=$($PYTHON_CMD --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    
    if [ "$(printf '%s\n' "$PYTHON_MIN_VERSION" "$version" | sort -V | head -n1)" != "$PYTHON_MIN_VERSION" ]; then
        error "需要 Python ${PYTHON_MIN_VERSION}+，当前版本: $version"
        exit 1
    fi
    
    success "Python 版本检查通过: $version"
}

# 检查 pip
check_pip() {
    if ! command_exists pip3 && ! command_exists pip; then
        error "未找到 pip，请先安装 pip"
        exit 1
    fi
    
    if command_exists pip3; then
        PIP_CMD="pip3"
    else
        PIP_CMD="pip"
    fi
}

# 创建目录
setup_directories() {
    info "创建安装目录..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    
    # 确保 BIN_DIR 在 PATH 中
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        warning "$BIN_DIR 不在 PATH 中"
        info "请将以下行添加到 ~/.bashrc 或 ~/.zshrc:"
        echo "    export PATH=\"$BIN_DIR:\$PATH\""
    fi
}

# 克隆仓库
clone_repo() {
    info "下载 Smart Router..."
    
    if [ -d "$INSTALL_DIR/repo" ]; then
        warning "检测到已存在的安装，正在更新..."
        cd "$INSTALL_DIR/repo"
        git pull --quiet
    else
        if ! command_exists git; then
            error "未找到 git，请先安装 git"
            exit 1
        fi
        git clone --depth 1 --quiet "$REPO_URL" "$INSTALL_DIR/repo"
        cd "$INSTALL_DIR/repo"
    fi
    
    success "代码下载完成"
}

# 安装 Python 包
install_package() {
    info "安装 Smart Router..."
    
    cd "$INSTALL_DIR/repo"
    $PIP_CMD install -q -e "."
    
    success "Smart Router 安装完成"
}

# 创建启动器
create_launcher() {
    info "创建启动器..."
    
    cat > "$BIN_DIR/smart-router" << 'EOF'
#!/bin/bash
# Smart Router 启动器

INSTALL_DIR="$HOME/.smart-router"
export SMART_ROUTER_HOME="$INSTALL_DIR"

# 执行实际的 smart-router 命令
exec "$(which python3)" -m smart_router.cli "$@"
EOF
    
    chmod +x "$BIN_DIR/smart-router"
    
    # 创建 smr 快捷方式
    ln -sf "$BIN_DIR/smart-router" "$BIN_DIR/smr"
    
    success "启动器创建完成"
}

# 生成默认配置
generate_config() {
    if [ ! -f "$INSTALL_DIR/smart-router.yaml" ]; then
        info "生成默认配置文件..."
        
        cat > "$INSTALL_DIR/smart-router.yaml" << 'EOF'
# Smart Router 配置文件
# 文档: https://github.com/vaycent/smartRouter/blob/main/docs/GUIDE.md

server:
  port: 4000
  host: "127.0.0.1"
  master_key: "sk-smart-router-local"

model_list:
  # ============================================================
  # OpenAI (默认 api_base: https://api.openai.com/v1)
  # ============================================================
  # - model_name: gpt-4o
  #   litellm_params:
  #     model: openai/gpt-4o
  #     api_key: os.environ/OPENAI_API_KEY
  #     # api_base: https://api.openai.com/v1  # 默认，可省略

  # - model_name: gpt-4o-mini
  #   litellm_params:
  #     model: openai/gpt-4o-mini
  #     api_key: os.environ/OPENAI_API_KEY
  #     # api_base: https://api.openai.com/v1  # 默认，可省略

  # ============================================================
  # Anthropic Claude (默认 api_base: https://api.anthropic.com)
  # ============================================================
  # - model_name: claude-3-sonnet
  #   litellm_params:
  #     model: anthropic/claude-3-5-sonnet-20241022
  #     api_key: os.environ/ANTHROPIC_API_KEY
  #     # api_base: https://api.anthropic.com  # 默认，可省略

  # ============================================================
  # DeepSeek (默认 api_base: https://api.deepseek.com/v1)
  # ============================================================
  # - model_name: deepseek-chat
  #   litellm_params:
  #     model: deepseek/deepseek-chat
  #     api_key: os.environ/DEEPSEEK_API_KEY
  #     # api_base: https://api.deepseek.com/v1  # 默认，可省略

  # ============================================================
  # 阿里 Qwen (默认 api_base: https://dashscope.aliyuncs.com/compatible-mode/v1)
  # ============================================================
  # - model_name: qwen-turbo
  #   litellm_params:
  #     model: dashscope/qwen-turbo
  #     api_key: os.environ/DASHSCOPE_API_KEY
  #     # api_base: https://dashscope.aliyuncs.com/compatible-mode/v1  # 默认，可省略

  # ============================================================
  # Moonshot Kimi (默认 api_base: https://api.moonshot.cn/v1)
  # ============================================================
  # - model_name: kimi-k2
  #   litellm_params:
  #     model: moonshot/moonshot-v1-8k
  #     api_key: os.environ/MOONSHOT_API_KEY
  #     # api_base: https://api.moonshot.cn/v1  # 默认，可省略

  # ============================================================
  # 智谱 GLM (OpenAI-compatible 格式，必须指定 api_base)
  # ============================================================
  # - model_name: glm-5
  #   litellm_params:
  #     model: openai/glm-5
  #     api_base: https://open.bigmodel.cn/api/paas/v4
  #     api_key: os.environ/ZHIPU_API_KEY

smart_router:
  default_strategy: auto

  stage_routing:
    code_review:
      easy: ["gpt-4o-mini"]
      medium: ["claude-3-sonnet"]
      hard: ["claude-3-opus"]
    writing:
      easy: ["gpt-4o-mini"]
      medium: ["gpt-4o"]
      hard: ["claude-3-opus"]
    reasoning:
      easy: ["gpt-4o-mini"]
      medium: ["gpt-4o"]
      hard: ["claude-3-opus"]
    brainstorming:
      easy: ["gpt-4o-mini"]
      medium: ["gpt-4o"]
      hard: ["claude-3-opus"]
    chat:
      easy: ["gpt-4o-mini"]
      medium: ["gpt-4o"]
      hard: ["claude-3-opus"]
EOF
        
        success "配置文件生成: $INSTALL_DIR/smart-router.yaml"
    else
        info "配置文件已存在，跳过生成"
    fi
}

# 验证安装
verify_installation() {
    info "验证安装..."
    
    if command -v smart-router >/dev/null 2>&1; then
        success "smart-router 命令可用"
    else
        warning "smart-router 命令暂时不可用，请重新加载 shell 或手动添加 $BIN_DIR 到 PATH"
    fi
    
    if command -v smr >/dev/null 2>&1; then
        success "smr 快捷命令可用"
    fi
}

# 打印完成信息
print_completion() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         Smart Router 安装成功！                        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "📁 安装目录: $INSTALL_DIR"
    echo "⚙️  配置文件: $INSTALL_DIR/smart-router.yaml"
    echo ""
    echo "🚀 快速开始:"
    echo ""
    echo "   1. 配置 API Key:"
    echo "      vim $INSTALL_DIR/smart-router.yaml"
    echo ""
    echo "   2. 设置环境变量（根据你的配置）:"
    echo "      export OPENAI_API_KEY='your-key'"
    echo "      export ANTHROPIC_API_KEY='your-key'"
    echo ""
    echo "   3. 启动服务:"
    echo "      smart-router start"
    echo ""
    echo "   4. 查看状态:"
    echo "      smart-router status"
    echo ""
    echo "📖 常用命令:"
    echo "   smart-router start     # 后台启动"
    echo "   smart-router stop      # 停止服务"
    echo "   smart-router status    # 查看状态"
    echo "   smart-router logs      # 查看日志"
    echo "   smart-router doctor    # 健康检查"
    echo ""
    echo "📚 文档: https://github.com/vaycent/smartRouter/blob/main/docs/GUIDE.md"
    echo ""
    
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo -e "${YELLOW}⚠️  重要提示:${NC}"
        echo "   $BIN_DIR 不在你的 PATH 中"
        echo "   请运行以下命令或将其添加到 ~/.bashrc / ~/.zshrc:"
        echo ""
        echo "   export PATH=\"$BIN_DIR:\$PATH\""
        echo ""
    fi
}

# 主函数
main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     Smart Router - 智能模型路由网关安装程序            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    check_python
    check_pip
    setup_directories
    clone_repo
    install_package
    create_launcher
    generate_config
    verify_installation
    print_completion
}

# 处理命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --uninstall)
            info "卸载 Smart Router..."
            rm -rf "$INSTALL_DIR"
            rm -f "$BIN_DIR/smart-router"
            rm -f "$BIN_DIR/smr"
            success "Smart Router 已卸载"
            exit 0
            ;;
        --help|-h)
            echo "Smart Router 安装脚本"
            echo ""
            echo "用法:"
            echo "  curl -fsSL $RAW_URL/script/install-remote.sh | bash"
            echo ""
            echo "选项:"
            echo "  --uninstall    卸载 Smart Router"
            echo "  --help, -h     显示帮助信息"
            exit 0
            ;;
        *)
            error "未知选项: $1"
            exit 1
            ;;
    esac
    shift
done

main
