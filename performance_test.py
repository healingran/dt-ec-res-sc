# performance_test.py
import os
import requests
import time
import matplotlib.pyplot as plt
import numpy as np

# 基础配置
BASE_URL = "http://127.0.0.1:8000"
TEST_TASKS = 20

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

def reset_backend():
    """重置后端状态（通过重启模拟器的方式）"""
    try:
        # 清空任务队列
        requests.post(f"{BASE_URL}/reset")
        return True
    except:
        return False

def run_test(strategy, test_name):
    """运行单个测试"""
    print(f"\n开始测试: {test_name} (策略: {strategy})")
    load_history = []
    
    for i in range(TEST_TASKS):
        try:
            # 创建任务
            requests.post(f"{BASE_URL}/task?cpu_need=10")
            # 执行调度
            resp = requests.post(f"{BASE_URL}/schedule?strategy={strategy}").json()
            # 获取节点状态
            nodes_data = requests.get(f"{BASE_URL}/nodes").json()["nodes"]
            max_load = max([n["cpu"] for n in nodes_data])
            load_history.append(max_load)
            print(f"  Task {i+1:2d}/{TEST_TASKS}: Max Load {max_load:5.1f}% | Node: {resp.get('node_id', 'N/A')}")
            time.sleep(0.5)
        except Exception as e:
            print(f"  Task {i+1} failed: {e}")
            load_history.append(np.nan)
    
    return [x for x in load_history if not np.isnan(x)]

if __name__ == "__main__":
    # 创建输出目录
    os.makedirs("algorithms/output", exist_ok=True)
    
    print("="*60)
    print("调度策略性能对比测试")
    print("="*60)
    print(f"测试任务数: {TEST_TASKS}")
    print(f"API地址: {BASE_URL}")
    print("="*60)
    
    try:
        # 测试1：基础调度
        print("\n" + "="*60)
        print("第1轮：基础调度测试")
        print("="*60)
        res_basic = run_test("least_load", "基础调度")
        
        # 等待系统稳定
        time.sleep(3)
        
        # 测试2：LSTM调度（需要先重置后端）
        print("\n" + "="*60)
        print("第2轮：LSTM预测调度测试")
        print("="*60)
        print("注意：请手动重启后端以重置节点状态")
        print("请在另一个终端按 Ctrl+C 停止后端，然后重新运行 python main.py")
        print("完成后按 Enter 继续...")
        input()
        
        res_lstm = run_test("predictive", "LSTM预测调度")
        
        # 计算统计数据
        avg_basic = np.mean(res_basic)
        avg_lstm = np.mean(res_lstm)
        max_basic = np.max(res_basic)
        max_lstm = np.max(res_lstm)
        
        # 画图
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # 左图：负载变化趋势
        ax1.plot(res_basic, label='基础调度', marker='o', linewidth=2, markersize=4)
        ax1.plot(res_lstm, label='LSTM预测调度', marker='s', linewidth=2, markersize=4)
        ax1.set_xlabel('任务序号')
        ax1.set_ylabel('系统峰值负载 (%)')
        ax1.set_title('负载变化趋势对比')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 右图：箱线图对比
        data_to_plot = [res_basic, res_lstm]
        ax2.boxplot(data_to_plot, tick_labels=['基础调度', 'LSTM预测调度'])
        ax2.set_ylabel('负载 (%)')
        ax2.set_title('负载分布对比')
        ax2.grid(True, alpha=0.3)
        
        # 添加统计信息
        improvement_avg = (avg_basic - avg_lstm) / avg_basic * 100 if avg_basic > 0 else 0
        improvement_max = (max_basic - max_lstm) / max_basic * 100 if max_basic > 0 else 0
        
        plt.suptitle(f'调度策略性能对比报告\n'
                    f'基础调度: 平均负载 {avg_basic:.1f}%, 峰值 {max_basic:.1f}%\n'
                    f'LSTM调度: 平均负载 {avg_lstm:.1f}%, 峰值 {max_lstm:.1f}%\n'
                    f'改善率: 平均降低 {improvement_avg:.1f}%, 峰值降低 {improvement_max:.1f}%',
                    fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        # 保存报告
        save_path = "algorithms/output/performance_report.png"
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n✅ 性能对比报告已生成：{save_path}")
        
        # 保存数据
        import pandas as pd
        df = pd.DataFrame({
            'task_index': range(1, len(res_basic)+1),
            'basic_schedule': res_basic,
            'lstm_schedule': res_lstm
        })
        df.to_csv("algorithms/output/performance_data.csv", index=False)
        print(f"✅ 性能数据已保存：algorithms/output/performance_data.csv")
        # 在 performance_test.py 最后，plt.show() 之前添加
        from scripts.performance_report import generate_performance_report

        # 生成性能对比报告
        generate_performance_report(res_basic, res_lstm)
        plt.show()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()