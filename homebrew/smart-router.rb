# Homebrew Formula for Smart Router
# Usage: brew tap vaycent/smart-router https://github.com/vaycent/smartRouter
#        brew install smart-router

class SmartRouter < Formula
  include Language::Python::Virtualenv

  desc "Intelligent model routing gateway based on LiteLLM"
  homepage "https://github.com/vaycentsun/smartRouter"
  url "https://github.com/vaycentsun/smartRouter/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.11"

  resource "litellm" do
    url "https://files.pythonhosted.org/packages/litellm/litellm-1.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "typer" do
    url "https://files.pythonhosted.org/packages/typer/typer-0.12.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/pydantic/pydantic-2.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/pyyaml/pyyaml-6.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/rich/rich-13.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources
    
    # 生成默认配置
    (etc/"smart-router").mkpath
    (etc/"smart-router/smart-router.yaml").write config_file_content
  end

  def config_file_content
    <<~EOS
      # Smart Router 配置文件
      # 文档: https://github.com/vaycentsun/smartRouter/blob/main/docs/GUIDE.md

      server:
        port: 4000
        host: "127.0.0.1"
        master_key: "sk-smart-router-local"

      model_list: []

      smart_router:
        default_strategy: auto
        stage_routing:
          code_review:
            easy: ["gpt-4o-mini"]
            medium: ["claude-3-sonnet"]
            hard: ["claude-3-opus"]
          writing:
            easy: ["gpt-4o-mini"]
            medium: ["gpt-4o"]
            hard: ["claude-3-opus"]
          reasoning:
            easy: ["gpt-4o-mini"]
            medium: ["gpt-4o"]
            hard: ["claude-3-opus"]
          brainstorming:
            easy: ["gpt-4o-mini"]
            medium: ["gpt-4o"]
            hard: ["claude-3-opus"]
          chat:
            easy: ["gpt-4o-mini"]
            medium: ["gpt-4o"]
            hard: ["claude-3-opus"]
    EOS
  end

  def caveats
    <<~EOS
      Smart Router 已安装！

      配置文件位置: #{etc}/smart-router/smart-router.yaml
      
      快速开始:
        1. 编辑配置文件，添加你的 API Keys
           vim #{etc}/smart-router/smart-router.yaml
        
        2. 设置环境变量
           export OPENAI_API_KEY='your-key'
        
        3. 启动服务
           smart-router start
        
        4. 查看状态
           smart-router status

      文档: https://github.com/vaycentsun/smartRouter/docs/GUIDE.md
    EOS
  end

  test do
    system "#{bin}/smart-router", "--version"
    system "#{bin}/smr", "--version"
  end
end
