# test_model_loading.py
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*50)
print("测试模型加载和预测")
print("="*50)

# 测试模型加载
from algorithms.predictor import model, scaler, get_predictions

print(f"\n模型状态: {'✅ 已加载' if model else '❌ 未加载'}")
print(f"Scaler状态: {'✅ 已加载' if scaler else '❌ 未加载'}")

# 测试预测
from backend.dashboard_state import CPU_HISTORY
CPU_HISTORY.clear()

# 模拟历史数据
for i in range(30):
    CPU_HISTORY.append(50 + i * 0.5)

print(f"\n历史数据 (最后10个): {list(CPU_HISTORY)[-10:]}...")

pred = get_predictions(steps=5)
print(f"\n预测结果:")
print(f"  Steps: {pred['steps']}")
print(f"  Loads: {pred['predicted_load']}")

print("\n✅ 测试完成")