#!/usr/bin/env python3
"""Smart Router API 测试脚本"""

import os
from openai import OpenAI

# 配置
BASE_URL = "http://127.0.0.1:4000"
API_KEY = "sk-smart-router-local"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def test_models_list():
    """测试 1: 获取模型列表"""
    print("=" * 50)
    print("测试 1: 获取模型列表")
    print("=" * 50)
    
    try:
        models = client.models.list()
        print(f"✓ 成功获取 {len(models.data)} 个模型:")
        for m in models.data[:5]:  # 只显示前5个
            print(f"  - {m.id}")
        if len(models.data) > 5:
            print(f"  ... 还有 {len(models.data) - 5} 个模型")
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False

def test_chat_completion(model_name="glm-4-plus"):
    """测试 2: 简单对话"""
    print("\n" + "=" * 50)
    print(f"测试 2: 对话测试 (模型: {model_name})")
    print("=" * 50)
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": "你好，请用一句话回复"}
            ],
            max_tokens=50,
            stream=False
        )
        print(f"✓ 成功!")
        print(f"  模型: {response.model}")
        print(f"  回复: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False

def test_streaming(model_name="glm-4-plus"):
    """测试 3: 流式输出"""
    print("\n" + "=" * 50)
    print(f"测试 3: 流式输出 (模型: {model_name})")
    print("=" * 50)
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": "你好"}
            ],
            max_tokens=30,
            stream=True
        )
        
        print("✓ 成功! 回复: ", end="")
        for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print()
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False

def test_with_stage_marker():
    """测试 4: 使用阶段标记"""
    print("\n" + "=" * 50)
    print("测试 4: 阶段标记路由")
    print("=" * 50)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # 模型名会被路由覆盖
            messages=[
                {"role": "user", "content": "[stage:code_review]\n请审查这段代码: print('hello')"}
            ],
            max_tokens=50
        )
        print(f"✓ 成功! 路由模型: {response.model}")
        print(f"  回复预览: {response.choices[0].message.content[:50]}...")
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False

if __name__ == "__main__":
    print("Smart Router API 测试")
    print("=" * 50)
    
    results = []
    
    # 运行测试
    results.append(("模型列表", test_models_list()))
    results.append(("简单对话", test_chat_completion("glm-4-plus")))
    results.append(("流式输出", test_streaming("glm-4-plus")))
    results.append(("阶段标记", test_with_stage_marker()))
    
    # 总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
