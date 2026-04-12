#!/usr/bin/env python3
"""
实验结果导出工具
功能：从数据库中导出最近一次完成的实验及其节点历史数据
支持格式：JSON 和 CSV
"""

import sqlite3
import json
import csv
import argparse
from datetime import datetime
import os
import sys

def export_last_experiment(
    db_path: str = "smart_city.db",
    output_format: str = "json",
    output_dir: str = "output"
) -> None:
    """
    导出最近一次完成的实验数据
    
    Args:
        db_path: SQLite 数据库文件路径
        output_format: 输出格式，支持 'json' 或 'csv'
        output_dir: 输出目录
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 允许以字典形式访问行
        cur = conn.cursor()
        
        # 1. 获取最近一次已结束的实验（主线 stop_experiment 写入 'stopped'；兼容旧数据 'finished'）
        cur.execute("""
            SELECT id, experiment_name, start_time, end_time, status
            FROM experiment
            WHERE status IN ('stopped', 'finished') AND end_time IS NOT NULL
            ORDER BY end_time DESC
            LIMIT 1
        """)
        
        exp_row = cur.fetchone()
        
        if not exp_row:
            print("❌ 未找到已完成的实验记录")
            print("提示：请确保有 status IN ('stopped','finished') 且 end_time 不为空的实验记录")
            sys.exit(1)
        
        exp_data = dict(exp_row)
        exp_id = exp_data['id']
        exp_name = exp_data['experiment_name']
        
        print(f"✅ 找到实验记录:")
        print(f"   - ID: {exp_id}")
        print(f"   - 名称: {exp_name}")
        print(f"   - 状态: {exp_data['status']}")
        print(f"   - 时间范围: {exp_data['start_time']} 到 {exp_data['end_time']}")
        
        # 2. 获取该实验期间的节点记录
        cur.execute("""
            SELECT node_name, cpu, mem, status, timestamp
            FROM nodes
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """, (exp_data['start_time'], exp_data['end_time']))
        
        node_rows = cur.fetchall()
        node_count = len(node_rows)
        print(f"📊 共找到 {node_count} 条节点记录")
        
        if node_count == 0:
            print("⚠️  警告：该实验没有找到节点记录")
            # 如果没有节点记录，查找所有节点记录
            cur.execute("""
                SELECT node_name, cpu, mem, status, timestamp
                FROM nodes
                ORDER BY timestamp ASC
            """)
            node_rows = cur.fetchall()
            node_count = len(node_rows)
            print(f"📊 改为导出所有节点记录：{node_count} 条")
        
        # 2b. 同一时间窗内的任务事件历史（若表存在）
        task_events = []
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

        # 3. 构建导出数据结构
        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "format": output_format,
                "experiment_count": 1,
                "node_count": node_count,
                "tasks_history_count": len(task_events),
            },
            "experiments": [{
                "id": exp_data['id'],
                "name": exp_data['experiment_name'],
                "start_time": exp_data['start_time'],
                "end_time": exp_data['end_time'],
                "status": exp_data['status']
            }],
            "nodes": [
                {
                    "node_name": row['node_name'],
                    "cpu": row['cpu'],
                    "mem": row['mem'],
                    "status": row['status'],
                    "timestamp": row['timestamp']
                }
                for row in node_rows
            ],
            "tasks_history": task_events,
        }
        
        # 4. 生成文件名
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in exp_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        filename = f"experiment_{exp_id}_{safe_name}_{timestamp_str}.{output_format}"
        filepath = os.path.join(output_dir, filename)
        
        # 5. 导出文件
        if output_format == "json":
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            print(f"📄 JSON 文件已导出：{filepath}")
            print(f"   文件大小：{os.path.getsize(filepath):,} 字节")
            
        elif output_format == "csv":
            # 创建两个 CSV 文件：一个实验信息，一个节点信息
            exp_filepath = filepath.replace('.csv', '_experiments.csv')
            nodes_filepath = filepath.replace('.csv', '_nodes.csv')
            
            # 导出实验信息
            with open(exp_filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "name", "start_time", "end_time", "status"])
                writer.writeheader()
                writer.writerow(export_data["experiments"][0])
            print(f"📄 实验信息 CSV 已导出：{exp_filepath}")
            
            # 导出节点信息
            with open(nodes_filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["experiment_id", "experiment_name", "node_name", "cpu", "mem", "status", "timestamp"])
                writer.writeheader()
                for node in export_data["nodes"]:
                    writer.writerow({
                        "experiment_id": exp_id,
                        "experiment_name": exp_name,
                        "node_name": node["node_name"],
                        "cpu": node["cpu"],
                        "mem": node["mem"],
                        "status": node["status"],
                        "timestamp": node["timestamp"]
                    })
            print(f"📄 节点信息 CSV 已导出：{nodes_filepath}")

            if export_data.get("tasks_history"):
                th_filepath = filepath.replace(".csv", "_tasks_history.csv")
                with open(th_filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=[
                            "experiment_id",
                            "task_id",
                            "status",
                            "node_name",
                            "timestamp",
                        ],
                    )
                    writer.writeheader()
                    for ev in export_data["tasks_history"]:
                        writer.writerow(
                            {
                                "experiment_id": exp_id,
                                "task_id": ev.get("task_id"),
                                "status": ev.get("status"),
                                "node_name": ev.get("node_name"),
                                "timestamp": ev.get("timestamp"),
                            }
                        )
                print(f"📄 任务事件 CSV 已导出：{th_filepath}")
            
        else:
            print(f"❌ 不支持的格式：{output_format}")
            print("   支持格式：json, csv")
            sys.exit(1)
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ 数据库错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 导出过程中出错: {e}")
        sys.exit(1)

def main():
    """主函数：解析命令行参数并执行导出"""
    parser = argparse.ArgumentParser(
        description="导出最近一次完成的实验数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 导出为 JSON（默认）
  python export_last_experiment.py
  
  # 导出为 CSV
  python export_last_experiment.py --format csv
  
  # 指定数据库路径
  python export_last_experiment.py --db-path /path/to/database.db
  
  # 指定输出目录
  python export_last_experiment.py --output-dir exports
        """
    )
    
    parser.add_argument(
        "--db-path",
        default="smart_city.db",
        help="SQLite 数据库文件路径（默认：smart_city.db）"
    )
    
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="输出格式：json 或 csv（默认：json）"
    )
    
    parser.add_argument(
        "--output-dir",
        default="output",
        help="输出目录（默认：output）"
    )
    
    args = parser.parse_args()
    
    print("🚀 开始导出实验数据...")
    print("=" * 50)
    print(f"数据库: {args.db_path}")
    print(f"输出格式: {args.format}")
    print(f"输出目录: {args.output_dir}")
    print("=" * 50)
    
    export_last_experiment(
        db_path=args.db_path,
        output_format=args.format,
        output_dir=args.output_dir
    )

if __name__ == "__main__":
    main()