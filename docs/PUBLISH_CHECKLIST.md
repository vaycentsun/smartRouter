# Smart Router 发布检查清单

## 发布前必须完成的事项

### 1. 账号准备

- [ ] 注册 [PyPI](https://pypi.org/account/register/) 账号
- [ ] 在 PyPI 上启用双因素认证 (2FA)
- [ ] 创建 PyPI API Token
- [ ] （可选）注册 [TestPyPI](https://test.pypi.org/account/register/) 用于测试

### 2. GitHub 仓库设置

- [ ] 将代码推送到 GitHub
- [ ] 确保仓库是公开的
- [ ] 在 Settings → Secrets → Actions 中添加 `PYPI_API_TOKEN`

### 3. 更新版本号

```bash
# 更新 pyproject.toml
vim pyproject.toml  # version = "0.2.0"

# 同步更新 core/smart_router/__init__.py 和 cli.py
```

---

## 发布方式

### 方式一：PyPI + pip（推荐）

```bash
# 构建包
python -m build

# 检查包
twine check dist/*

# 上传到 PyPI
twine upload dist/*
```

自动发布：创建 Git tag 后 GitHub Actions 会自动构建并发布到 PyPI。

### 方式二：GitHub Releases

```bash
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin main
git push origin v0.2.0
```

GitHub Actions 会自动创建 Release 并上传构建产物。

### 方式三：curl 一键安装

确保 `script/install-remote.sh` 已推送到 main 分支：

```bash
curl -fsSL https://raw.githubusercontent.com/vaycent/smartRouter/main/script/install-remote.sh | bash
```

### 方式四：Homebrew（macOS/Linux）

```bash
brew tap vaycentsun/smart-router https://github.com/vaycentsun/smartRouter.git
brew install smart-router
```

> **自动更新**：GitHub Actions 会在发布到 PyPI 后自动更新 `smart-router.rb` 中的版本号和 SHA256，无需手动操作。

---

## 同步更新机制

打 tag 后，GitHub Actions 会自动完成以下同步：

| 分发方式 | 更新方式 | 是否自动 |
|---------|---------|---------|
| **pip (PyPI)** | GitHub Actions 构建并上传 | 是 |
| **curl** | 脚本从 main 分支实时获取 | 是（无需额外操作） |
| **Homebrew** | GitHub Actions 自动更新 Formula | 是 |

**操作流程**：
1. 更新版本号（`pyproject.toml`、`__init__.py`、`cli.py`）
2. 提交并推送代码到 main 分支
3. 打 tag：`git tag -a v1.0.3 -m "Release v1.0.3"`
4. 推送 tag：`git push origin v1.0.3`
5. GitHub Actions 自动完成所有分发渠道的更新

---

## 发布后验证

### PyPI 安装测试

```bash
pip install smartRouter
smart-router --version
```

### curl 安装测试

```bash
rm -rf ~/.smart-router
rm -f ~/.local/bin/smart-router
rm -f ~/.local/bin/smr
curl -fsSL https://raw.githubusercontent.com/vaycent/smartRouter/main/script/install-remote.sh | bash
```

### GitHub Release 检查

访问 `https://github.com/vaycent/smartRouter/releases` 确认 Release 已创建。

---

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| PyPI 上传失败 | 检查 API Token，确认版本号不重复 |
| curl 安装失败 | 检查 GitHub raw URL，确保仓库公开 |
| GitHub Actions 失败 | 检查 Secrets 设置，查看 Actions 日志 |
| Homebrew 安装失败 | 确认 GitHub Actions 中 `update-homebrew-formula` job 是否成功；检查 `smart-router.rb` 中的版本号是否与 tag 一致 |