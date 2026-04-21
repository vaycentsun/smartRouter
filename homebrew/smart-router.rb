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
    
    # 创建配置目录（V3 三文件配置）
    (etc/"smart-router").mkpath
    (etc/"smart-router/README").write readme_content
  end

  def readme_content
    <<~EOS
      # Smart Router 配置目录
      
      请运行以下命令生成默认 V3 配置（三文件格式）：
        smart-router init --output #{etc}/smart-router
      
      或运行：
        smart-router init
      # 配置将生成到 ~/.smart-router/
      
      三文件说明：
        - providers.yaml  # API 服务商连接配置
        - models.yaml     # 模型能力声明配置
        - routing.yaml    # 路由策略配置
    EOS
  end

  def caveats
    <<~EOS
      Smart Router 已安装！

      配置文件位置: #{etc}/smart-router/
      
      快速开始:
        1. 生成默认 V3 配置
           smart-router init --output #{etc}/smart-router
        
        2. 编辑配置文件，添加你的 API Keys
           vim #{etc}/smart-router/providers.yaml
        
        3. 设置环境变量
           export OPENAI_API_KEY='your-key'
        
        4. 启动服务
           smart-router start
        
        5. 查看状态
           smart-router status

      文档: https://github.com/vaycentsun/smartRouter/docs/GUIDE.md
    EOS
  end

  test do
    system "#{bin}/smart-router", "--version"
    system "#{bin}/smr", "--version"
  end
end
