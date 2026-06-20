"""
数据库模块 — 初始化 SQLite 表结构
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "api_stats.db")


def get_db_connection():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # API 调用记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            model TEXT NOT NULL,
            endpoint TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            duration_ms INTEGER DEFAULT 0,
            status TEXT DEFAULT 'success',
            error_message TEXT
        )
    """)
    
    # 创建索引加速查询
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON api_calls(timestamp)
    """)
    
    conn.commit()
    conn.close()


def log_api_call(model, endpoint, prompt_tokens=0, completion_tokens=0, 
                 total_tokens=0, duration_ms=0, status='success', error_message=None):
    """记录一次 API 调用"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO api_calls 
        (timestamp, model, endpoint, prompt_tokens, completion_tokens, 
         total_tokens, duration_ms, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now(), model, endpoint, prompt_tokens, completion_tokens,
          total_tokens, duration_ms, status, error_message))
    
    conn.commit()
    call_id = cursor.lastrowid
    conn.close()
    return call_id


def get_stats_today():
    """获取今日统计"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_calls,
            SUM(total_tokens) as total_tokens,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
            AVG(duration_ms) as avg_duration
        FROM api_calls
        WHERE date(timestamp) = date('now', 'localtime')
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    return {
        'total_calls': row['total_calls'] or 0,
        'total_tokens': row['total_tokens'] or 0,
        'error_count': row['error_count'] or 0,
        'avg_duration': round(row['avg_duration'] or 0, 2)
    }


def get_stats_total():
    """获取总统计"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_calls,
            SUM(total_tokens) as total_tokens,
            SUM(prompt_tokens) as total_prompt_tokens,
            SUM(completion_tokens) as total_completion_tokens
        FROM api_calls
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    return {
        'total_calls': row['total_calls'] or 0,
        'total_tokens': row['total_tokens'] or 0,
        'total_prompt_tokens': row['total_prompt_tokens'] or 0,
        'total_completion_tokens': row['total_completion_tokens'] or 0
    }


def get_calls_by_hour(hours=24):
    """获取最近 N 小时的调用量（按小时分组）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            strftime('%Y-%m-%d %H:00', timestamp) as hour,
            COUNT(*) as calls,
            SUM(total_tokens) as tokens
        FROM api_calls
        WHERE timestamp >= datetime('now', '-' || ? || ' hours', 'localtime')
        GROUP BY hour
        ORDER BY hour
    """, (hours,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_calls_by_minute(minutes=5):
    """获取最近 N 分钟的调用量（按分钟分组）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            strftime('%Y-%m-%d %H:%M', timestamp) as minute,
            COUNT(*) as calls
        FROM api_calls
        WHERE timestamp >= datetime('now', '-' || ? || ' minutes', 'localtime')
        GROUP BY minute
        ORDER BY minute
    """, (minutes,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_recent_calls(limit=50):
    """获取最近的调用记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            id, timestamp, model, endpoint, 
            prompt_tokens, completion_tokens, total_tokens,
            duration_ms, status
        FROM api_calls
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_calls_by_model():
    """按模型统计调用量"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            model,
            COUNT(*) as calls,
            SUM(total_tokens) as tokens
        FROM api_calls
        GROUP BY model
        ORDER BY calls DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# 初始化数据库
init_db()
