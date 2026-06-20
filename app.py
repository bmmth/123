"""
Flask 后端 — 提供 Dashboard API 和静态页面
启动方式：python app.py
"""
from flask import Flask, jsonify, render_template_string
from datetime import datetime
import database
from config import DASHBOARD_PORT, RATE_LIMIT_RPM, WARN_THRESHOLD, DANGER_THRESHOLD

app = Flask(__name__)


# ========== API 接口 ==========

@app.route('/api/stats/today')
def api_stats_today():
    """今日统计"""
    stats = database.get_stats_today()
    
    # 计算当前分钟调用量
    minute_calls = database.get_calls_by_minute(1)
    current_rpm = sum(m['calls'] for m in minute_calls)
    
    # 计算限流状态
    rpm_percent = current_rpm / RATE_LIMIT_RPM
    if rpm_percent >= DANGER_THRESHOLD:
        rpm_status = 'danger'
    elif rpm_percent >= WARN_THRESHOLD:
        rpm_status = 'warning'
    else:
        rpm_status = 'normal'
    
    return jsonify({
        'total_calls': stats['total_calls'],
        'total_tokens': stats['total_tokens'],
        'error_count': stats['error_count'],
        'avg_duration': stats['avg_duration'],
        'current_rpm': current_rpm,
        'rpm_limit': RATE_LIMIT_RPM,
        'rpm_percent': round(rpm_percent * 100, 1),
        'rpm_status': rpm_status
    })


@app.route('/api/stats/total')
def api_stats_total():
    """总统计"""
    return jsonify(database.get_stats_total())


@app.route('/api/stats/hourly')
def api_stats_hourly():
    """按小时统计（最近 24 小时）"""
    return jsonify(database.get_calls_by_hour(24))


@app.route('/api/stats/minute')
def api_stats_minute():
    """按分钟统计（最近 5 分钟）"""
    return jsonify(database.get_calls_by_minute(5))


@app.route('/api/stats/model')
def api_stats_model():
    """按模型统计"""
    return jsonify(database.get_calls_by_model())


@app.route('/api/calls/recent')
def api_calls_recent():
    """最近调用记录"""
    return jsonify(database.get_recent_calls(50))


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
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 28px;
            background: linear-gradient(135deg, #76b900, #a3e635);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .header p { color: #64748b; font-size: 14px; }
        
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
    </style>
</head>
<body>
    <div class="header">
        <h1>NVIDIA API Monitor</h1>
        <p>实时监控 API 调用次数、频率和用量</p>
    </div>
    
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
    
    <div class="table-card">
        <div class="table-title">最近调用记录</div>
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
            <tbody id="callsTable"></tbody>
        </table>
    </div>
    
    <div class="refresh-info">
        每 5 秒自动刷新 | 上次更新: <span id="lastUpdate">-</span>
    </div>

    <script>
        let hourlyChart, modelChart;
        
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
                hourlyChart.data.labels = hourly.map(h => h.hour.slice(11, 16));
                hourlyChart.data.datasets[0].data = hourly.map(h => h.calls);
                hourlyChart.update();
                
                // 模型图表
                const modelRes = await fetch('/api/stats/model');
                const models = await modelRes.json();
                modelChart.data.labels = models.map(m => m.model.split('/').pop());
                modelChart.data.datasets[0].data = models.map(m => m.calls);
                modelChart.update();
                
                // 调用记录
                const callsRes = await fetch('/api/calls/recent');
                const calls = await callsRes.json();
                const tbody = document.getElementById('callsTable');
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
                
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
            } catch (e) {
                console.error('刷新失败:', e);
            }
        }
        
        initCharts();
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
║  按 Ctrl+C 停止服务                                         ║
╚════════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=DASHBOARD_PORT, debug=True)
