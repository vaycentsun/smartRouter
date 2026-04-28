# src → core 目录重命名执行计划

## 背景

为配合未来前端 H5 工程（`frontend/`）的引入，现有 Python CLI 工程源码目录 `src/` 重命名为 `core/`，以形成清晰的 **core（核心引擎）vs frontend（展示层）** 语义边界。

## 影响范围确认

### 必须修改（构建/分发依赖）

| # | 文件 | 修改内容 | 说明 |
|---|------|---------|------|
| 1 | `pyproject.toml` | `tool.hatch.build.targets.wheel.packages = ["core/smart_router"]` | hatchling 打包入口 |
| 1 | `pyproject.toml` | `tool.hatch.build.targets.sdist.include = ["/core", ...]` | sdist 包含目录 |
| 1 | `pyproject.toml` | `include = ["core/smart_router/templates/*.yaml"]` | 模板文件通配 |
| 1 | `pyproject.toml` | `testpaths = ["core"]` | pytest 测试发现路径 |
| 2 | `script/install-remote.sh` | 第 165 行 URL 路径：`/main/core/smart_router/templates/${filename}` | curl 安装脚本模板下载 |
| 3 | `script/download-config.py` | 第 37 行 URL 路径：`${repo_url}/core/smart_router/templates/${filename}` | Python 配置下载脚本 |

### 建议同步更新（文档一致性）

| # | 文件 | 修改内容 |
|---|------|---------|
| 4 | `AGENTS.md` | 源码结构树中 `src/` → `core/`；测试命令示例路径 |
| 5 | `README.md` | 源码路径引用（如 `src/smart_router/cli.py` → `core/smart_router/cli.py`） |
| 6 | `docs/PUBLISH_CHECKLIST.md` | `src/smart_router/__init__.py` → `core/smart_router/__init__.py` |

### 无需修改（运行时天然解耦）

- **Python 源码内部**：grep 确认零处硬编码 `src/`，`importlib.resources` 加载模板与源码目录名无关
- **`.github/workflows/publish.yml`**：CI 无硬编码 `src/`，通过 hatchling 构建
- **已发布 PyPI wheel**：对已安装用户零影响

### 历史文档建议保留原样

- `docs/superpowers/plans/` 下的历史设计文档含有大量 `src/` 路径，建议保留原样以维持历史代码对照，可在文档顶部加注释说明目录已迁移。

---

## 执行步骤

### Step 1: 重命名目录

```bash
# 在项目根目录执行
git mv src/ core/
```

### Step 2: 修改构建配置（pyproject.toml）

将以下 4 处 `src` 替换为 `core`：

```toml
# 1. wheel packages
tool.hatch.build.targets.wheel.packages = ["core/smart_router"]

# 2. sdist include
tool.hatch.build.targets.sdist.include = ["/core", "/config", "/docs", "/script", "/README.md", "/LICENSE"]

# 3. wheel 包含模板
tool.hatch.build.targets.wheel.include = ["core/smart_router/templates/*.yaml"]

# 4. pytest testpaths
tool.pytest.ini_options.testpaths = ["core"]
```

### Step 3: 修改安装脚本

**`script/install-remote.sh`**（第 165 行）：
```bash
# 改前
local url="https://raw.githubusercontent.com/${REPO}/main/src/smart_router/templates/${filename}"
# 改后
local url="https://raw.githubusercontent.com/${REPO}/main/core/smart_router/templates/${filename}"
```

**`script/download-config.py`**（第 37 行）：
```python
# 改前
url = f"{repo_url}/src/smart_router/templates/{filename}"
# 改后
url = f"{repo_url}/core/smart_router/templates/{filename}"
```

### Step 4: 修改文档

- **`AGENTS.md`**：搜索并替换 `src/` → `core/`（仅限源码结构描述和命令示例，历史引用可保留）
- **`README.md`**：搜索并替换源码路径引用
- **`docs/PUBLISH_CHECKLIST.md`**：更新版本同步路径

### Step 5: 验证构建

```bash
# 1. 验证 hatchling 能正确打包
python -m build

# 2. 验证 pytest 能发现测试
pytest -v --collect-only | head -n 20

# 3. 验证 wheel 内模板文件存在
unzip -l dist/smartrouter-*.whl | grep templates/

# 4. 验证安装后 CLI 可用
pip install dist/smartrouter-*.whl
smart-router --version
smr doctor
```

### Step 6: 提交

```bash
git add -A
git commit -m "refactor: rename src/ to core/ for frontend monorepo preparation

- Rename src/ → core/ to establish core vs frontend boundary
- Update pyproject.toml hatchling and pytest paths
- Update install-remote.sh and download-config.py raw URLs
- Sync AGENTS.md, README.md, and PUBLISH_CHECKLIST.md"
```

---

## 风险与回滚

| 风险 | 缓解措施 |
|------|---------|
| 遗漏某处 `src/` 引用 | 执行前全局 grep `src/` 复查；CI 构建会自动暴露 hatchling 配置错误 |
| 外部链接 404 | 这是任何目录重构的固有风险，无法避免；README 中的链接需同步更新 |
| 历史计划文档与代码不一致 | 保留历史文档原样，加注释说明 |

**回滚方案**：
```bash
git revert HEAD  # 若提交后发现问题，可直接 revert
```

---

## 下一步（前端工程启动时）

完成本次 rename 后，未来引入前端工程时的目录结构将直接就绪：

```
lucky-falcon/
├── core/                          # 重命名后的 Python CLI 核心引擎
│   └── smart_router/
├── frontend/                      # 未来：Node.js + TypeScript H5 工程
├── pyproject.toml
├── package.json                   # 可选：pnpm workspaces 根配置
├── Makefile                       # 统一构建
└── ...
```

无需再动目录骨架，前端工程可直接在 `frontend/` 下初始化。
