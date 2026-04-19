# Smart Router 发布检查清单

## ✅ 发布前必须完成的事项

### 1. 账号准备

- [ ] 注册 [PyPI](https://pypi.org/account/register/) 账号
- [ ] 在 PyPI 上启用双因素认证 (2FA)
- [ ] 创建 PyPI API Token
- [ ] （可选）注册 [TestPyPI](https://test.pypi.org/account/register/) 用于测试

### 2. 项目信息配置

- [ ] 更新 `pyproject.toml` 中的作者信息
  ```toml
  authors = [
      {name = "你的姓名", email = "your.email@example.com"},
  ]
  ```

- [ ] 更新所有脚本中的 GitHub 用户名
  - `script/install-remote.sh`: 将 `vaycent` 改为你的用户名
  - `homebrew/smart-router.rb`: 更新所有 URL
  - `docs/RELEASE.md`: 更新所有 URL
  - `README.md`: 更新 curl 命令中的 URL

### 3. GitHub 仓库设置

- [ ] 将代码推送到 GitHub
- [ ] 确保仓库是公开的（Private 仓库无法使用 GitHub Raw）
- [ ] 在 Settings → Secrets → Actions 中添加 `PYPI_API_TOKEN`

## 🚀 首次发布步骤

### 第 1 步：本地测试

```bash
# 1. 测试本地安装
./script/install.sh

# 2. 运行测试
pytest tests/ -v

# 3. 验证 CLI 工作
smart-router --version
smart-router doctor
```

### 第 2 步：发布到 PyPI

```bash
# 1. 安装构建工具
pip install build twine

# 2. 构建包
python -m build

# 3. 检查包
twine check dist/*

# 4. （可选）先发布到 TestPyPI 测试
twine upload --repository testpypi dist/*

# 5. 从 TestPyPI 安装测试
pip install --index-url https://test.pypi.org/simple/ smart-router

# 6. 正式发布到 PyPI
twine upload dist/*
```

### 第 3 步：GitHub Release（自动）

```bash
# 1. 提交所有更改
git add .
git commit -m "Prepare for v0.1.0 release"

# 2. 创建 tag
git tag -a v0.1.0 -m "Release version 0.1.0"

# 3. 推送
git push origin main
git push origin v0.1.0

# 4. GitHub Actions 会自动：
#    - 发布到 PyPI
#    - 创建 GitHub Release
#    - 上传构建产物
```

### 第 4 步：验证 curl 安装

确保 `script/install-remote.sh` 已推送到 main 分支后：

```bash
# 测试 curl 安装（在干净环境中）
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/smartRouter/main/script/install-remote.sh | bash
```

### 第 5 步：（可选）Homebrew

如果需要 Homebrew 支持：

1. **选项 A**：在当前仓库维护 Formula
   - 用户通过 `brew install vaycent/smartRouter/smart-router` 安装

2. **选项 B**：创建单独的 Tap 仓库
   ```bash
   # 创建新仓库 homebrew-smart-router
   # 将 homebrew/smart-router.rb 复制过去
   # 用户通过 brew tap vaycent/smart-router 安装
   ```

## 📋 发布后验证清单

### PyPI 安装测试
```bash
pip uninstall smart-router -y
pip install smart-router
smart-router --version
```

### curl 安装测试
```bash
# 卸载旧版本
rm -rf ~/.smart-router
rm -f ~/.local/bin/smart-router
rm -f ~/.local/bin/smr

# 测试安装
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/smartRouter/main/script/install-remote.sh | bash

# 测试卸载
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/smartRouter/main/script/install-remote.sh | bash -s -- --uninstall
```

### GitHub Release 检查
- [ ] 访问 `https://github.com/YOUR_USERNAME/smartRouter/releases`
- [ ] 确认 Release 已创建
- [ ] 确认构建产物已上传 (wheel 和 tar.gz)

## 🔄 后续版本更新流程

```bash
# 1. 更新版本号
vim pyproject.toml
# version = "0.2.0"

# 2. 更新 CHANGELOG.md
vim CHANGELOG.md

# 3. 提交更改
git add .
git commit -m "Bump version to v0.2.0"

# 4. 创建新 tag
git tag -a v0.2.0 -m "Release version 0.2.0"

# 5. 推送
git push origin main
git push origin v0.2.0

# 6. 等待 GitHub Actions 完成
```

## 📚 用户安装命令（发布后可用）

在你的 README 中展示以下安装方式：

### pip 安装（推荐）
```bash
pip install smart-router
```

### curl 一键安装
```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/smartRouter/main/script/install-remote.sh | bash
```

### Homebrew（macOS/Linux）
```bash
brew tap YOUR_USERNAME/smart-router
brew install smart-router
```

## ⚠️ 注意事项

1. **GitHub 用户名**：确保将所有 `vaycent` 替换为你的 GitHub 用户名
2. **版本号**：遵循语义化版本 (SemVer)：MAJOR.MINOR.PATCH
3. **Python 版本**：确保 `install-remote.sh` 中的 Python 版本要求与 `pyproject.toml` 一致
4. **依赖包**：如果添加新依赖，记得更新 `homebrew/smart-router.rb`

## 🆘 故障排除

| 问题 | 解决方案 |
|------|---------|
| PyPI 上传失败 | 检查 API Token，确认版本号不重复 |
| curl 安装失败 | 检查 GitHub raw URL，确保仓库公开 |
| GitHub Actions 失败 | 检查 Secrets 设置，查看 Actions 日志 |
| Homebrew 安装失败 | 更新 Formula 中的 SHA256 |
