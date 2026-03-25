import json
import sqlite3
import time
from typing import Any, Dict, Optional


DB_PATH = "smart_city.db"


def get_db_connection(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str = DB_PATH) -> None:
    conn = get_db_connection(path)
    cur = conn.cursor()

    # 节点负载快照（用于持久化）
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_name TEXT NOT NULL UNIQUE,
            cpu REAL NOT NULL,
            mem REAL NOT NULL,
            status TEXT NOT NULL,
            timestamp REAL NOT NULL
        )
        """
    )

    # 实验记录（预留）
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_name TEXT NOT NULL,
            start_time REAL NOT NULL,
            status TEXT DEFAULT 'running'
        )
        """
    )

    conn.commit()
    conn.close()


def save_node_load(
    name: str,
    cpu: float,
    mem: float,
    status: str,
    timestamp: Optional[float] = None,
    path: str = DB_PATH,
) -> None:
    ts = time.time() if timestamp is None else float(timestamp)
    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO nodes (node_name, cpu, mem, status, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, float(cpu), float(mem), str(status), ts),
    )
    conn.commit()
    conn.close()


def healthcheck(path: str = DB_PATH) -> Dict[str, Any]:
    """轻量自检：确认 DB 可连接且表存在。"""
    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    return {"db_path": path, "tables": tables}

