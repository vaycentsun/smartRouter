#!/bin/bash
# Smart Router 远程安装脚本
# 使用方法: curl -sSL https://raw.githubusercontent.com/vaycentsun/smartRouter/main/script/install-remote.sh | bash
#
# 这个脚本用于:
# 1. 从 GitHub 源码安装最新版 smart-router
# 2. 下载默认配置文件到 ~/.smart-router

set -e

REPO_RAW_URL="https://raw.githubusercontent.com/vaycentsun/smartRouter/main"
CONFIG_DIR="$HOME/.smart-router"

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

# ==================== 安装 smart-router ====================
echo ""
echo "📦 从 GitHub 安装最新版 smart-router..."

REPO_URL="https://github.com/vaycentsun/smartRouter.git"

# 检查是否已安装，如果是则升级
if pip3 show smart-router &> /dev/null; then
    echo "  发现已安装的 smart-router，正在升级..."
    pip3 install -q --force-reinstall --no-deps "git+${REPO_URL}#egg=smart-router[dev]"
    echo "✓ smart-router 升级成功"
else
    pip3 install -q "git+${REPO_URL}#egg=smart-router[dev]"
    echo "✓ smart-router 安装成功"
fi

# ==================== 创建配置目录 ====================
echo ""
echo "📁 创建配置目录: $CONFIG_DIR"
mkdir -p "$CONFIG_DIR"

# ==================== 下载配置文件 ====================
echo ""
echo "⬇️  下载配置文件..."

download_config() {
    local filename=$1
    # Use templates directory as source for configuration templates
    local url="$REPO_RAW_URL/src/smart_router/templates/$filename"
    local output="$CONFIG_DIR/$filename"
    
    if curl -fsSL "$url" -o "$output" 2>/dev/null; then
        echo "  ✓ 下载成功: $filename"
        return 0
    else
        echo "  ✗ 下载失败: $filename"
        return 1
    fi
}

# 如果配置文件已存在，先备份
backup_existing_configs() {
    local needs_backup=false
    for file in providers.yaml models.yaml routing.yaml; do
        if [ -f "$CONFIG_DIR/$file" ]; then
            needs_backup=true
            break
        fi
    done
    
    if [ "$needs_backup" = true ]; then
        local backup_dir="$CONFIG_DIR.backup.$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        cp "$CONFIG_DIR"/*.yaml "$backup_dir/" 2>/dev/null || true
        echo "  📦 已备份旧配置到: $backup_dir"
    fi
}

# 备份现有配置
backup_existing_configs

# 下载三个配置文件
download_config "providers.yaml"
download_config "models.yaml"
download_config "routing.yaml"

# 如果 GitHub 下载失败，回退到 smart-router init 生成默认配置
github_failed=false
for file in providers.yaml models.yaml routing.yaml; do
    if [ ! -f "$CONFIG_DIR/$file" ]; then
        github_failed=true
        break
    fi
done

if [ "$github_failed" = true ] && command -v smart-router &> /dev/null; then
    echo ""
    echo "⚠️  GitHub 下载不完整，尝试使用 smart-router init 生成默认配置..."
    smart-router init -f --output "$CONFIG_DIR"
fi

# ==================== 验证安装 ====================
echo ""
echo "🔍 验证安装..."

if command -v smart-router &> /dev/null; then
    version=$(smart-router version --short 2>/dev/null || echo "未知")
    echo "✓ smart-router 版本: $version"
else
    echo "⚠️  smart-router 命令未找到，可能需要手动添加 PATH"
fi

# 检查配置文件
config_count=0
for file in providers.yaml models.yaml routing.yaml; do
    if [ -f "$CONFIG_DIR/$file" ]; then
        ((config_count++))
    fi
done

if [ $config_count -eq 3 ]; then
    echo "✓ 配置文件完整 ($config_count/3)"
else
    echo "⚠️ 配置文件不完整 ($config_count/3)"
    echo "  请运行: smart-router init"
fi

# ==================== 完成提示 ====================
echo ""
echo "✨ 安装完成！"
echo ""
echo "📁 配置文件位置: $CONFIG_DIR"
echo "   - providers.yaml   # API Key 配置"
echo "   - models.yaml      # 模型能力配置"
echo "   - routing.yaml     # 路由策略配置"
echo ""
echo "📝 下一步:"
echo "   1. 编辑 $CONFIG_DIR/providers.yaml 配置你的 API Key"
echo "   2. 启动服务: smart-router start"
echo "   3. 查看状态: smart-router status"
echo ""
echo "📖 常用命令:"
echo "   smart-router start     # 后台启动服务"
echo "   smart-router stop      # 停止服务"
echo "   smart-router status    # 查看状态"
echo "   smart-router doctor    # 健康检查"
echo ""
