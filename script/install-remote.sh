#!/bin/bash
# Smart Router 安全远程安装脚本
# 从 GitHub Release 下载版本化包并校验 SHA256，支持 pip / Homebrew / curl 全平台安装
#
# 一键安装最新版:
#   curl -fsSL https://raw.githubusercontent.com/vaycentsun/smartRouter/main/script/install-remote.sh | bash
#
# 从 Git 源码安装（开发版）:
#   curl -fsSL ... | bash -s -- --dev

set -euo pipefail

REPO="vaycentsun/smartRouter"
GITHUB_API="https://api.github.com/repos/${REPO}"
CONFIG_DIR="${HOME}/.smart-router"
INSTALL_METHOD="release"  # release 或 git

# ==================== 参数解析 ====================
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev|--git)
            INSTALL_METHOD="git"
            shift
            ;;
        --version)
            TARGET_VERSION="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--dev|--git] [--version VERSION]"
            echo ""
            echo "Options:"
            echo "  --dev, --git      从 Git 源码安装最新开发版（不校验 SHA256）"
            echo "  --version VERSION 安装指定版本（默认：最新 release）"
            echo "  --help, -h        显示此帮助"
            exit 0
            ;;
        *)
            echo "❌ 未知参数: $1"
            exit 1
            ;;
    esac
done

echo "🚀 Smart Router 远程安装脚本"
echo ""

# ==================== 检查 Python 环境 ====================
echo "📋 检查 Python 环境..."

if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python 3.9+"
    exit 1
fi

python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ 需要 Python 3.9+，当前版本: $python_version"
    exit 1
fi

echo "✓ Python 版本: $python_version"

# ==================== Release 安装模式 ====================
if [ "$INSTALL_METHOD" == "release" ]; then
    echo ""
    echo "📦 从 GitHub Release 安装..."

    # 获取版本号
    if [ -z "${TARGET_VERSION:-}" ]; then
        echo "  查询最新 release 版本..."
        LATEST_RELEASE=$(curl -fsSL "${GITHUB_API}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
        if [ -z "$LATEST_RELEASE" ]; then
            echo "❌ 无法获取最新版本号"
            exit 1
        fi
        TARGET_VERSION="$LATEST_RELEASE"
    fi

    echo "  目标版本: v${TARGET_VERSION}"

    # 创建临时目录
    TMPDIR=$(mktemp -d)
    trap 'rm -rf "$TMPDIR"' EXIT

    # 下载 sdist 和 checksums
    RELEASE_URL="https://github.com/${REPO}/releases/download/v${TARGET_VERSION}"
    SDIST_FILE="smartrouter-${TARGET_VERSION}.tar.gz"
    SDIST_URL="${RELEASE_URL}/${SDIST_FILE}"
    CHECKSUM_URL="${RELEASE_URL}/checksums.sha256"

    echo "  下载 ${SDIST_FILE}..."
    curl -fsSL "${SDIST_URL}" -o "${TMPDIR}/${SDIST_FILE}"

    echo "  下载 checksums.sha256..."
    curl -fsSL "${CHECKSUM_URL}" -o "${TMPDIR}/checksums.sha256"

    # 校验 SHA256
    echo "  校验 SHA256..."
    EXPECTED_SHA=$(grep "${SDIST_FILE}" "${TMPDIR}/checksums.sha256" | awk '{print $1}')
    ACTUAL_SHA=$(sha256sum "${TMPDIR}/${SDIST_FILE}" | awk '{print $1}')

    if [ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]; then
        echo "❌ SHA256 校验失败！"
        echo "  期望: ${EXPECTED_SHA}"
        echo "  实际: ${ACTUAL_SHA}"
        echo "  文件可能已被篡改，安装已中止。"
        exit 1
    fi

    echo "✓ SHA256 校验通过 (${ACTUAL_SHA})"

    # 安装
    echo "  安装 smart-router..."
    pip3 install -q "${TMPDIR}/${SDIST_FILE}"
    echo "✓ smart-router v${TARGET_VERSION} 安装成功"

# ==================== Git 开发版安装模式 ====================
elif [ "$INSTALL_METHOD" == "git" ]; then
    echo ""
    echo "📦 从 Git 源码安装开发版..."
    REPO_URL="https://github.com/${REPO}.git"

    if pip3 show smartRouter &> /dev/null; then
        echo "  发现已安装的 smartRouter，正在升级..."
        pip3 install -q --force-reinstall --no-deps "git+${REPO_URL}#egg=smartRouter[dev]"
    else
        pip3 install -q "git+${REPO_URL}#egg=smartRouter[dev]"
    fi
    echo "✓ 开发版安装成功"
fi

# ==================== 创建配置目录 ====================
echo ""
echo "📁 创建配置目录: ${CONFIG_DIR}"
mkdir -p "${CONFIG_DIR}"

# ==================== 下载配置文件 ====================
echo ""
echo "⬇️  下载配置文件..."

backup_existing_configs() {
    local needs_backup=false
    for file in providers.yaml models.yaml routing.yaml; do
        if [ -f "${CONFIG_DIR}/${file}" ]; then
            needs_backup=true
            break
        fi
    done

    if [ "$needs_backup" = true ]; then
        local backup_dir="${CONFIG_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        cp "${CONFIG_DIR}"/*.yaml "$backup_dir/" 2>/dev/null || true
        echo "  📦 已备份旧配置到: ${backup_dir}"
    fi
}

backup_existing_configs

download_config() {
    local filename=$1
    local url="https://raw.githubusercontent.com/${REPO}/main/src/smart_router/templates/${filename}"
    local output="${CONFIG_DIR}/${filename}"

    if curl -fsSL "$url" -o "$output" 2>/dev/null; then
        echo "  ✓ 下载成功: ${filename}"
        return 0
    else
        echo "  ✗ 下载失败: ${filename}"
        return 1
    fi
}

download_config "providers.yaml"
download_config "models.yaml"
download_config "routing.yaml"

# 如果 GitHub 下载失败，回退到 smart-router init 生成默认配置
github_failed=false
for file in providers.yaml models.yaml routing.yaml; do
    if [ ! -f "${CONFIG_DIR}/${file}" ]; then
        github_failed=true
        break
    fi
done

if [ "$github_failed" = true ] && command -v smart-router &> /dev/null; then
    echo ""
    echo "⚠️  GitHub 下载不完整，尝试使用 smart-router init 生成默认配置..."
    smart-router init -f --output "${CONFIG_DIR}"
fi

# ==================== 验证安装 ====================
echo ""
echo "🔍 验证安装..."

if command -v smart-router &> /dev/null; then
    version=$(smart-router version --short 2>/dev/null || echo "未知")
    echo "✓ smart-router 版本: ${version}"
else
    echo "⚠️  smart-router 命令未找到，可能需要手动添加 PATH"
fi

config_count=0
for file in providers.yaml models.yaml routing.yaml; do
    if [ -f "${CONFIG_DIR}/${file}" ]; then
        ((config_count++))
    fi
done

if [ $config_count -eq 3 ]; then
    echo "✓ 配置文件完整 (${config_count}/3)"
else
    echo "⚠️ 配置文件不完整 (${config_count}/3)"
    echo "  请运行: smart-router init"
fi

# ==================== 完成提示 ====================
echo ""
echo "✨ 安装完成！"
echo ""
echo "📁 配置文件位置: ${CONFIG_DIR}"
echo "   - providers.yaml   # API Key 配置"
echo "   - models.yaml      # 模型能力配置"
echo "   - routing.yaml     # 路由策略配置"
echo ""
echo "📝 下一步:"
echo "   1. 编辑 ${CONFIG_DIR}/providers.yaml 配置你的 API Key"
echo "   2. 启动服务: smart-router start"
echo "   3. 查看状态: smart-router status"
echo ""
echo "📖 常用命令:"
echo "   smart-router start     # 后台启动服务"
echo "   smart-router stop      # 停止服务"
echo "   smart-router status    # 查看状态"
echo "   smart-router doctor    # 健康检查"
echo ""
