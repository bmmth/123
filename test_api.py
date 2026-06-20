"""
测试脚本 — 测试 NVIDIA API 调用和 Dashboard 统计功能
运行方式：python test_api.py
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_client import NvidiaClient
from config import NVIDIA_API_KEY


def test_connection():
    """测试 API 连接"""
    print("=" * 50)
    print("测试 NVIDIA API 连接")
    print("=" * 50)
    
    if NVIDIA_API_KEY == "nvapi-你的key放这里":
        print("❌ 请先在 config.py 中配置你的 NVIDIA_API_KEY")
        print("   获取方式：https://build.nvidia.com -> 点击 Get API Key")
        return False
    
    client = NvidiaClient()
    
    print(f"\nAPI Key: {NVIDIA_API_KEY[:20]}...")
    print(f"Base URL: {client.base_url}")
    
    # 测试简单聊天
    print("\n发送测试请求: '你好，请用一句话介绍自己'")
    print("-" * 50)
    
    try:
        response = client.chat_simple(
            model="meta/llama-3.1-8b-instruct",
            user_message="你好，请用一句话介绍自己",
            max_tokens=100
        )
        print(f"✅ 响应成功！")
        print(f"\n回复内容:")
        print(response)
        return True
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def test_multiple_calls():
    """测试多次调用（验证统计功能）"""
    print("\n" + "=" * 50)
    print("测试多次调用（验证统计功能）")
    print("=" * 50)
    
    client = NvidiaClient()
    
    questions = [
        "1+1等于几？",
        "中国的首都是哪里？",
        "Python 是什么？",
    ]
    
    for i, q in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] 问题: {q}")
        try:
            response = client.chat_simple(
                model="meta/llama-3.1-8b-instruct",
                user_message=q,
                max_tokens=50
            )
            print(f"回答: {response[:100]}...")
        except Exception as e:
            print(f"错误: {e}")
    
    print("\n✅ 测试完成！请刷新 Dashboard 查看统计数据")


def show_available_models():
    """显示可用模型"""
    print("\n" + "=" * 50)
    print("常用 NVIDIA NIM 模型")
    print("=" * 50)
    
    models = [
        ("meta/llama-3.1-8b-instruct", "Llama 3.1 8B - 快速、轻量"),
        ("meta/llama-3.1-70b-instruct", "Llama 3.1 70B - 平衡性能"),
        ("meta/llama-3.1-405b-instruct", "Llama 3.1 405B - 最强性能"),
        ("mistralai/mistral-large", "Mistral Large"),
        ("google/gemma-2-9b-it", "Gemma 2 9B"),
        ("microsoft/phi-3-medium-128k-instruct", "Phi-3 Medium"),
        ("deepseek-ai/deepseek-v3", "DeepSeek V3"),
        ("qwen/qwen2.5-7b-instruct", "Qwen 2.5 7B"),
    ]
    
    for model_id, desc in models:
        print(f"  {model_id:<45} {desc}")


def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║           NVIDIA API Monitor - 测试脚本                     ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    # 显示可用模型
    show_available_models()
    
    # 测试连接
    if test_connection():
        print("\n" + "-" * 50)
        choice = input("\n是否继续测试多次调用？(y/n): ").strip().lower()
        if choice == 'y':
            test_multiple_calls()
    
    print("\n" + "=" * 50)
    print("下一步:")
    print("  1. 运行 'python app.py' 启动 Dashboard")
    print("  2. 浏览器访问 http://localhost:5000")
    print("=" * 50)


if __name__ == '__main__':
    main()
