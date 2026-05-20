#!/bin/bash
set -e

# Smart Router Docker 启动脚本
# 同时启动 Proxy 服务（4000端口）和 Dashboard（8080端口）

echo "🚀 Starting Smart Router services..."

# 检查配置文件是否存在，缺失时自动生成默认配置
CONFIG_DIR="/app/config"
NEED_INIT=false

if [ ! -f "$CONFIG_DIR/providers.yaml" ]; then
    NEED_INIT=true
fi
if [ ! -d "$CONFIG_DIR/models" ]; then
    NEED_INIT=true
fi
if [ ! -f "$CONFIG_DIR/routing.yaml" ]; then
    NEED_INIT=true
fi

if [ "$NEED_INIT" = true ]; then
    echo "⚠️  配置文件缺失，正在生成默认配置到 $CONFIG_DIR ..."
    smart-router init --safe --output "$CONFIG_DIR"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  重要提示"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "默认配置已生成，但 API Key 为空。"
    echo "请通过环境变量设置 API Key，或将本地配置目录挂载到容器："
    echo ""
    echo "  docker run -v /本地配置路径:/app/config ..."
    echo ""
    echo "服务将继续启动，但模型调用会因缺少 API Key 而失败。"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi

# 启动 Proxy 服务（后台）
smart-router start --foreground --config "$CONFIG_DIR" &
PROXY_PID=$!
echo "✓ Proxy service started (PID: $PROXY_PID) on port 4000"

# 等待 Proxy 服务就绪
sleep 3

# 启动 Dashboard（前台）
echo "✓ Starting Dashboard on port 8080..."
exec smart-router dashboard --foreground --host 0.0.0.0 --port 8080
