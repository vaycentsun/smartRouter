# 目录架构重构：src/smart_router 模块分组优化

**日期**: 2026-04-23  
**状态**: 待实施  
**优先级**: 低（纯组织性重构，不影响功能）

---

## 动机

当前 `src/smart_router/` 根目录包含 14 个条目，其中多个 `.py` 文件直接平铺在根级，缺乏按职责分组的子模块结构。虽然已有 `classifier/`、`config/`、`selector/`、`utils/` 等子模块，但服务层和路由核心层的文件仍散落在根目录，不利于后续扩展和维护。

### 当前结构问题

1. **职责混合**：服务运行（server/daemon）与路由逻辑（plugin）平级放置，难以一眼区分层次
2. **根目录膨胀**：随着功能增加，根级 `.py` 文件会持续增多
3. **coffee_qr.py 定位不清**：运营性质功能不应和核心代码并列

---

## 目标结构

```
src/smart_router/
├── __init__.py
│
├── cli.py                    # 保留根级：CLI 入口，项目门面
│
├── gateway/                  # ← 新增：服务运行层
│   ├── __init__.py
│   ├── server.py             # FastAPI 前台服务 + middleware 逻辑
│   ├── server_main.py        # 后台服务入口（argparse）
│   └── daemon.py             # PID 文件、进程启动/停止/状态管理
│
├── router/                   # ← 新增：路由核心层
│   ├── __init__.py
│   ├── plugin.py             # SmartRouter V3 主插件（继承 LiteLLM Router）
│   └── plugin_v3_adapter.py  # V3 配置适配器（备用路径）
│
├── classifier/               # 保留：任务分类器
├── config/                   # 保留：配置系统
├── selector/                 # 保留：模型选择器
├── utils/                    # 保留：工具函数
│
├── assets/                   # 保留：静态资源
├── templates/                # 保留：配置模板
└── misc/                     # ← 新增：非核心杂项
    ├── __init__.py
    └── coffee_qr.py          # 赞助二维码（运营功能）
```

---

## 变更明细

### 移动文件

| 源路径 | 目标路径 | 说明 |
|--------|----------|------|
| `server.py` | `gateway/server.py` | 服务运行层 |
| `server_main.py` | `gateway/server_main.py` | 后台服务入口 |
| `daemon.py` | `gateway/daemon.py` | 进程管理 |
| `plugin.py` | `router/plugin.py` | V3 路由插件 |
| `plugin_v3_adapter.py` | `router/plugin_v3_adapter.py` | V3 适配器 |
| `coffee_qr.py` | `misc/coffee_qr.py` | 运营功能 |

### 新增文件

- `gateway/__init__.py`
- `router/__init__.py`
- `misc/__init__.py`

### 需要更新导入的模块

以下文件的相对/绝对导入路径需要同步修改：

| 受影响文件 | 变更内容 |
|-----------|---------|
| `cli.py` | `from .server import ...` → `from .gateway.server import ...` |
| `cli.py` | `from .daemon import ...` → `from .gateway.daemon import ...` |
| `cli.py` | `from .plugin import ...` → `from .router.plugin import ...` |
| `cli.py` | `from .coffee_qr import ...` → `from .misc.coffee_qr import ...` |
| `server.py` → `gateway/server.py` | 所有 `from .plugin import ...` → `from ..router.plugin import ...` |
| `server_main.py` → `gateway/server_main.py` | 导入路径更新 |
| `daemon.py` → `gateway/daemon.py` | 导入路径更新（如有） |
| `plugin.py` → `router/plugin.py` | 所有内部导入路径更新 |

---

## 实施步骤

1. **创建新目录和 `__init__.py`**：`gateway/`、`router/`、`misc/`
2. **移动文件**：按上表迁移，不修改内容
3. **批量替换导入路径**：全局搜索替换所有受影响的 import 语句
4. **运行全量测试**：`pytest tests/ -v`，确保 244 个测试全部通过
5. **检查 CLI 命令**：验证 `smr doctor`、`smr dry-run`、`smr list` 等命令正常

---

## 风险评估

- **风险等级**: 低
- **影响范围**: 仅内部导入路径，无 API/行为变更
- **回滚方案**: git revert
- **测试覆盖**: 全量 244 个单元测试 + 集成测试可完全验证
