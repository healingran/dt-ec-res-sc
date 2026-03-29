import sqlite3


def check(db_path: str = "smart_city.db") -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print("📁 数据库中的表有：", tables)

    cur.execute("PRAGMA table_info(nodes)")
    print("\n📄 `nodes` 表结构：")
    for col in cur.fetchall():
        print(f"  - {col[1]} ({col[2]})")

    cur.execute("PRAGMA table_info(experiment)")
    print("\n📄 `experiment` 表结构：")
    for col in cur.fetchall():
        print(f"  - {col[1]} ({col[2]})")

    conn.close()


if __name__ == "__main__":
    check()

