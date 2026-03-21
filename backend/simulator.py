<<<<<<< HEAD
# backend/simulator.py
import random
import time
import threading
from backend.models import nodes  # 注意这里的路径变化！

def _simulate_logic():
    while True:
        for node in nodes:
            if node["status"] == "online":
                node["cpu"] = round(max(0, min(100, node["cpu"] + random.uniform(-2, 2))), 1)
                node["mem"] = round(max(0, min(100, node["mem"] + random.uniform(-2, 2))), 1)
        time.sleep(2)

def start_simulator():
    daemon_thread = threading.Thread(target=_simulate_logic, daemon=True)
    daemon_thread.start()
=======
# backend/simulator.py
import random
import time
import threading
from backend.models import nodes  # 注意这里的路径变化！

def _simulate_logic():
    while True:
        for node in nodes:
            if node["status"] == "online":
                node["cpu"] = round(max(0, min(100, node["cpu"] + random.uniform(-2, 2))), 1)
                node["mem"] = round(max(0, min(100, node["mem"] + random.uniform(-2, 2))), 1)
        time.sleep(2)

def start_simulator():
    daemon_thread = threading.Thread(target=_simulate_logic, daemon=True)
    daemon_thread.start()
>>>>>>> 401a1f2ae0766c497231bc734755250693c7e6b2
    print(">>> 负载模拟器已启动...")