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

# 保证从项目根目录执行时可导入 backend
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.experiment_export_last import (  # noqa: E402
    build_last_experiment_export_dict,
    suggested_export_filename,
)


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
        export_data = build_last_experiment_export_dict(db_path)
        export_data["export_info"]["format"] = output_format

        exp0 = export_data["experiments"][0]
        exp_id = exp0["id"]
        exp_name = exp0["name"]
        node_count = export_data["export_info"]["node_count"]

        print(f"✅ 找到实验记录:")
        print(f"   - ID: {exp_id}")
        print(f"   - 名称: {exp_name}")
        print(f"   - 状态: {exp0['status']}")
        print(f"   - 时间范围: {exp0['start_time']} 到 {exp0['end_time']}")
        print(f"📊 共找到 {node_count} 条节点记录")

        filename = suggested_export_filename(export_data, output_format)
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

    except ValueError as e:
        print(f"❌ {e}")
        print("提示：请确保有 status IN ('stopped','finished') 且 end_time 不为空的实验记录")
        sys.exit(1)
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