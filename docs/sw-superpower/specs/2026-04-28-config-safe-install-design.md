# Smart Router 配置文件安全安装设计文档

> 版本: 1.0  
> 日期: 2026-04-28  
> 作者: OpenCode  
> 状态: 已审批

---

## 背景与目标

用户通过 `install.sh`、`install-remote.sh`、`brew install`、`pip install` 四种方式安装 Smart Router 时，本地已有的 `providers.yaml`、`models.yaml`、`routing.yaml` 三个配置文件**不应被覆盖**。

唯一允许覆盖配置文件的场景是：用户**显式执行** `smr init`（不带 `--safe` 时默认询问确认，`--force` 时强制覆盖）。

对于全新安装（本地尚无配置文件），各安装方式仍应**自动补齐缺失的默认配置**。

---

## 当前行为分析

| 安装方式 | 当前配置处理逻辑 | 问题 |
|---|---|---|
| `install.sh` | 第 41–44 行把 **整个** `~/.smart-router` 备份并删除，然后执行 `smart-router init -f` 强制覆盖 | 用户配置必然丢失 |
| `install-remote.sh` | 先备份已有 yaml，然后**无条件下载**三个 yaml 覆盖，最后再 `init -f` fallback | 用户配置必然丢失 |
| `brew install` | 仅安装 Python 包，不触碰配置文件 | ✅ 符合要求 |
| `pip install` | 仅安装 Python 包，不触碰配置文件 | ✅ 符合要求 |
| `smr init` | 默认询问是否覆盖；`--force` 强制覆盖 | ✅ 行为合理 |

---

## 方案概述

核心思路：**CLI 新增 `--safe` 参数**，语义为"只生成缺失的配置文件，已有文件完全不动、不提示、不覆盖"。

安装脚本统一使用 `smart-router init --safe` 来补齐缺失配置，从而避免覆盖用户已有配置。

---

## 详细设计

### 1. CLI 改动：`smart-router init --safe`

#### 参数定义

```python
force: bool = typer.Option(False, "--force", "-f", help="强制覆盖已存在的配置文件")
safe: bool = typer.Option(False, "--safe", help="安全模式：只生成缺失的配置文件，不覆盖已有文件")
```

#### 行为矩阵

| 已有配置 | 无参数 | `--safe` | `--force` | `--safe` + `--force` |
|---|---|---|---|---|
| 全部缺失 | 生成全部，无提示 | 生成全部，无提示 | 生成全部，无提示 | 生成全部，无提示 |
| 部分存在 | 提示是否覆盖存在的 | **仅生成缺失的**，无提示 | 强制覆盖全部 | `--safe` 优先，**仅生成缺失的** |
| 全部存在 | 提示是否覆盖 | **不生成、不覆盖、无提示** | 强制覆盖全部 | `--safe` 优先，**不生成、不覆盖、无提示** |

> 注意：`--safe` 和 `--force` 同时存在时，`--safe` 优先。

### 2. `install.sh` 改动

- 不再备份并删除整个 `~/.smart-router`，改为仅备份目录，然后只删除 `venv` 和 `bin`。
- 配置生成改为 `smart-router init --safe`。

### 3. `install-remote.sh` 改动

- `download_config` 增加已存在跳过逻辑。
- 移除 `backup_existing_configs` 函数。
- Fallback 使用 `init --safe`。

### 4. `brew install` / `pip install`

无需改动。

---

## 测试策略

- `test_init_safe_creates_missing`：部分文件存在，`--safe` 只生成缺失的。
- `test_init_safe_skips_existing`：三文件全存在，`--safe` 跳过。
- `test_init_safe_priority_over_force`：`--safe --force` 同时传入，`--safe` 优先。
- `test_init_safe_all_missing`：全新目录，`--safe` 正常生成三文件。

---

## 兼容性影响

| 维度 | 影响 |
|---|---|
| 现有 `smr init` 用户 | 无影响。默认行为不变。 |
| `install.sh` 新用户 | 首次安装体验不变；重装时配置不再丢失。 |
| `install-remote.sh` 新用户 | 同上。 |
| `brew install` / `pip install` | 无改动，无影响。 |
