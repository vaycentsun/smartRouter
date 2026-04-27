.PHONY: build build-web test install clean dev-web dev-core

# 前端依赖安装（仅当 package-lock.json 更新时重新执行）
frontend/node_modules/.package-lock.json: frontend/package-lock.json
	cd frontend && npm ci
	@touch frontend/node_modules/.package-lock.json

# 前端开发服务器
dev-web: frontend/node_modules/.package-lock.json
	cd frontend && npm run dev

# Python 开发安装
dev-core:
	pip3 install -e ".[dev]"

# 前端构建并嵌入 Python 包
build-web: frontend/node_modules/.package-lock.json
	cd frontend && npm run build
	rm -rf core/smart_router/web/static
	mkdir -p core/smart_router/web/static
	cp -r frontend/dist/* core/smart_router/web/static/

# Python 包构建（含前端产物）
build: build-web
	python3 -m build

# 测试
test:
	pytest -v

# 安装
install:
	pip3 install -e ".[dev]"

# 清理
clean:
	rm -rf frontend/dist core/smart_router/web/static dist/
