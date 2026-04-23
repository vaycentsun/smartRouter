class SmartRouter < Formula
  include Language::Python::Virtualenv

  desc "智能模型路由网关 — 基于 LiteLLM 的多服务商自动路由 CLI 工具"
  homepage "https://github.com/vaycentsun/smartRouter"
  url "https://files.pythonhosted.org/packages/source/s/smartrouter/smartrouter-1.0.9.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"
  head "https://github.com/vaycentsun/smartRouter.git", branch: "main"

  depends_on "python@3.9"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/smart-router", "--version"
  end
end
