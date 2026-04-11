#!/usr/bin/env python3
"""
实验运行脚本
扩展实验体系，运行多个实验并收集KPI
"""
import sys
import os
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.experiment_kpi import ExperimentKPI

def run_single_experiment(experiment_id: int, output_dir: str = "experiment_results") -> Dict[str, Any]:
    """
    运行单个实验并计算KPI
    
    参数:
        experiment_id: 实验ID
        output_dir: 输出目录
    
    返回:
        实验KPI结果
    """
    print(f"开始分析实验 {experiment_id}")
    print("-" * 50)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 计算KPI
    kpi_calculator = ExperimentKPI()
    
    try:
        kpis = kpi_calculator.calculate_experiment_kpis(experiment_id)
        
        if "error" in kpis:
            print(f"实验 {experiment_id} 分析失败: {kpis['error']}")
            return {}
        
        # 打印关键指标
        summary = kpis.get("summary", {}).get("key_metrics", {})
        print("关键指标:")
        for metric, value in summary.items():
            if isinstance(value, float):
                print(f"  {metric}: {value:.4f}")
            else:
                print(f"  {metric}: {value}")
        
        # 导出结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exp_name = kpis.get("experiment_info", {}).get("experiment_name", f"exp_{experiment_id}")
        exp_name_safe = "".join(c for c in exp_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        exp_name_safe = exp_name_safe.replace(' ', '_')
        
        # JSON导出
        json_file = os.path.join(output_dir, f"kpi_{exp_name_safe}_{timestamp}.json")
        kpi_calculator.export_to_json(kpis, json_file)
        
        # CSV导出
        csv_prefix = os.path.join(output_dir, f"kpi_{exp_name_safe}")
        kpi_calculator.export_to_csv(kpis, csv_prefix)
        
        print(f"实验 {experiment_id} 分析完成")
        print()
        
        return kpis
        
    finally:
        kpi_calculator.close()

def run_multiple_experiments(experiment_ids: List[int], output_dir: str = "experiment_results") -> None:
    """
    运行多个实验并生成汇总报告
    
    参数:
        experiment_ids: 实验ID列表
        output_dir: 输出目录
    """
    print("=" * 60)
    print("实验体系运行器")
    print(f"输出目录: {output_dir}")
    print(f"实验数量: {len(experiment_ids)}")
    print("=" * 60)
    
    all_results = []
    
    for exp_id in experiment_ids:
        result = run_single_experiment(exp_id, output_dir)
        if result:
            all_results.append({
                "experiment_id": exp_id,
                "experiment_name": result.get("experiment_info", {}).get("experiment_name", ""),
                "kpis": result.get("summary", {}).get("key_metrics", {})
            })
    
    # 生成对比报告
    if all_results:
        generate_comparison_report(all_results, output_dir)
    
    print("所有实验分析完成！")

def generate_comparison_report(results: List[Dict[str, Any]], output_dir: str) -> None:
    """生成实验对比报告"""
    import csv
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f"experiment_comparison_{timestamp}.csv")
    
    all_metrics = set()
    for result in results:
        all_metrics.update(result["kpis"].keys())
    
    with open(report_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        header = ["experiment_id", "experiment_name"] + sorted(list(all_metrics))
        writer.writerow(header)
 
        for result in results:
            row = [
                result["experiment_id"],
                result["experiment_name"]
            ]
            
            for metric in sorted(list(all_metrics)):
                row.append(result["kpis"].get(metric, ""))
            
            writer.writerow(row)
    
    print(f"实验对比报告已生成: {report_file}")

def find_available_experiments(db_path: str = "smart_city.db") -> List[int]:
    """查找数据库中可用的实验"""
    import sqlite3
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return []
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id FROM experiment WHERE status = 'finished' ORDER BY id")
        experiments = [row[0] for row in cur.fetchall()]
        
        if experiments:
            print(f"找到 {len(experiments)} 个已完成的实验: {experiments}")
        else:
            print("未找到已完成的实验")
            print("提示: 可以运行 scripts/generate_sample_data.py 生成测试数据")
        
        return experiments
    finally:
        conn.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="实验体系运行器")
    parser.add_argument(
        "--experiment-ids",
        type=int,
        nargs="+",
        help="要分析的实验ID列表"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="分析所有已完成的实验"
    )
    parser.add_argument(
        "--output-dir",
        default="experiment_results",
        help="输出目录（默认: experiment_results）"
    )
    
    args = parser.parse_args()

    if args.all:
        experiment_ids = find_available_experiments()
        if not experiment_ids:
            print("没有可分析的实验")
            sys.exit(1)
    elif args.experiment_ids:
        experiment_ids = args.experiment_ids
    else:
        # 默认分析最近一个实验
        experiment_ids = find_available_experiments()
        if experiment_ids:
            experiment_ids = [experiment_ids[-1]]  # 取最近一个
            print(f"默认分析最近一个实验: {experiment_ids[0]}")
        else:
            print("没有可分析的实验")
            sys.exit(1)
    
    # 运行实验
    run_multiple_experiments(experiment_ids, args.output_dir)

if __name__ == "__main__":
    main()