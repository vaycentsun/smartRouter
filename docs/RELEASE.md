# Smart Router 发布指南

本文档介绍如何将 Smart Router 发布到公开领域，让其他用户可以通过各种方式安装。

## 📋 发布前准备

1. **注册 PyPI 账号**
   - 访问 https://pypi.org/account/register/
   - 启用双因素认证 (2FA)
   - 创建 API Token

2. **配置 GitHub Secrets**（用于自动发布）
   - 进入仓库 Settings → Secrets and variables → Actions
   - 添加 `PYPI_API_TOKEN`

3. **更新版本号**
   ```bash
   # 编辑 pyproject.toml 和 homebrew/smart-router.rb
   version = "0.1.0"  # 更新为新版本
   ```

## 🚀 发布方式

### 方式一：PyPI + pip（推荐）

这是最标准的 Python 包分发方式。

**用户安装命令：**
```bash
pip install smart-router
```

**发布步骤：**

1. **手动发布**
   ```bash
   # 安装构建工具
   pip install build twine
   
   # 构建包
   python -m build
   
   # 检查包
   twine check dist/*
   
   # 上传到 PyPI
   twine upload dist/*
   ```

2. **自动发布（推荐）**
   ```bashn   # 创建 Git tag
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   
   # GitHub Actions 会自动构建并发布到 PyPI
   ```

### 方式二：GitHub Raw + curl（最简单）

适合让用户快速体验，无需依赖 pip。

**用户安装命令：**
```bash
curl -fsSL https://raw.githubusercontent.com/vaycent/smartRouter/main/script/install-remote.sh | bash
```

**卸载命令：**
```bash
curl -fsSL https://raw.githubusercontent.com/vaycent/smartRouter/main/script/install-remote.sh | bash -s -- --uninstall
```

**发布步骤：**
1. 将 `script/install-remote.sh` 推送到 main 分支
2. 确保脚本中的 `REPO_URL` 和 `RAW_URL` 正确
3. 用户即可通过 curl 安装

### 方式三：Homebrew（macOS/Linux）

适合 macOS 用户，提供更原生的体验。

**用户安装命令：**
```bash
brew tap vaycent/smart-router
brew install smart-router
```

**发布步骤：**

1. **创建 Homebrew Tap 仓库**
   ```bash
   # 创建新的 GitHub 仓库: homebrew-smart-router
   # 或使用当前仓库作为 Tap
   ```

2. **更新 Formula**
   ```bash
   # 计算新版本的 SHA256
   curl -sL https://github.com/vaycent/smartRouter/archive/refs/tags/v0.1.0.tar.gz | shasum -a 256
   
   # 更新 homebrew/smart-router.rb 中的 url 和 sha256
   ```

3. **推送到 Tap 仓库**
   ```bash
   git add homebrew/smart-router.rb
   git commit -m "Update smart-router to v0.1.0"
   git push
   ```

### 方式四：GitHub Releases

适合分发二进制文件或提供离线安装包。

**发布步骤：**

1. 创建 Git tag 并推送
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

2. GitHub Actions 会自动：
   - 构建 wheel 和 sdist
   - 创建 GitHub Release
   - 上传构建产物

3. 用户可以从 Releases 页面下载安装
   ```bash
   pip install https://github.com/vaycent/smartRouter/releases/download/v0.1.0/smart_router-0.1.0-py3-none-any.whl
   ```

## 📦 完整发布流程

### 首次发布

```bash
# 1. 确保所有代码已提交
git add .
git commit -m "Prepare for v0.1.0 release"

# 2. 创建 tag
git tag -a v0.1.0 -m "Release version 0.1.0"

# 3. 推送到 GitHub
git push origin main
git push origin v0.1.0

# 4. GitHub Actions 自动发布到 PyPI 和 GitHub Releases
```

### 后续版本更新

```bash
# 1. 更新版本号
vim pyproject.toml  # 更新 version
vim homebrew/smart-router.rb  # 更新 url 和 sha256

# 2. 提交更改
git add .
git commit -m "Bump version to v0.2.0"

# 3. 创建新 tag
git tag -a v0.2.0 -m "Release version 0.2.0"

# 4. 推送
git push origin main
git push origin v0.2.0
```

## 📝 更新 README

发布后在 README.md 中添加安装说明：

```markdown
## 🚀 安装

### 方式一：pip 安装（推荐）

```bash
pip install smart-router
```

### 方式二：curl 一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/vaycent/smartRouter/main/script/install-remote.sh | bash
```

### 方式三：Homebrew（macOS/Linux）

```bash
brew tap vaycent/smart-router
brew install smart-router
```
```

## ✅ 发布后验证

1. **验证 PyPI 发布**
   ```bash
   pip install smart-router
   smart-router --version
   ```

2. **验证 curl 安装**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/vaycent/smartRouter/main/script/install-remote.sh | bash
   ```

3. **验证 Homebrew 安装**
   ```bash
   brew tap vaycent/smart-router
   brew install smart-router
   ```

## 🐛 常见问题

### PyPI 上传失败
- 检查 API Token 是否正确设置
- 确认版本号没有重复
- 运行 `twine check dist/*` 检查包完整性

### curl 安装失败
- 检查 `install-remote.sh` 是否有执行权限
- 确认 GitHub raw URL 正确
- 检查用户是否有 Python 3.9+

### Homebrew 安装失败
- 更新 Formula 中的 SHA256
- 确保所有依赖包的 URL 和 SHA256 正确
- 运行 `brew install --debug ./homebrew/smart-router.rb` 调试

## 📚 相关链接

- [PyPI](https://pypi.org/project/smart-router/)
- [GitHub Releases](https://github.com/vaycent/smartRouter/releases)
- [Homebrew Tap](https://github.com/vaycent/homebrew-smart-router)（如果需要单独创建）
