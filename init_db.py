import sqlite3


def create_tables(db_path: str = "smart_city.db") -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

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

    cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_node_name ON nodes(node_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_timestamp ON nodes(timestamp)")

    conn.commit()
    conn.close()
    print("✅ 数据库表结构创建成功！")


if __name__ == "__main__":
    create_tables()

