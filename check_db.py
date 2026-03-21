import sqlite3

conn = sqlite3.connect('smart_city.db')
c = conn.cursor()

# 列出所有表
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = c.fetchall()
print('📁 数据库中的表有：', tables)

# 检查 nodes 表结构
c.execute('PRAGMA table_info(nodes)')
print('\n📄 `nodes` 表结构：')
for col in c.fetchall():
    print(f'  - {col[1]} ({col[2]})')

conn.close()