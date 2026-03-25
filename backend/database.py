import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple


DB_PATH = "smart_city.db"


def get_db_connection(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str = DB_PATH) -> None:
    conn = get_db_connection(path)
    cur = conn.cursor()

    # 1) experiment：增加 end_time（支持按时间窗口查询历史）
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS experiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_name TEXT NOT NULL,
            start_time REAL,
            end_time REAL,
            status TEXT DEFAULT 'created'
        )
        """
    )
    cur.execute("PRAGMA table_info(experiment)")
    exp_info = cur.fetchall()
    exp_cols = {row[1] for row in exp_info}
    if "end_time" not in exp_cols:
        cur.execute("ALTER TABLE experiment ADD COLUMN end_time REAL")
    if "start_time" not in exp_cols:
        cur.execute("ALTER TABLE experiment ADD COLUMN start_time REAL")
    # 若旧表对 start_time 有 NOT NULL 约束（历史版本），则迁移为允许 NULL 的结构
    start_time_notnull = False
    for row in exp_info:
        # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
        if row[1] == "start_time" and int(row[3]) == 1:
            start_time_notnull = True
            break
    if start_time_notnull:
        cur.execute("ALTER TABLE experiment RENAME TO experiment_legacy")
        cur.execute(
            """
            CREATE TABLE experiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_name TEXT NOT NULL,
                start_time REAL,
                end_time REAL,
                status TEXT DEFAULT 'created'
            )
            """
        )
        try:
            cur.execute(
                """
                INSERT INTO experiment (id, experiment_name, start_time, status)
                SELECT id, experiment_name, start_time, status FROM experiment_legacy
                """
            )
        except sqlite3.Error:
            pass
        cur.execute("DROP TABLE experiment_legacy")

    # 2) nodes：历史快照表（允许同一 node_name 多条记录）
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_name TEXT NOT NULL,
            cpu REAL NOT NULL,
            mem REAL NOT NULL,
            status TEXT NOT NULL,
            timestamp REAL NOT NULL
        )
        """
    )

    # 若旧表存在 UNIQUE(node_name) 约束，则迁移为历史表结构
    cur.execute("PRAGMA index_list(nodes)")
    idx_rows = cur.fetchall()
    has_unique_node_name = False
    for r in idx_rows:
        # PRAGMA index_list: (seq, name, unique, origin, partial)
        idx_name = r[1]
        is_unique = bool(r[2])
        if not is_unique:
            continue
        cur.execute(f"PRAGMA index_info({idx_name})")
        cols = [x[2] for x in cur.fetchall()]
        if cols == ["node_name"]:
            has_unique_node_name = True
            break

    if has_unique_node_name:
        cur.execute("ALTER TABLE nodes RENAME TO nodes_legacy")
        cur.execute(
            """
            CREATE TABLE nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_name TEXT NOT NULL,
                cpu REAL NOT NULL,
                mem REAL NOT NULL,
                status TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
            """
        )
        # 尽最大努力迁移旧数据（若旧表字段匹配）
        try:
            cur.execute(
                """
                INSERT INTO nodes (node_name, cpu, mem, status, timestamp)
                SELECT node_name, cpu, mem, status, timestamp FROM nodes_legacy
                """
            )
        except sqlite3.Error:
            pass
        cur.execute("DROP TABLE nodes_legacy")

    # 索引：加速按 node_name/time_window 查询
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_node_name ON nodes(node_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_timestamp ON nodes(timestamp)")

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
        INSERT INTO nodes (node_name, cpu, mem, status, timestamp)
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


def create_experiment(experiment_name: str, path: str = DB_PATH) -> Dict[str, Any]:
    init_db(path)
    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO experiment (experiment_name, status)
        VALUES (?, 'created')
        """,
        (experiment_name,),
    )
    conn.commit()
    exp_id = cur.lastrowid
    conn.close()
    return get_experiment(exp_id, path=path)


def start_experiment(experiment_id: int, path: str = DB_PATH) -> Dict[str, Any]:
    init_db(path)
    conn = get_db_connection(path)
    cur = conn.cursor()
    now = time.time()
    cur.execute(
        """
        UPDATE experiment
        SET start_time = ?, status = 'running'
        WHERE id = ?
        """,
        (now, int(experiment_id)),
    )
    conn.commit()
    conn.close()
    return get_experiment(experiment_id, path=path)


def stop_experiment(experiment_id: int, path: str = DB_PATH) -> Dict[str, Any]:
    init_db(path)
    conn = get_db_connection(path)
    cur = conn.cursor()
    now = time.time()
    cur.execute(
        """
        UPDATE experiment
        SET end_time = ?, status = 'stopped'
        WHERE id = ?
        """,
        (now, int(experiment_id)),
    )
    conn.commit()
    conn.close()
    return get_experiment(experiment_id, path=path)


def get_experiment(experiment_id: int, path: str = DB_PATH) -> Dict[str, Any]:
    init_db(path)
    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM experiment WHERE id = ?", (int(experiment_id),))
    row = cur.fetchone()
    conn.close()
    if row is None:
        raise KeyError(f"experiment {experiment_id} not found")
    return dict(row)


def list_experiments(path: str = DB_PATH) -> List[Dict[str, Any]]:
    init_db(path)
    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM experiment ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_nodes_history(
    experiment_id: int,
    limit: int = 500,
    offset: int = 0,
    path: str = DB_PATH,
) -> Dict[str, Any]:
    exp = get_experiment(experiment_id, path=path)
    start_time = exp.get("start_time")
    end_time = exp.get("end_time")
    if start_time is None:
        raise ValueError("experiment has not been started")
    if end_time is None:
        end_time = time.time()

    conn = get_db_connection(path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM nodes
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        LIMIT ? OFFSET ?
        """,
        (float(start_time), float(end_time), int(limit), int(offset)),
    )
    rows = cur.fetchall()
    conn.close()
    return {"experiment": exp, "nodes": [dict(r) for r in rows]}

