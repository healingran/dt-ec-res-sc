import sqlite3


def create_tables(db_path: str = "smart_city.db") -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

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
    print("✅ 数据库表结构创建成功！")


if __name__ == "__main__":
    create_tables()

