# Smart Router 文件组织规范

## 📂 推荐目录结构

```
smartRouter/
├── config/                          # 配置目录
│   ├── smart-router.yaml           # ⭐ 默认配置模板（项目自带）
│   └── examples/                   # 配置示例
│       ├── smart-router.minimal.yaml      # 最小化配置
│       └── smart-router.full.yaml         # 完整配置示例
│
├── docs/                           # 文档目录
│   ├── GUIDE.md                   # 使用指南
│   ├── ROUTING_GUIDE.md           # 路由策略详解
│   └── CONFIG_REFERENCE.md        # 配置参考手册
│
├── src/                           # 源码
│   └── smart_router/
│       └── ...
│
├── tests/                         # 测试
├── script/                        # 脚本
├── README.md                      # 项目 README
└── smart-router.yaml             # ⚠️ 用户工作目录配置（运行时读取）
```

---

## 📄 文件职责说明

### 1. `smart-router.yaml`（根目录）

**职责**: 当前工作目录的运行时配置

**特点**:
- Smart Router 启动时默认查找的配置文件
- 向上递归查找（可以在任意子目录运行）
- 包含真实的 API Key 等敏感信息
- **不应提交到 Git**

**使用场景**: 
```bash
# 在项目根目录运行
smart-router start

# 或在子目录运行（会自动找到根目录的配置）
cd projects/my-app
smart-router start  # 会使用 smartRouter/smart-router.yaml
```

---

### 2. `config/smart-router.yaml`

**职责**: 默认配置模板（项目自带）

**特点**:
- 项目维护的默认配置模板
- 运行 `smart-router init` 时会复制到当前目录
- 作为新用户的起点配置
- **可以提交到 Git**

**使用场景**:
```bash
# 生成新的配置文件
smart-router init  # 复制 config/smart-router.yaml 到当前目录
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
   └── 获取 config/smart-router.yaml（模板）

2. smart-router init
   └── 复制 config/smart-router.yaml → ./smart-router.yaml
   └── 用户编辑 API Key 等配置

3. smart-router start
   └── 读取 ./smart-router.yaml（运行时配置）

4. 日常开发
   └── 修改 ./smart-router.yaml（本地配置）
   └── 项目升级时对比 config/smart-router.yaml（模板更新）
```

---

## ⚠️ 当前问题与解决方案

### 问题 1: 根目录文件过多

**当前状态**:
```
smartRouter/
├── smart-router.yaml           # ✅ 运行时配置
├── smart-router-guide.yaml     # ❌ 应删除或合并
├── ROUTING_GUIDE.md            # ⚠️ 应移入 docs/
├── VERSION-v1.0.md             # ⚠️ 应移入 docs/versions/
├── QUICKSTART-v1.0.md          # ⚠️ 应移入 docs/versions/
└── ...
```

**解决方案**:
```bash
# 1. 删除重复/临时的 guide 文件
rm smart-router-guide.yaml  # 内容已合并到 ROUTING_GUIDE.md

# 2. 移动文档到 docs 目录
mv ROUTING_GUIDE.md docs/
mv VERSION-v1.0.md docs/versions/
mv QUICKSTART-v1.0.md docs/versions/

# 3. 保留根目录的 smart-router.yaml（运行时配置）
# 4. 保留 config/smart-router.yaml（模板）
```

---

## 📝 Git 管理建议

### 应该提交到 Git 的文件

```gitignore
# config/ 目录下的模板配置
config/smart-router.yaml           ✅ 提交
config/examples/*.yaml             ✅ 提交

# 文档
docs/**/*.md                       ✅ 提交

# 源码、测试等
src/                               ✅ 提交
tests/                             ✅ 提交
```

### 不应提交到 Git 的文件

```gitignore
# 根目录的运行时配置（包含 API Key）
/smart-router.yaml                 ❌ 忽略

# 虚拟环境
venv/                              ❌ 忽略

# 日志和临时文件
*.log
__pycache__/
```

---

## 🎯 推荐操作

### 立即执行（清理当前混乱）

```bash
# 1. 删除临时的 guide yaml（内容已包含在 ROUTING_GUIDE.md 中）
rm smart-router-guide.yaml

# 2. 创建 docs/versions/ 目录并移动版本文档
mkdir -p docs/versions
mv VERSION-v1.0.md docs/versions/
mv QUICKSTART-v1.0.md docs/versions/

# 3. 移动路由指南到 docs
mv ROUTING_GUIDE.md docs/

# 4. 更新 .gitignore，忽略根目录的配置文件
echo "/smart-router.yaml" >> .gitignore

# 5. 确保 config/smart-router.yaml 是最新的模板
cp smart-router.yaml config/smart-router.yaml
```

### 清理后的目录结构

```
smartRouter/
├── config/
│   ├── smart-router.yaml          # 配置模板
│   └── examples/                  # 配置示例
├── docs/
│   ├── GUIDE.md
│   ├── ROUTING_GUIDE.md           # 路由指南（从根目录移入）
│   └── versions/
│       ├── VERSION-v1.0.md
│       └── QUICKSTART-v1.0.md
├── src/
├── tests/
├── smart-router.yaml              # 运行时配置（本地使用，不提交）
└── .gitignore                     # 忽略 /smart-router.yaml
```

---

## 💡 总结

| 文件 | 位置 | 是否提交 Git | 用途 |
|------|------|--------------|------|
| `smart-router.yaml` | 根目录 | ❌ 否 | 运行时配置（含 API Key） |
| `config/smart-router.yaml` | config/ | ✅ 是 | 配置模板 |
| `*.md` 文档 | docs/ | ✅ 是 | 项目文档 |
| `*-guide.yaml` | - | 🗑️ 删除 | 临时文件，已合并 |
