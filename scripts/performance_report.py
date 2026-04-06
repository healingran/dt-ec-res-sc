# scripts/performance_report.py
import pandas as pd
import numpy as np

def generate_performance_report(basic_data, lstm_data):
    """生成性能对比报告（包含负载、时延、能耗估算）"""
    
    # 计算各项指标
    avg_basic = np.mean(basic_data)
    avg_lstm = np.mean(lstm_data)
    
    max_basic = np.max(basic_data)
    max_lstm = np.max(lstm_data)
    
    std_basic = np.std(basic_data)
    std_lstm = np.std(lstm_data)
    
    # 时延估算（负载越高时延越大，模拟线性关系）
    delay_basic = avg_basic * 0.5  # 模拟时延 ms
    delay_lstm = avg_lstm * 0.5
    
    # 能耗估算（负载与能耗成正比）
    energy_basic = avg_basic * 0.8  # 模拟能耗 W
    energy_lstm = avg_lstm * 0.8
    
    # 改善率
    improvement_avg = (avg_basic - avg_lstm) / avg_basic * 100 if avg_basic > 0 else 0
    improvement_delay = (delay_basic - delay_lstm) / delay_basic * 100 if delay_basic > 0 else 0
    improvement_energy = (energy_basic - energy_lstm) / energy_basic * 100 if energy_basic > 0 else 0
    
    # 创建对比表
    comparison_table = pd.DataFrame({
        '指标': ['平均负载 (%)', '峰值负载 (%)', '负载标准差', '平均时延 (ms)', '估算能耗 (W)'],
        '基础调度': [f"{avg_basic:.2f}", f"{max_basic:.2f}", f"{std_basic:.2f}", f"{delay_basic:.2f}", f"{energy_basic:.2f}"],
        'LSTM预测调度': [f"{avg_lstm:.2f}", f"{max_lstm:.2f}", f"{std_lstm:.2f}", f"{delay_lstm:.2f}", f"{energy_lstm:.2f}"],
        '改善率 (%)': [f"{improvement_avg:.1f}%", 
                      f"{(max_basic - max_lstm) / max_basic * 100:.1f}%" if max_basic > 0 else "N/A",
                      f"{(std_basic - std_lstm) / std_basic * 100:.1f}%" if std_basic > 0 else "N/A",
                      f"{improvement_delay:.1f}%",
                      f"{improvement_energy:.1f}%"]
    })
    
    print("\n" + "="*70)
    print("性能对比报告 - 基础调度 vs LSTM预测调度")
    print("="*70)
    print(comparison_table.to_string(index=False))
    print("="*70)
    
    # 保存到 CSV
    comparison_table.to_csv("algorithms/output/performance_comparison.csv", index=False)
    print("\n✅ 对比表已保存: algorithms/output/performance_comparison.csv")
    
    return comparison_table