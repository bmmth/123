# NVIDIA API Monitor Dashboard

一个轻量级的本地 Dashboard，用于监控 NVIDIA NIM API 的调用次数、频率和用量。

## 功能特性

- **调用统计**：今日调用次数、总调用次数、Token 消耗
- **频率监控**：实时显示当前 RPM（每分钟请求数），接近限流时自动预警
- **趋势图表**：24 小时调用趋势、按模型分布
- **调用记录**：最近 50 条调用详情

## 快速开始

### 1. 安装依赖

```bash
cd nvidia-api-monitor
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `config.py`，填入你的 NVIDIA API Key：

```python
NVIDIA_API_KEY = "nvapi-你的key放这里"
```

获取方式：访问 https://build.nvidia.com → 点击 Get API Key

### 3. 启动 Dashboard

```bash
python app.py
```

然后浏览器访问 http://localhost:5000

## 使用方式

### 方式一：直接使用测试脚本

```bash
python test_api.py
```

### 方式二：在你的代码中集成

```python
from api_client import chat_simple

# 简单调用
response = chat_simple(
    model="meta/llama-3.1-8b-instruct",
    user_message="你好，介绍一下自己"
)
print(response)
```

### 方式三：完整控制

```python
from api_client import NvidiaClient

client = NvidiaClient()

# 完整聊天接口
response = client.chat(
    model="meta/llama-3.1-8b-instruct",
    messages=[
        {"role": "system", "content": "你是一个友好的助手"},
        {"role": "user", "content": "你好"}
    ],
    temperature=0.7,
    max_tokens=100
)

print(response.choices[0].message.content)
```

## 常用模型

| 模型 ID | 说明 |
|---------|------|
| `meta/llama-3.1-8b-instruct` | Llama 3.1 8B，快速轻量 |
| `meta/llama-3.1-70b-instruct` | Llama 3.1 70B，平衡性能 |
| `mistralai/mistral-large` | Mistral Large |
| `deepseek-ai/deepseek-v3` | DeepSeek V3 |
| `qwen/qwen2.5-7b-instruct` | Qwen 2.5 7B |

完整模型列表：https://build.nvidia.com/models

## 限流说明

NVIDIA 免费版 API 限制：
- **每分钟 40 次请求（40 RPM）**
- Dashboard 会在达到 70% 时显示黄色警告，90% 时显示红色警告

## 项目结构

```
nvidia-api-monitor/
├── app.py           # Flask 后端 + Dashboard 页面
├── api_client.py    # NVIDIA API 封装（带统计）
├── database.py      # SQLite 数据库操作
├── config.py        # 配置文件
├── test_api.py      # 测试脚本
├── requirements.txt # 依赖列表
└── data/
    └── api_stats.db # SQLite 数据库（自动创建）
```

## 注意事项

1. API Key 不要泄露，不要上传到公开仓库
2. 数据存储在本地 SQLite，重启不会丢失
3. Dashboard 每 5 秒自动刷新数据
