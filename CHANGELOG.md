# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-04-19

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
