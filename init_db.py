import sqlite3

def create_tables():
    conn = sqlite3.connect('smart_city.db')
    cursor = conn.cursor()

    # 创建 nodes 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_name TEXT NOT NULL UNIQUE,
            load REAL DEFAULT 0.0,
            timestamp REAL NOT NULL
        )
    ''')

    # 创建 experiment 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_name TEXT NOT NULL,
            start_time REAL NOT NULL,
            status TEXT DEFAULT 'running'
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ 数据库表结构创建成功！")

if __name__ == '__main__':
    create_tables()