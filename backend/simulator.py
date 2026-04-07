# backend/simulator.py
import random
import time
import threading
from backend.models import nodes  # 注意这里的路径变化！
from backend.database import init_db, save_node_load
from backend.ws_manager import manager as ws_manager
from algorithms.predictor import get_predictions
from algorithms.realtime_predictor import default_predictor

def _simulate_logic():
    init_db()
    rt_predictor = default_predictor()
    while True:
        for node in nodes:
            if node["status"] == "online":
                node["cpu"] = round(max(0, min(100, node["cpu"] + random.uniform(-2, 2))), 1)
                node["mem"] = round(max(0, min(100, node["mem"] + random.uniform(-2, 2))), 1)
                # 在线预测：仅记录 tracked 节点（默认 id=1）的 CPU，避免多节点交替写入污染序列
                try:
                    nid = node.get("id")
                    if nid is not None:
                        rt_predictor.update(node["cpu"], node_id=int(nid))
                except Exception:
                    pass
                # 模拟任务处理：每个周期队列长度衰减（不会一直累积）
                if "queue_len" in node:
                    node["queue_len"] = max(0, int(node["queue_len"]) - random.randint(0, 2))

            # 持久化节点快照
            try:
                save_node_load(
                    name=node["name"],
                    cpu=node["cpu"],
                    mem=node["mem"],
                    status=node["status"],
                )
            except Exception:
                # 持久化失败不阻断模拟器
                pass

        # 获取预测负载（王瑾的 LSTM /predict 逻辑）
        predicted_load = []
        steps = []
        try:
            pred = get_predictions(steps=10)
            predicted_load = pred.get("predicted_load", []) or []
            steps = pred.get("steps", []) or []
        except Exception:
            pass

        # 推送给 WebSocket 客户端（包含 cpu/mem/status + predicted_load）
        snapshot = {
            "timestamp": time.time(),
            "nodes": [
                {
                    "id": n.get("id"),
                    "name": n.get("name"),
                    "cpu": n.get("cpu"),
                    "mem": n.get("mem"),
                    "status": n.get("status"),
                }
                for n in nodes
            ],
            "predicted": {"steps": steps, "predicted_load": predicted_load},
        }
        ws_manager.broadcast_threadsafe(snapshot)
        time.sleep(2)

def start_simulator():
    daemon_thread = threading.Thread(target=_simulate_logic, daemon=True)
    daemon_thread.start()
    print(">>> 负载模拟器已启动...")