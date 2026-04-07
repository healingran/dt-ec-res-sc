import sqlite3
import csv

def export_sample_data(db_path="smart_city.db", output_file="sample_nodes_data.csv"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    query = """
    SELECT e.experiment_name, n.node_name, n.cpu, n.mem, n.status, n.timestamp 
    FROM nodes n JOIN experiment e ON n.experiment_id = e.id LIMIT 50;
    """
    cur.execute(query)
    rows = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(column_names)
        writer.writerows(rows)
            
    conn.close()
    print(f"✅ 样例数据已导出至：{output_file}")

if __name__ == "__main__":
    export_sample_data()