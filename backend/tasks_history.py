# backend/tasks_history.py
"""
任务历史记录 - 严格按任务要求实现
只记录：到达、分配、完成、超时
"""
import sqlite3
import time

def init_tasks_history_table():
    """初始化任务历史表"""
    conn = sqlite3.connect("smart_city.db")
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        status TEXT NOT NULL,           -- 状态: arrived, assigned, completed, timeout
        node_name TEXT,                 -- 分配的节点（仅assigned状态有）
        timestamp REAL NOT NULL         -- 时间戳
    )
    """)
    
    conn.commit()
    conn.close()

def record_task_arrival(task_id: str):
    """记录任务到达"""
    conn = sqlite3.connect("smart_city.db")
    cur = conn.cursor()
    
    cur.execute(
        "INSERT INTO tasks_history (task_id, status, timestamp) VALUES (?, ?, ?)",
        (task_id, "arrived", time.time())
    )
    
    conn.commit()
    conn.close()

def record_task_assigned(task_id: str, node_name: str):
    """记录任务分配"""
    conn = sqlite3.connect("smart_city.db")
    cur = conn.cursor()
    
    cur.execute(
        "INSERT INTO tasks_history (task_id, status, node_name, timestamp) VALUES (?, ?, ?, ?)",
        (task_id, "assigned", node_name, time.time())
    )
    
    conn.commit()
    conn.close()

def record_task_completed(task_id: str):
    """记录任务完成"""
    conn = sqlite3.connect("smart_city.db")
    cur = conn.cursor()
    
    cur.execute(
        "INSERT INTO tasks_history (task_id, status, timestamp) VALUES (?, ?, ?)",
        (task_id, "completed", time.time())
    )
    
    conn.commit()
    conn.close()

def record_task_timeout(task_id: str):
    """记录任务超时"""
    conn = sqlite3.connect("smart_city.db")
    cur = conn.cursor()
    
    cur.execute(
        "INSERT INTO tasks_history (task_id, status, timestamp) VALUES (?, ?, ?)",
        (task_id, "timeout", time.time())
    )
    
    conn.commit()
    conn.close()

def get_task_history(task_id: str = None, limit: int = 100):
    """获取任务历史 - 用于前端复盘"""
    conn = sqlite3.connect("smart_city.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    if task_id:
        cur.execute(
            "SELECT * FROM tasks_history WHERE task_id = ? ORDER BY timestamp DESC LIMIT ?",
            (task_id, limit)
        )
    else:
        cur.execute(
            "SELECT * FROM tasks_history ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
    
    results = [dict(row) for row in cur.fetchall()]
    conn.close()
    return results

# 初始化表
init_tasks_history_table()