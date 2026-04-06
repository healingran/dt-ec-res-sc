# test_api.py
import requests
import time

BASE = "http://127.0.0.1:8000"

print("="*50)
print("智能边缘计算调度系统 - API测试")
print("="*50)

# 1. 查看节点状态
print("\n1. 节点状态:")
resp = requests.get(f"{BASE}/nodes").json()
for node in resp['nodes']:
    print(f"   {node['name']}: CPU={node['cpu']}%, MEM={node['mem']}%")

# 2. 创建任务
print("\n2. 创建任务:")
resp = requests.post(f"{BASE}/task?cpu_need=15").json()
print(f"   {resp['message']}: {resp['task']}")

# 3. 执行最小负载调度
print("\n3. 执行调度 (least_load):")
resp = requests.post(f"{BASE}/schedule?strategy=least_load").json()
print(f"   {resp['message']}")
print(f"   策略: {resp['strategy']}")
print(f"   分配到: {resp['node_name']}, CPU: {resp['node_cpu_before']}% -> {resp['node_cpu_after']}%")

# 4. 查看预测
print("\n4. LSTM负载预测 (未来5步):")
resp = requests.get(f"{BASE}/predict?steps=5").json()
print(f"   步数: {resp['steps']}")
print(f"   预测负载: {resp['predicted_load']}")

# 5. 查看任务队列
print("\n5. 任务队列:")
resp = requests.get(f"{BASE}/tasks").json()
print(f"   待处理任务数: {resp['pending_tasks']}")
for task in resp['tasks']:
    print(f"   Task {task['id']}: CPU需求={task['cpu_need']}, 状态={task['status']}")

# 6. 测试预测调度策略
print("\n6. 执行调度 (predictive - LSTM预测调度):")
requests.post(f"{BASE}/task?cpu_need=10")
resp = requests.post(f"{BASE}/schedule?strategy=predictive").json()
print(f"   {resp['message']}")
print(f"   策略: {resp['strategy']}")
print(f"   分配到: {resp['node_name']}, CPU: {resp['node_cpu_before']}% -> {resp['node_cpu_after']}%")

# 7. 重置系统
print("\n7. 重置系统:")
resp = requests.post(f"{BASE}/reset").json()
print(f"   {resp['message']}")

print("\n" + "="*50)
print("✅ 所有测试通过！")
print("="*50)