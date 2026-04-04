import sqlite3
import time
import random

def generate_sample_data(db_path="smart_city.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. 插入实验记录
    cur.execute("INSERT INTO experiment (experiment_name, start_time, status) VALUES (?, ?, ?)", 
                ("压力测试_2026-04-03", time.time() - 3600, "running"))
    exp_id = cur.lastrowid 

    # 2. 插入节点监控数据
    node_names = ["node-001", "node-002", "node-003", "node-004"]
    base_time = time.time() - 3600 

    for i in range(100): 
        for node in node_names:
            cur.execute(
                "INSERT INTO nodes (experiment_id, node_name, cpu, mem, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (exp_id, node, round(random.uniform(10, 90), 1), round(random.uniform(20, 80), 1), 
                 "online", base_time + i * 60)
            )

    conn.commit()
    conn.close()
    print(f"✅ 样例数据生成完成！关联实验 ID: {exp_id}")

if __name__ == "__main__":
    generate_sample_data()