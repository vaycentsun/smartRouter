# Smart Router 文件组织规范

## 📂 推荐目录结构

```
smartRouter/
├── config/                          # 配置目录
│   └── examples/                    # V3 配置示例
│       ├── v3/
│       │   ├── providers.yaml       # 服务商配置示例
│       │   ├── models.yaml          # 模型配置示例
│       │   └── routing.yaml         # 路由策略示例
│       ├── minimal.yaml             # 最小化配置（V2 遗留）
│       └── multi-provider.yaml      # 多服务商配置（V2 遗留）
│
├── docs/                            # 文档目录
│   ├── GUIDE.md                     # 使用指南
│   ├── ROUTING_GUIDE.md             # 路由策略详解
│   └── FILE_ORGANIZATION.md         # 文件组织规范
│
├── src/                             # 源码
│   └── smart_router/
│       └── ...
│
├── tests/                           # 测试
├── script/                          # 脚本
├── README.md                        # 项目 README
└── .smart-router/                   # 用户运行时配置目录（~/.smart-router）
    ├── providers.yaml               # API 服务商连接配置
    ├── models.yaml                  # 模型能力声明配置
    ├── routing.yaml                 # 路由策略配置
    ├── smart-router.pid             # 服务进程 PID 文件
    └── smart-router.log             # 服务日志文件
```

---

## 📄 文件职责说明

### 1. `~/.smart-router/`（用户配置目录）

**职责**: 运行时配置目录

**特点**:
- `smart-router init` 默认生成的配置位置
- 包含真实的 API Key 等敏感信息
- **不应提交到 Git**

**使用场景**:
```bash
# 初始化配置到默认目录
smart-router init

# 启动服务（自动读取 ~/.smart-router/）
smart-router start

# 或在当前目录运行（自动查找当前目录配置）
cd projects/my-app
smart-router start  # 会使用当前目录的 providers.yaml / models.yaml / routing.yaml
```

---

### 2. `config/examples/v3/`

**职责**: V3 三文件配置示例

**特点**:
- 项目维护的默认配置示例
- 作为新用户的起点参考
- **可以提交到 Git**

**文件说明**:
- `providers.yaml` — API 服务商连接配置（OpenAI、Anthropic、DeepSeek 等）
- `models.yaml` — 模型能力声明配置（质量评分、支持任务、难度等级）
- `routing.yaml` — 路由策略配置（阶段路由表、分类规则、Fallback 链）

**使用场景**:
```bash
# 查看配置示例
cat config/examples/v3/providers.yaml
```

---

### 3. `docs/ROUTING_GUIDE.md`

**职责**: 路由策略使用文档

**内容**:
- 如何配置路由策略
- stage_routing 详解
- classification_rules 编写指南
- 最佳实践

---

## 🔄 文件关系图

```
用户操作                          文件变化
─────────────────────────────────────────────────────────
1. 安装项目
   └── 获取 config/examples/v3/（示例）

2. smart-router init
   └── 生成 ~/.smart-router/providers.yaml
   └── 生成 ~/.smart-router/models.yaml
   └── 生成 ~/.smart-router/routing.yaml
   └── 用户编辑 API Key 等配置

3. smart-router start
   └── 读取 ~/.smart-router/ 下的三文件（运行时配置）

4. 日常开发
   └── 修改 ~/.smart-router/*.yaml（本地配置）
   └── 项目升级时对比 config/examples/v3/（模板更新）
```

---

## 📝 Git 管理建议

### 应该提交到 Git 的文件

```gitignore
# config/ 目录下的示例配置
config/examples/                   ✅ 提交
docs/**/*.md                       ✅ 提交
src/                               ✅ 提交
tests/                             ✅ 提交
```

### 不应提交到 Git 的文件

```gitignore
# 用户运行时配置目录（包含 API Key）
/.smart-router/                    ❌ 忽略
/smart-router.yaml                 ❌ 忽略（V2 遗留）

# 虚拟环境
venv/                              ❌ 忽略

# 日志和临时文件
*.log
__pycache__/
```

---

## 🎯 推荐操作

### 初始化配置

```bash
# 生成默认 V3 配置到 ~/.smart-router/
smart-router init

# 或生成到指定目录
smart-router init --output ./my-config
```

### 使用自定义配置目录启动

```bash
# 使用指定目录的配置启动
smart-router start --config ./my-config
```

---

## 💡 总结

| 文件/目录 | 位置 | 是否提交 Git | 用途 |
|-----------|------|--------------|------|
| `~/.smart-router/` | 用户主目录 | ❌ 否 | 运行时配置（含 API Key） |
| `config/examples/v3/` | config/ | ✅ 是 | V3 配置示例 |
| `*.md` 文档 | docs/ | ✅ 是 | 项目文档 |
