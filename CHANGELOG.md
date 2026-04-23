# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.9] - 2026-04-23

### Changed
- Bump version to 1.0.9

## [1.0.7] - 2026-04-23

### Fixed
- 修复 PyPI 包名不一致问题：`pyproject.toml` 中的 `name` 从 `smart-router` 改为 `smartRouter`，与 PyPI 实际发布的包名保持一致
- 同步更新所有文档、脚本和 CI 配置中的 pip 安装命令：`pip install smartRouter` / `pip uninstall smartRouter`
- 同步更新版本号到 1.0.7（`__init__.py`、`cli.py`）

## [1.0.5] - 2026-04-23

### Fixed
- 修复 GitHub Actions workflow 中错误的 action commit SHA 引用
- 将 action 版本引用改为语义化标签（@v4, @v5），解决 CI 构建失败

## [1.0.4] - 2026-04-23

### Fixed
- 修复 GitHub Actions 组织权限策略导致的 action 不可用问题

## [1.0.3] - 2026-04-22

### Added
- 新增 artifact attestation 构建来源验证
- 新增 Homebrew Formula 自动更新流程
- 新增 SHA256 checksums 生成与验证

### Changed
- 重构 publish.yml 支持安全全平台分发（PyPI + Homebrew + curl + checksums + attestation）

## [1.0.2] - (日期待定)

### Added / Changed / Fixed
（待补充）

## [1.0.1] - (日期待定)

### Added / Changed / Fixed
（待补充）

## [1.0.0] - (日期待定)

### Added / Changed / Fixed
（待补充）

## [0.1.1] - 2026-04-19

### Added

- Coffee sponsor command (`smr coffee`) with QR code display
- ASCII art mode for QR code display (no image dependency)
- Support for custom sponsor links (Alipay, WeChat, GitHub Sponsors)
- Default sponsor link: GitHub Sponsors

### Changed

- `coffee_qr.py` module refactored into `misc/coffee_qr.py`
- QR code asset moved to `assets/coffee_qr.png`

## [0.1.0] - 2026-04-18

### Added
- Initial release of Smart Router
- Unified OpenAI API interface for multiple LLM providers
- Intelligent task classification (L1 Rule Engine + L2 Embedding)
- Stage markers for explicit routing control (`[stage:code_review]`)
- Four routing strategies: auto, speed, cost, quality
- Automatic fallback on model failure
- CLI commands: start, stop, restart, status, logs, dry-run, validate, doctor
- Configuration file support (YAML)
- Support for OpenAI, Anthropic, DeepSeek, Qwen, Kimi, MiniMax, GLM

[Unreleased]: https://github.com/vaycent/smartRouter/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/vaycent/smartRouter/releases/tag/v0.1.0
