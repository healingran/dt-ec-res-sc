# test_arrival_prediction.py
import requests
import time

BASE = "http://127.0.0.1:8000"

print("="*60)
print("潮汐到达率预测测试")
print("="*60)

# 1. 查看任务统计
print("\n1. 任务统计信息:")
resp = requests.get(f"{BASE}/api/v1/task_stats").json()
print(f"   总生成任务: {resp['total_generated']}")
print(f"   平峰任务: {resp['offpeak_count']} ({resp['offpeak_ratio']}%)")
print(f"   潮汐任务: {resp['tidal_count']} ({resp['tidal_ratio']}%)")
print(f"   事故任务: {resp['incident_count']} ({resp['incident_ratio']}%)")
print(f"   预测超时: {resp['predicted_timeout']} ({resp['timeout_ratio']}%)")
print(f"   当前队列: {resp['queue_length']}")

# 2. 测试到达率预测
print("\n2. 到达率预测:")
resp = requests.get(f"{BASE}/api/v1/predict_arrival?steps=5").json()
if "error" in resp:
    print(f"   {resp['error']}")
else:
    print(f"   当前到达率: {resp['current_rate']} 任务/分钟")
    print(f"   趋势: {resp['trend']} (斜率: {resp['slope']})")
    print(f"   预测值:")
    for step, rate in zip(resp['steps'], resp['predicted_rates']):
        print(f"     {step}分钟后: {rate} 任务/分钟")

# 3. 等待几秒后再次测试（查看变化）
print("\n3. 等待5秒后重新测试...")
time.sleep(5)

resp = requests.get(f"{BASE}/api/v1/predict_arrival?steps=3").json()
if "error" not in resp:
    print(f"\n   新到达率: {resp['current_rate']} 任务/分钟")
    print(f"   趋势: {resp['trend']}")
    print(f"   预测: {resp['predicted_rates']}")

# 4. 重置统计（可选）
print("\n4. 重置统计:")
resp = requests.post(f"{BASE}/api/v1/reset_stats").json()
print(f"   {resp['message']}")

print("\n" + "="*60)
print("测试完成！")