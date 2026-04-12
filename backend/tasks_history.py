# backend/tasks_history.py
"""
任务历史（到达 / 分配 / 完成 / 超时）— SQLite 持久化，与 backend.database 共用 DB_PATH。
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any, Dict, List, Optional

from backend.database import DB_PATH, get_db_connection


def task_public_id(task: Dict[str, Any]) -> str:
    """统一任务主键字符串：优先 task_id，其次 id。"""
    if task.get("task_id") is not None:
        return str(task["task_id"])
    if task.get("id") is not None:
        return str(task["id"])
    return ""


def init_tasks_history_table(path: str = DB_PATH) -> None:
    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            status TEXT NOT NULL,
            node_name TEXT,
            timestamp REAL NOT NULL
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_history_task_id ON tasks_history(task_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_history_ts ON tasks_history(timestamp)"
    )
    conn.commit()
    conn.close()


def record_task_arrival(task_id: str, path: str = DB_PATH) -> None:
    if not task_id:
        return
    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks_history (task_id, status, timestamp) VALUES (?, ?, ?)",
        (task_id, "arrived", time.time()),
    )
    conn.commit()
    conn.close()


def record_task_assigned(task_id: str, node_name: str, path: str = DB_PATH) -> None:
    if not task_id:
        return
    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks_history (task_id, status, node_name, timestamp) VALUES (?, ?, ?, ?)",
        (task_id, "assigned", node_name, time.time()),
    )
    conn.commit()
    conn.close()


def record_task_completed(task_id: str, path: str = DB_PATH) -> None:
    if not task_id:
        return
    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks_history (task_id, status, timestamp) VALUES (?, ?, ?)",
        (task_id, "completed", time.time()),
    )
    conn.commit()
    conn.close()


def record_task_timeout(task_id: str, path: str = DB_PATH) -> None:
    if not task_id:
        return
    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks_history (task_id, status, timestamp) VALUES (?, ?, ?)",
        (task_id, "timeout", time.time()),
    )
    conn.commit()
    conn.close()


def get_task_history(
    task_id: Optional[str] = None, limit: int = 100, path: str = DB_PATH
) -> List[Dict[str, Any]]:
    conn = get_db_connection(path)
    cur = conn.cursor()
    if task_id:
        cur.execute(
            """
            SELECT * FROM tasks_history
            WHERE task_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (task_id, int(limit)),
        )
    else:
        cur.execute(
            """
            SELECT * FROM tasks_history
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (int(limit),),
        )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]
