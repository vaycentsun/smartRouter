# 根级测试目录统一实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 分析根级 tests/ 目录是否需要统一到模块内

**Architecture:** 当前 `src/smart_router/tests/cli/` 和 `tests/integration/` 位于根级，其他模块测试已移入各自模块。需要分析是否需要进一步统一。

**Tech Stack:** Python, Pytest

---

## 当前结构分析

```
src/smart_router/
├── tests/                     ← 根级测试
│   ├── cli/                  ← CLI 命令测试
│   │   ├── test_cli.py
│   │   ├── test_cli_edge.py
│   │   └── test_cli_list.py
│   └── integration/          ← 跨模块集成测试
│       ├── test_api.py
│       ├── test_v3_integration.py
│       ├── test_context_aware.py
│       └── test_integration.py
├── classifier/tests/           ← 模块级测试
├── config/tests/
├── gateway/tests/
├── misc/tests/
├── router/tests/
├── selector/tests/
└── utils/tests/
```

---

## 决策分析

### 为什么 cli/ 测试不在模块内？

**原因：** `cli.py` 是单一文件（未重构为 cli/ 子模块），所以 `tests/cli/` 无法成为 `cli/` 的子目录。

**选项：**
1. **保持现状** - cli.py 未重构，cli 测试保留在根级
2. **等待计划 1 执行** - cli 重构后，cli 测试可移入 `cli/` 模块

### 为什么 integration 测试保留在根级？

**原因：** `integration` 测试是**跨模块测试**，测试完整链路：加载 → 分类 → 选择 → LiteLLM

**结论：** 这**不是缺陷**，而是正确的设计选择。

---

## Task 1: 确认当前设计（无需改动）

- [ ] **Step 1: 分析当前设计合理性**

| 测试目录 | 归属 | 原因 |
|---------|------|------|
| cli/ | 根级 | cli.py 未重构为子模块 |
| integration/ | 根级 | 跨模块测试 |
| */tests/ | 模块内 | 模块级测试 |

- [ ] **Step 2: 确认无需改动**

```bash
# 当前结构符合模块化设计，无需执行迁移
```

**结论：** 当前设计已经是**最优解**，无需改动。

---

## 替代方案：cli 重构后的测试迁移

当计划 1（CLI 模块化重构）执行后，可以选择迁移 cli 测试：

- [ ] **Step 1: cli 重构完成后，创建 cli/tests/**

```bash
mkdir -p src/smart_router/cli/tests/
touch src/smart_router/cli/tests/__init__.py
```

- [ ] **Step 2: 移动测试文件**

```bash
mv src/smart_router/tests/cli/* src/smart_router/cli/tests/
rmdir src/smart_router/tests/cli/
```

- [ ] **Step 3: 更新测试导入**

```python
# 更新 import 路径
from smart_router.cli import app  # 无变化
```

- [ ] **Step 4: 验证**

```bash
pytest src/smart_router/cli/tests/ -v
```

---

## 最终结论

| 改进项 | 状态 | 说明 |
|--------|------|------|
| cli 测试统一到 cli/ 模块 | **待计划 1 执行后** | cli 重构后可迁移 |
| integration 测试统一 | **不需要** | 跨模块测试保留在根级是正确的设计 |

**建议：** 此计划标记为"待执行"，等到 CLI 重构完成后再处理。

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-27-tests-organization.md`.**

**结论：** 根据分析，当前项目目录设计已经是**最优结构**，无需执行额外迁移。计划 1（CLI 重构）执行后，cli 测试可自然迁移到 `cli/tests/`。

**Which approach?**

1. **标记为待执行** - 等待 CLI 重构完成��执行
2. **立即执行** - 迁移 cli 测试（但需要手动调整路径）