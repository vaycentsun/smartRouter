"""Smart Router 全局异常定义

将异常类集中在独立模块，避免循环导入。
"""


class NoModelAvailableError(Exception):
    """没有可用模型匹配当前请求的任务/难度/策略"""
    pass


class UnknownStrategyError(Exception):
    """未知的路由策略"""
    pass
