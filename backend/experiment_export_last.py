"""
最近一次已完成 SQLite 实验的导出数据构建（供 scripts 与 HTTP 下载共用）。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List


def build_last_experiment_export_dict(db_path: str) -> Dict[str, Any]:
    """
    与 scripts/export_last_experiment.py 逻辑一致，返回可 JSON 序列化的 dict。
    无可用实验时抛出 ValueError。
    """
    if not db_path:
        raise ValueError("db_path 为空")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, experiment_name, start_time, end_time, status
        FROM experiment
        WHERE status IN ('stopped', 'finished') AND end_time IS NOT NULL
        ORDER BY end_time DESC
        LIMIT 1
        """
    )
    exp_row = cur.fetchone()
    if not exp_row:
        conn.close()
        raise ValueError(
            "未找到已完成的实验（需 status 为 stopped/finished 且 end_time 非空）"
        )

    exp_data = dict(exp_row)
    exp_id = exp_data["id"]
    exp_name = exp_data["experiment_name"]

    cur.execute(
        """
        SELECT node_name, cpu, mem, status, timestamp
        FROM nodes
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
        """,
        (exp_data["start_time"], exp_data["end_time"]),
    )
    node_rows = cur.fetchall()
    node_count = len(node_rows)

    if node_count == 0:
        cur.execute(
            """
            SELECT node_name, cpu, mem, status, timestamp
            FROM nodes
            ORDER BY timestamp ASC
            """
        )
        node_rows = cur.fetchall()
        node_count = len(node_rows)

    task_events: List[Dict[str, Any]] = []
    try:
        cur.execute(
            """
            SELECT task_id, status, node_name, timestamp
            FROM tasks_history
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (exp_data["start_time"], exp_data["end_time"]),
        )
        task_events = [dict(r) for r in cur.fetchall()]
    except sqlite3.OperationalError:
        pass

    conn.close()

    export_data: Dict[str, Any] = {
        "export_info": {
            "timestamp": datetime.now().isoformat(),
            "format": "json",
            "experiment_count": 1,
            "node_count": node_count,
            "tasks_history_count": len(task_events),
        },
        "experiments": [
            {
                "id": exp_data["id"],
                "name": exp_data["experiment_name"],
                "start_time": exp_data["start_time"],
                "end_time": exp_data["end_time"],
                "status": exp_data["status"],
            }
        ],
        "nodes": [
            {
                "node_name": row["node_name"],
                "cpu": row["cpu"],
                "mem": row["mem"],
                "status": row["status"],
                "timestamp": row["timestamp"],
            }
            for row in node_rows
        ],
        "tasks_history": task_events,
    }
    return export_data


def suggested_export_filename(export_data: Dict[str, Any], suffix: str = "json") -> str:
    exp = export_data["experiments"][0]
    exp_id = exp["id"]
    exp_name = str(exp.get("name") or "exp")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(c for c in exp_name if c.isalnum() or c in (" ", "-", "_")).rstrip()
    safe = safe.replace(" ", "_") or "experiment"
    return f"experiment_{exp_id}_{safe}_{ts}.{suffix}"
