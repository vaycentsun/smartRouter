#!/bin/bash
set -e

# Smart Router Docker 启动脚本
# 同时启动 Proxy 服务（4000端口）和 Dashboard（8080端口）

echo "🚀 Starting Smart Router services..."

# 启动 Proxy 服务（后台）
smart-router start --foreground --config /app/config &
PROXY_PID=$!
echo "✓ Proxy service started (PID: $PROXY_PID) on port 4000"

# 等待 Proxy 服务就绪
sleep 3

# 启动 Dashboard（前台）
echo "✓ Starting Dashboard on port 8080..."
exec smart-router dashboard --foreground --host 0.0.0.0 --port 8080
