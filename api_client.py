"""
API 中间件 — 封装 NVIDIA API 调用并自动记录统计
使用方法：
    from api_client import NvidiaClient
    
    client = NvidiaClient()
    response = client.chat("meta/llama-3.1-8b-instruct", "你好")
"""
import time
from openai import OpenAI
import database
from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, RATE_LIMIT_RPM


class NvidiaClient:
    """NVIDIA API 客户端（带统计功能）"""
    
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or NVIDIA_API_KEY
        self.base_url = base_url or NVIDIA_BASE_URL
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(self, model, messages, **kwargs):
        """
        发送聊天请求
        
        Args:
            model: 模型名称，如 "meta/llama-3.1-8b-instruct"
            messages: 消息列表，如 [{"role": "user", "content": "你好"}]
            **kwargs: 其他参数（temperature, max_tokens 等）
        
        Returns:
            OpenAI Response 对象
        """
        start_time = time.time()
        status = 'success'
        error_msg = None
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            
            # 提取 token 统计
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
            
            return response
            
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            raise
        
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录到数据库
            database.log_api_call(
                model=model,
                endpoint='/chat/completions',
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg
            )
    
    def chat_simple(self, model, user_message, system_prompt=None, **kwargs):
        """
        简化的聊天接口
        
        Args:
            model: 模型名称
            user_message: 用户消息字符串
            system_prompt: 系统提示词（可选）
            **kwargs: 其他参数
        
        Returns:
            助手回复文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        
        response = self.chat(model, messages, **kwargs)
        return response.choices[0].message.content
    
    def get_available_models(self):
        """获取可用模型列表"""
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except:
            # 返回一些常见的 NVIDIA NIM 模型
            return [
                "meta/llama-3.1-8b-instruct",
                "meta/llama-3.1-70b-instruct",
                "meta/llama-3.1-405b-instruct",
                "mistralai/mistral-large",
                "mistralai/mixtral-8x7b-instruct",
                "google/gemma-2-9b-it",
                "google/gemma-2-27b-it",
                "microsoft/phi-3-medium-128k-instruct",
                "deepseek-ai/deepseek-v3",
                "qwen/qwen2.5-7b-instruct",
            ]


# 便捷函数
_client = None

def get_client():
    """获取全局客户端实例"""
    global _client
    if _client is None:
        _client = NvidiaClient()
    return _client


def chat(model, messages, **kwargs):
    """便捷函数：发送聊天请求"""
    return get_client().chat(model, messages, **kwargs)


def chat_simple(model, user_message, system_prompt=None, **kwargs):
    """便捷函数：简化聊天"""
    return get_client().chat_simple(model, user_message, system_prompt, **kwargs)
