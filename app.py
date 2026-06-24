"""
Flask 后端 — 提供 Dashboard API 和静态页面
支持前端配置 API Key
"""
from flask import Flask, jsonify, render_template_string, request
from datetime import datetime, timedelta
import os
import json
import requests

app = Flask(__name__)

# API Key 存储文件路径
API_KEY_FILE = os.path.join(os.path.dirname(__file__), "data", "api_key.json")

# 限流参数
RATE_LIMIT_RPM = 40
WARN_THRESHOLD = 0.7
DANGER_THRESHOLD = 0.9
DASHBOARD_PORT = 5000

# ========== API Key 管理 ==========

def get_saved_api_key():
    """获取保存的 API Key"""
    try:
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE, 'r') as f:
                data = json.load(f)
                return data.get('api_key', '')
    except:
        pass
    return ''

def save_api_key(api_key):
    """保存 API Key"""
    os.makedirs(os.path.dirname(API_KEY_FILE), exist_ok=True)
    with open(API_KEY_FILE, 'w') as f:
        json.dump({'api_key': api_key}, f)

# ========== 简化的数据库（使用 JSON 文件） ==========

DB_FILE = os.path.join(os.path.dirname(__file__), "data", "api_stats.json")

def get_db():
    """获取数据库数据"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {'calls': []}

def save_db(data):
    """保存数据库数据"""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

def log_api_call(model, prompt_tokens, completion_tokens, total_tokens, duration_ms, status):
    """记录 API 调用"""
    db = get_db()
    db['calls'].append({
        'timestamp': datetime.now().isoformat(),
        'model': model,
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens': total_tokens,
        'duration_ms': duration_ms,
        'status': status
    })
    # 只保留最近 1000 条记录
    if len(db['calls']) > 1000:
        db['calls'] = db['calls'][-1000:]
    save_db(db)

# ========== API 代理服务器 ==========

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

@app.route('/v1/chat/completions', methods=['POST'])
def proxy_chat_completions():
    """
    代理 NVIDIA API 调用 - 自动记录所有请求
    
    使用方法：把你的 OpenAI 客户端 base_url 改成 http://localhost:5000
    """
    import time
    
    api_key = get_saved_api_key()
    if not api_key:
        return jsonify({'error': {'message': '请先在 Dashboard 配置 API Key', 'type': 'config_error'}}), 400
    
    # 获取请求体
    request_data = request.get_json()
    model = request_data.get('model', 'unknown')
    
    start_time = time.time()
    status = 'success'
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    
    try:
        # 转发请求到 NVIDIA API
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            headers=headers,
            json=request_data,
            timeout=60
        )
        
        duration = int((time.time() - start_time) * 1000)
        
        # 如果成功，提取 token 统计
        if response.status_code == 200:
            resp_json = response.json()
            usage = resp_json.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
        else:
            status = 'error'
        
        # 记录调用
        log_api_call(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            duration_ms=duration,
            status=status
        )
        
        # 返回原始响应
        return response.content, response.status_code, {'Content-Type': 'application/json'}
        
    except requests.exceptions.Timeout:
        duration = int((time.time() - start_time) * 1000)
        log_api_call(model=model, prompt_tokens=0, completion_tokens=0, total_tokens=0, duration_ms=duration, status='error')
        return jsonify({'error': {'message': '请求超时', 'type': 'timeout_error'}}), 504
        
    except Exception as e:
        duration = int((time.time() - start_time) * 1000)
        log_api_call(model=model, prompt_tokens=0, completion_tokens=0, total_tokens=0, duration_ms=duration, status='error')
        return jsonify({'error': {'message': str(e), 'type': 'proxy_error'}}), 500

@app.route('/v1/models', methods=['GET'])
def proxy_models():
    """代理模型列表 API"""
    api_key = get_saved_api_key()
    if not api_key:
        return jsonify({'error': {'message': '请先配置 API Key'}}), 400
    
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(f"{NVIDIA_BASE_URL}/models", headers=headers)
    return response.content, response.status_code, {'Content-Type': 'application/json'}

# ========== Dashboard API 接口 ==========

@app.route('/api/key/get')
def api_key_get():
    """获取当前保存的 API Key（只显示是否已配置）"""
    key = get_saved_api_key()
    return jsonify({
        'configured': bool(key),
        'key_preview': key[:20] + '...' if len(key) > 20 else key
    })

@app.route('/api/key/set', methods=['POST'])
def api_key_set():
    """设置 API Key"""
    data = request.get_json()
    api_key = data.get('api_key', '')
    if api_key:
        save_api_key(api_key)
        return jsonify({'success': True, 'message': 'API Key 已保存'})
    return jsonify({'success': False, 'message': 'API Key 不能为空'})

@app.route('/api/key/test', methods=['POST'])
def api_key_test():
    """测试 API Key 是否有效"""
    import time
    try:
        from openai import OpenAI
        
        data = request.get_json()
        api_key = data.get('api_key', get_saved_api_key())
        
        if not api_key:
            return jsonify({'success': False, 'message': '请先填写 API Key'})
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1"
        )
        
        start_time = time.time()
        response = client.chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10
        )
        duration = int((time.time() - start_time) * 1000)
        
        # 记录调用
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0
        
        log_api_call(
            model="meta/llama-3.1-8b-instruct",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            duration_ms=duration,
            status='success'
        )
        
        return jsonify({
            'success': True,
            'message': 'API Key 有效！',
            'response': response.choices[0].message.content[:50],
            'duration': duration,
            'tokens': total_tokens
        })
    except Exception as e:
        # 记录失败
        log_api_call(
            model="meta/llama-3.1-8b-instruct",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=0,
            status='error'
        )
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stats/today')
def api_stats_today():
    """今日统计"""
    db = get_db()
    today = datetime.now().date().isoformat()
    
    today_calls = [c for c in db['calls'] if c['timestamp'].startswith(today)]
    total_calls = len(today_calls)
    total_tokens = sum(c['total_tokens'] for c in today_calls)
    error_count = sum(1 for c in today_calls if c['status'] == 'error')
    avg_duration = sum(c['duration_ms'] for c in today_calls) / total_calls if total_calls > 0 else 0
    
    # 计算当前 RPM（最近 1 分钟）
    now = datetime.now()
    minute_ago = (now - timedelta(minutes=1)).isoformat()
    minute_calls = [c for c in db['calls'] if c['timestamp'] > minute_ago]
    current_rpm = len(minute_calls)
    
    rpm_percent = current_rpm / RATE_LIMIT_RPM
    if rpm_percent >= DANGER_THRESHOLD:
        rpm_status = 'danger'
    elif rpm_percent >= WARN_THRESHOLD:
        rpm_status = 'warning'
    else:
        rpm_status = 'normal'
    
    return jsonify({
        'total_calls': total_calls,
        'total_tokens': total_tokens,
        'error_count': error_count,
        'avg_duration': round(avg_duration, 2),
        'current_rpm': current_rpm,
        'rpm_limit': RATE_LIMIT_RPM,
        'rpm_percent': round(rpm_percent * 100, 1),
        'rpm_status': rpm_status
    })

@app.route('/api/stats/total')
def api_stats_total():
    """总统计"""
    db = get_db()
    calls = db['calls']
    return jsonify({
        'total_calls': len(calls),
        'total_tokens': sum(c['total_tokens'] for c in calls),
        'total_prompt_tokens': sum(c['prompt_tokens'] for c in calls),
        'total_completion_tokens': sum(c['completion_tokens'] for c in calls)
    })

@app.route('/api/stats/hourly')
def api_stats_hourly():
    """按小时统计"""
    db = get_db()
    calls = db['calls']
    
    # 按小时分组
    hourly = {}
    for c in calls:
        hour = c['timestamp'][:13] + ':00'
        hourly[hour] = hourly.get(hour, 0) + 1
    
    # 返回最近 24 小时
    result = [{'hour': h, 'calls': hourly[h]} for h in sorted(hourly.keys())[-24:]]
    return jsonify(result)

@app.route('/api/stats/model')
def api_stats_model():
    """按模型统计"""
    db = get_db()
    calls = db['calls']
    
    models = {}
    for c in calls:
        model = c['model']
        models[model] = models.get(model, {'calls': 0, 'tokens': 0})
        models[model]['calls'] += 1
        models[model]['tokens'] += c['total_tokens']
    
    return jsonify([{'model': m, 'calls': data['calls'], 'tokens': data['tokens']} 
                    for m, data in models.items()])

@app.route('/api/calls/recent')
def api_calls_recent():
    """最近调用记录"""
    db = get_db()
    return jsonify(db['calls'][-50:])

# ========== 前端页面 ==========

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NVIDIA API Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
            padding: 20px;
        }
        
        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
            gap: 16px;
        }
        .header-title h1 {
            font-size: 28px;
            background: linear-gradient(135deg, #76b900, #a3e635);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 4px;
        }
        .header-title p { color: #64748b; font-size: 14px; }
        
        /* Settings Button */
        .settings-btn {
            background: #1e293b;
            border: 1px solid #334155;
            color: #e2e8f0;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }
        .settings-btn:hover {
            background: #334155;
            border-color: #76b900;
        }
        .settings-btn.configured {
            border-color: #22c55e;
        }
        .settings-btn.not-configured {
            border-color: #f59e0b;
        }
        
        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-overlay.show { display: flex; }
        .modal {
            background: #1e293b;
            border-radius: 16px;
            padding: 32px;
            width: 90%;
            max-width: 500px;
            border: 1px solid #334155;
        }
        .modal-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 24px;
            color: #f1f5f9;
        }
        .modal-close {
            float: right;
            background: none;
            border: none;
            color: #64748b;
            font-size: 24px;
            cursor: pointer;
        }
        
        /* Form */
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 8px;
        }
        .form-input {
            width: 100%;
            background: #0f172a;
            border: 1px solid #334155;
            color: #e2e8f0;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
        }
        .form-input:focus {
            outline: none;
            border-color: #76b900;
        }
        .form-hint {
            font-size: 12px;
            color: #64748b;
            margin-top: 8px;
        }
        
        /* Buttons */
        .btn {
            background: #76b900;
            color: #000;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn:hover { background: #a3e635; }
        .btn-secondary {
            background: #334155;
            color: #e2e8f0;
        }
        .btn-secondary:hover { background: #475569; }
        .btn-group {
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }
        
        /* Status */
        .status-message {
            padding: 12px 16px;
            border-radius: 8px;
            margin-top: 16px;
            font-size: 14px;
        }
        .status-success {
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid #22c55e;
            color: #22c55e;
        }
        .status-error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid #ef4444;
            color: #ef4444;
        }
        .status-loading {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid #3b82f6;
            color: #3b82f6;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }
        .stat-card.warning { border-color: #f59e0b; }
        .stat-card.danger { border-color: #ef4444; }
        .stat-label {
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            color: #f1f5f9;
        }
        .stat-card.warning .stat-value { color: #f59e0b; }
        .stat-card.danger .stat-value { color: #ef4444; }
        .stat-sub {
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
        }
        
        /* Charts */
        .charts-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 16px;
            margin-bottom: 24px;
        }
        @media (max-width: 900px) {
            .charts-grid { grid-template-columns: 1fr; }
        }
        .chart-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }
        .chart-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #94a3b8;
        }
        
        /* Table */
        .table-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }
        .table-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #94a3b8;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        th, td {
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }
        th { color: #64748b; font-weight: 500; }
        td { color: #cbd5e1; }
        .status-success { color: #22c55e; }
        .status-error { color: #ef4444; }
        
        .refresh-info {
            text-align: center;
            color: #475569;
            font-size: 12px;
            margin-top: 20px;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }
        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        
        /* Proxy Info */
        .proxy-info {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            border: 1px solid #76b900;
            border-left: 4px solid #76b900;
        }
        .proxy-title {
            font-size: 14px;
            color: #76b900;
            margin-bottom: 8px;
        }
        .proxy-url {
            font-size: 18px;
            font-weight: 700;
            color: #f1f5f9;
            margin-bottom: 8px;
        }
        .proxy-desc {
            font-size: 13px;
            color: #94a3b8;
            margin-bottom: 12px;
        }
        .proxy-desc code {
            background: #0f172a;
            padding: 2px 6px;
            border-radius: 4px;
            color: #76b900;
        }
        .proxy-example {
            background: #0f172a;
            padding: 12px;
            border-radius: 8px;
            font-size: 12px;
            color: #94a3b8;
        }
        .proxy-example code {
            color: #22c55e;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="header-title">
            <h1>NVIDIA API Monitor</h1>
            <p>实时监控 API 调用次数、频率和用量</p>
        </div>
        <button class="settings-btn" id="settingsBtn" onclick="openSettings()">
            <span>⚙️</span>
            <span id="settingsStatus">配置 API Key</span>
        </button>
    </div>
    
    <!-- Settings Modal -->
    <div class="modal-overlay" id="settingsModal">
        <div class="modal">
            <button class="modal-close" onclick="closeSettings()">×</button>
            <div class="modal-title">API Key 配置</div>
            
            <div class="form-group">
                <label class="form-label">NVIDIA API Key</label>
                <input type="text" class="form-input" id="apiKeyInput" 
                       placeholder="nvapi-xxxxx...">
                <div class="form-hint">
                    从 <a href="https://build.nvidia.com" target="_blank" style="color: #76b900;">build.nvidia.com</a> 获取免费 API Key
                </div>
            </div>
            
            <div class="btn-group">
                <button class="btn" onclick="testApiKey()">测试连接</button>
                <button class="btn btn-secondary" onclick="saveApiKey()">保存</button>
            </div>
            
            <div id="statusMessage" style="display: none;"></div>
        </div>
    </div>
    
    <!-- Proxy Info -->
    <div class="proxy-info">
        <div class="proxy-title">🔗 代理服务器地址</div>
        <div class="proxy-url">http://localhost:5000/v1</div>
        <div class="proxy-desc">把你的 OpenAI 客户端 <code>base_url</code> 改成上面的地址，所有 API 调用都会自动记录到 Dashboard</div>
        <div class="proxy-example">
            <strong>示例代码：</strong><br>
            <code>client = OpenAI(api_key="nvapi-xxx", base_url="http://localhost:5000/v1")</code>
        </div>
    </div>
    
    <!-- Stats -->
    <div class="stats-grid" id="statsGrid">
        <div class="stat-card" id="cardToday">
            <div class="stat-label">今日调用</div>
            <div class="stat-value" id="todayCalls">-</div>
            <div class="stat-sub">次</div>
        </div>
        <div class="stat-card" id="cardTotal">
            <div class="stat-label">总调用</div>
            <div class="stat-value" id="totalCalls">-</div>
            <div class="stat-sub">次</div>
        </div>
        <div class="stat-card" id="cardTokens">
            <div class="stat-label">今日 Token</div>
            <div class="stat-value" id="todayTokens">-</div>
            <div class="stat-sub">tokens</div>
        </div>
        <div class="stat-card" id="cardRpm">
            <div class="stat-label">当前频率</div>
            <div class="stat-value" id="currentRpm">-</div>
            <div class="stat-sub" id="rpmStatus">/ 40 RPM</div>
        </div>
    </div>
    
    <!-- Charts -->
    <div class="charts-grid">
        <div class="chart-card">
            <div class="chart-title">调用趋势（最近 24 小时）</div>
            <canvas id="hourlyChart"></canvas>
        </div>
        <div class="chart-card">
            <div class="chart-title">模型分布</div>
            <canvas id="modelChart"></canvas>
        </div>
    </div>
    
    <!-- Table -->
    <div class="table-card">
        <div class="table-title">最近调用记录</div>
        <div id="callsTableContainer">
            <table>
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>模型</th>
                        <th>输入</th>
                        <th>输出</th>
                        <th>总Token</th>
                        <th>耗时</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody id="callsTable">
                    <tr>
                        <td colspan="7" class="empty-state">
                            <div class="empty-state-icon">📭</div>
                            <div>暂无调用记录，请先配置 API Key 并测试</div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="refresh-info">
        每 5 秒自动刷新 | 上次更新: <span id="lastUpdate">-</span>
    </div>

    <script>
        let hourlyChart, modelChart;
        let apiKeyConfigured = false;
        
        // 初始化图表
        function initCharts() {
            const ctx1 = document.getElementById('hourlyChart').getContext('2d');
            hourlyChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '调用次数',
                        data: [],
                        borderColor: '#76b900',
                        backgroundColor: 'rgba(118, 185, 0, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: '#334155' }, ticks: { color: '#64748b' } },
                        y: { grid: { color: '#334155' }, ticks: { color: '#64748b' }, beginAtZero: true }
                    }
                }
            });
            
            const ctx2 = document.getElementById('modelChart').getContext('2d');
            modelChart = new Chart(ctx2, {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: ['#76b900', '#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } }
                }
            });
        }
        
        // 设置弹窗
        function openSettings() {
            document.getElementById('settingsModal').classList.add('show');
            checkApiKey();
        }
        
        function closeSettings() {
            document.getElementById('settingsModal').classList.remove('show');
        }
        
        // 检查 API Key 状态
        async function checkApiKey() {
            try {
                const res = await fetch('/api/key/get');
                const data = await res.json();
                apiKeyConfigured = data.configured;
                
                const btn = document.getElementById('settingsBtn');
                const status = document.getElementById('settingsStatus');
                
                if (data.configured) {
                    btn.classList.add('configured');
                    btn.classList.remove('not-configured');
                    status.textContent = 'API Key 已配置';
                    document.getElementById('apiKeyInput').value = data.key_preview;
                } else {
                    btn.classList.add('not-configured');
                    btn.classList.remove('configured');
                    status.textContent = '请配置 API Key';
                }
            } catch (e) {
                console.error('检查失败:', e);
            }
        }
        
        // 保存 API Key
        async function saveApiKey() {
            const apiKey = document.getElementById('apiKeyInput').value.trim();
            if (!apiKey) {
                showStatus('请输入 API Key', 'error');
                return;
            }
            
            try {
                const res = await fetch('/api/key/set', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: apiKey })
                });
                const data = await res.json();
                
                if (data.success) {
                    showStatus('✓ ' + data.message, 'success');
                    checkApiKey();
                    closeSettings();
                } else {
                    showStatus('✗ ' + data.message, 'error');
                }
            } catch (e) {
                showStatus('✗ 保存失败: ' + e, 'error');
            }
        }
        
        // 测试 API Key
        async function testApiKey() {
            const apiKey = document.getElementById('apiKeyInput').value.trim();
            if (!apiKey) {
                showStatus('请输入 API Key', 'error');
                return;
            }
            
            showStatus('⏳ 正在测试连接...', 'loading');
            
            try {
                const res = await fetch('/api/key/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: apiKey })
                });
                const data = await res.json();
                
                if (data.success) {
                    showStatus(`✓ ${data.message} | 响应: "${data.response}" | 耗时: ${data.duration}ms | Token: ${data.tokens}`, 'success');
                    // 自动保存有效的 Key
                    saveApiKey();
                    // 刷新统计数据
                    refreshData();
                } else {
                    showStatus('✗ ' + data.message, 'error');
                }
            } catch (e) {
                showStatus('✗ 测试失败: ' + e, 'error');
            }
        }
        
        // 显示状态消息
        function showStatus(message, type) {
            const el = document.getElementById('statusMessage');
            el.style.display = 'block';
            el.className = 'status-message status-' + type;
            el.textContent = message;
        }
        
        // 更新数据
        async function refreshData() {
            try {
                // 今日统计
                const todayRes = await fetch('/api/stats/today');
                const today = await todayRes.json();
                
                document.getElementById('todayCalls').textContent = today.total_calls;
                document.getElementById('todayTokens').textContent = today.total_tokens.toLocaleString();
                document.getElementById('currentRpm').textContent = today.current_rpm;
                document.getElementById('rpmStatus').textContent = `/ ${today.rpm_limit} RPM (${today.rpm_percent}%)`;
                
                // RPM 状态颜色
                const rpmCard = document.getElementById('cardRpm');
                rpmCard.classList.remove('warning', 'danger');
                if (today.rpm_status === 'danger') rpmCard.classList.add('danger');
                else if (today.rpm_status === 'warning') rpmCard.classList.add('warning');
                
                // 总统计
                const totalRes = await fetch('/api/stats/total');
                const total = await totalRes.json();
                document.getElementById('totalCalls').textContent = total.total_calls.toLocaleString();
                
                // 小时图表
                const hourlyRes = await fetch('/api/stats/hourly');
                const hourly = await hourlyRes.json();
                if (hourly.length > 0) {
                    hourlyChart.data.labels = hourly.map(h => h.hour.slice(11, 16));
                    hourlyChart.data.datasets[0].data = hourly.map(h => h.calls);
                    hourlyChart.update();
                }
                
                // 模型图表
                const modelRes = await fetch('/api/stats/model');
                const models = await modelRes.json();
                if (models.length > 0) {
                    modelChart.data.labels = models.map(m => m.model.split('/').pop());
                    modelChart.data.datasets[0].data = models.map(m => m.calls);
                    modelChart.update();
                }
                
                // 调用记录
                const callsRes = await fetch('/api/calls/recent');
                const calls = await callsRes.json();
                const tbody = document.getElementById('callsTable');
                
                if (calls.length > 0) {
                    tbody.innerHTML = calls.map(c => `
                        <tr>
                            <td>${c.timestamp.slice(11, 19)}</td>
                            <td>${c.model.split('/').pop()}</td>
                            <td>${c.prompt_tokens}</td>
                            <td>${c.completion_tokens}</td>
                            <td>${c.total_tokens}</td>
                            <td>${c.duration_ms}ms</td>
                            <td class="status-${c.status}">${c.status === 'success' ? '成功' : '失败'}</td>
                        </tr>
                    `).join('');
                }
                
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
            } catch (e) {
                console.error('刷新失败:', e);
            }
        }
        
        // 初始化
        initCharts();
        checkApiKey();
        refreshData();
        setInterval(refreshData, 5000);
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """Dashboard 首页"""
    return render_template_string(DASHBOARD_HTML)


if __name__ == '__main__':
    print(f"""
╔════════════════════════════════════════════════════════════╗
║           NVIDIA API Monitor Dashboard                      ║
╠════════════════════════════════════════════════════════════╣
║  访问地址: http://localhost:{DASHBOARD_PORT}                       ║
║  功能: 前端配置 API Key + 实时监控                           ║
║  按 Ctrl+C 停止服务                                         ║
╚════════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=DASHBOARD_PORT, debug=True)