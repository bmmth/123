"""
配置文件 — 在这里修改你的 NVIDIA API Key 和限流参数
"""
import os

# ===== 必填 =====
# NVIDIA NIM API Key — 从 https://build.nvidia.com 获取
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "nvapi-你的key放这里")

# ===== 可选 =====
# NVIDIA API 地址（OpenAI 兼容格式）
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# 限流参数（NVIDIA 免费版：每分钟 40 次）
RATE_LIMIT_RPM = 40       # 每分钟最大请求数
WARN_THRESHOLD = 0.7      # 达到 70% 时 Dashboard 变黄
DANGER_THRESHOLD = 0.9    # 达到 90% 时 Dashboard 变红

# Dashboard 服务端口
DASHBOARD_PORT = 5000

# SQLite 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "api_stats.db")