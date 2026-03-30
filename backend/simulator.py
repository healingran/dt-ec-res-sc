# backend/simulator.py
import random
import time
import threading
from backend.models import nodes
from algorithms.predictor import update_node_history

def _simulate_logic():
    while True:
        for node in nodes:
            if node["status"] == "online":
                # 模拟负载波动
                new_cpu = node["cpu"] + random.uniform(-2, 2)
                node["cpu"] = round(max(0, min(100, new_cpu)), 1)
                
                new_mem = node["mem"] + random.uniform(-2, 2)
                node["mem"] = round(max(0, min(100, new_mem)), 1)
        
        # 更新节点1的历史数据（用于预测）
        node1 = next((n for n in nodes if n.get("id") == 1), None)
        if node1:
            update_node_history(node1["cpu"])
        
        time.sleep(2)

def start_simulator():
    daemon_thread = threading.Thread(target=_simulate_logic, daemon=True)
    daemon_thread.start()
    print(">>> 负载模拟器已启动...")