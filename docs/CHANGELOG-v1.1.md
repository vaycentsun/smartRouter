# Smart Router v1.1 更新日志

**发布日期**: 2025-04-19

---

## 🎉 新功能

### ☕ Coffee 赞助命令

新增 `coffee` 命令，支持作者并显示赞助二维码：

```bash
# 显示赞助二维码
smr coffee

# ASCII 艺术模式
smr coffee --ascii

# 自定义赞助链接
smr coffee --link "https://your-sponsor-link"
```

**功能特点**:
- 🎨 美观的终端界面（使用 Rich 库）
- 📱 支持显示二维码图片
- 🖼️ ASCII 艺术模式（无需图片依赖）
- 🔗 支持自定义赞助链接
- 💚 支持支付宝、微信、GitHub Sponsors 等多种方式

**文件变更**:
- 新增: `src/smart_router/coffee_qr.py` - 二维码生成模块
- 新增: `src/smart_router/assets/coffee_qr.png` - 示例二维码
- 更新: `src/smart_router/cli.py` - 添加 coffee 命令
- 新增: `docs/COFFEE_SPONSOR.md` - 赞助说明文档

---

## 📋 v1.0 基础功能回顾

### 已配置模型 (11个)
- ✅ **Kimi** (kimi-k2) - 已验证
- ✅ **MiniMax** (minimax-m2) - 已验证
- ⏸️ OpenAI 系列 (环境变量配置)
- ⏸️ Claude 系列 (环境变量配置)
- ⏸️ DeepSeek 系列 (环境变量配置)
- ⏸️ Qwen 系列 (环境变量配置)
- ⏸️ GLM (环境变量配置)

### 核心功能
- 🎯 5 种任务类型自动路由
- 📝 Stage Marker 精确控制
- ⚡ 4 种策略模式 (auto/speed/cost/quality)
- 🔄 Fallback 降级机制
- 🔍 正则规则自动分类

---

## 🚀 快速开始

```bash
# 安装
./script/install.sh

# 启动服务
smr start

# 测试路由
smr dry-run "帮我 review 这段代码"

# 显示赞助二维码
smr coffee
```

---

## 📁 文件结构

```
smartRouter/
├── config/
│   └── smart-router.yaml          # 配置模板
├── docs/
│   ├── GUIDE.md                   # 使用指南
│   ├── ROUTING_GUIDE.md           # 路由策略详解
│   ├── COFFEE_SPONSOR.md          # 赞助说明 ⭐ NEW
│   └── FILE_ORGANIZATION.md       # 文件组织规范
├── src/smart_router/
│   ├── cli.py                     # CLI 入口
│   ├── coffee_qr.py               # 二维码模块 ⭐ NEW
│   └── assets/
│       └── coffee_qr.png          # 示例二维码 ⭐ NEW
└── smart-router.yaml              # 运行时配置
```

---

## 💡 使用提示

1. **配置 API Key**: 编辑 `smart-router.yaml` 配置您的 API Key
2. **自定义二维码**: 替换 `src/smart_router/assets/coffee_qr.png` 为您自己的收款码
3. **查看路由**: 使用 `smr dry-run "测试文本"` 预览路由决策

---

**版本**: v1.1 | **状态**: ✅ 已发布

☕ 感谢每一位支持者！
