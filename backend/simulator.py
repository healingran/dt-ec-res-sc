# backend/simulator.py
import random
import time
import threading
from datetime import datetime
from collections import deque
from backend.models import nodes, tasks, task_counter
from backend.database import init_db, save_node_load
from backend.ws_manager import manager as ws_manager
from algorithms.predictor import get_predictions
from algorithms.realtime_predictor import default_predictor
from backend.tasks_history import record_task_arrival, task_public_id

# 任务统计
task_stats = {
    "total_generated": 0,
    "offpeak_count": 0,
    "tidal_count": 0,
    "incident_count": 0,
    "predicted_timeout": 0,
    "last_reset_time": time.time()
}

# 潮汐到达率统计
arrival_rate_history = deque(maxlen=100)  # 存储每分钟到达率
arrival_rate_window = deque(maxlen=10)    # 10分钟滑窗

def generate_task_by_scene(scene_mode):
    """根据场景模式生成任务"""
    task_types = {
        "offpeak": {
            "types": ["normal", "compute", "io"],
            "weights": [0.7, 0.2, 0.1],
            "cpu_range": (5, 20),
            "deadline_range": (100, 300),
            "priority": "low"
        },
        "tidal": {
            "types": ["sensor_fusion", "traffic_optimization"],
            "weights": [0.8, 0.2],
            "cpu_range": (15, 40),
            "deadline_range": (50, 150),
            "priority": "high"
        },
        "incident": {
            "types": ["collision_warning"],
            "weights": [1.0],
            "cpu_range": (20, 60),
            "deadline_range": (10, 50),
            "priority": "critical"
        }
    }
    
    config = task_types.get(scene_mode, task_types["offpeak"])
    
    # 选择任务类型
    task_type = random.choices(
        config["types"], 
        weights=config["weights"], 
        k=1
    )[0]
    
    # 生成任务参数
    cpu_need = random.uniform(*config["cpu_range"])
    deadline_ms = random.randint(*config["deadline_range"])
    data_size_kb = random.uniform(100, 500)
    
    # 创建任务
    new_task = {
        "task_id": f"task_{task_counter['current']}",
        "cpu_need": round(cpu_need, 2),
        "task_type": task_type,
        "deadline_ms": deadline_ms,
        "data_size_kb": round(data_size_kb, 2),
        "status": "waiting",
        "created_at": datetime.now().isoformat(),
        "priority": config["priority"],
        "scene_mode": scene_mode
    }
    
    return new_task

def update_task_stats(scene_mode, task):
    """更新任务统计"""
    global task_stats
    
    task_stats["total_generated"] += 1
    
    if scene_mode == "offpeak":
        task_stats["offpeak_count"] += 1
    elif scene_mode == "tidal":
        task_stats["tidal_count"] += 1
    elif scene_mode == "incident":
        task_stats["incident_count"] += 1
    
    # 预测超时（deadline < 50ms 或 cpu_need > 40）
    if task["deadline_ms"] < 50 or task["cpu_need"] > 40:
        task_stats["predicted_timeout"] += 1

def calculate_arrival_rate():
    """计算当前任务到达率（每分钟任务数）"""
    global arrival_rate_history
    
    # 模拟每分钟到达率的计算
    # 这里基于当前任务队列长度和生成速度估算
    current_rate = len(tasks) * 2 + random.uniform(-5, 15)
    current_rate = max(0, current_rate)
    
    arrival_rate_history.append(current_rate)
    
    # 计算滑窗平均到达率（最近10分钟）
    if len(arrival_rate_history) >= 10:
        recent_rates = list(arrival_rate_history)[-10:]
        avg_rate = sum(recent_rates) / len(recent_rates)
        arrival_rate_window.append(avg_rate)
    else:
        arrival_rate_window.append(current_rate)
    
    return current_rate, list(arrival_rate_window)

def predict_arrival_rate():
    """简单预测未来到达率（基于滑窗趋势）"""
    if len(arrival_rate_window) < 3:
        return None
    
    rates = list(arrival_rate_window)
    
    # 计算趋势（线性回归简化版）
    x = list(range(len(rates)))
    n = len(rates)
    
    if n == 0:
        return None
    
    # 简单趋势预测
    x_mean = sum(x) / n
    y_mean = sum(rates) / n
    
    numerator = sum((x[i] - x_mean) * (rates[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        slope = 0
    else:
        slope = numerator / denominator
    
    # 预测未来5分钟
    predictions = []
    for i in range(1, 6):
        pred = y_mean + slope * (n + i - x_mean)
        predictions.append(max(0, round(pred, 2)))
    
    return {
        "current_rate": round(rates[-1], 2),
        "trend": "rising" if slope > 0.5 else "falling" if slope < -0.5 else "stable",
        "slope": round(slope, 3),
        "predictions": predictions
    }

def _simulate_logic():
    """模拟器主逻辑"""
    init_db()
    rt_predictor = default_predictor()
    
    # 场景切换定时器
    last_scene_switch = time.time()
    current_scene = "offpeak"
    scene_duration = {
        "offpeak": 60,   # 60秒
        "tidal": 30,     # 30秒
        "incident": 15   # 15秒
    }
    
    # 任务生成周期
    last_task_gen = time.time()
    gen_interval = 2  # 每2秒生成一次任务
    
    while True:
        current_time = time.time()
        
        # 自动切换场景（用于演示）
        if current_time - last_scene_switch > scene_duration[current_scene]:
            # 场景轮换
            scenes = ["offpeak", "tidal", "incident"]
            current_index = scenes.index(current_scene)
            next_index = (current_index + 1) % len(scenes)
            current_scene = scenes[next_index]
            last_scene_switch = current_time
            print(f"[Simulator] 场景切换: {current_scene}")
        
        # 生成任务
        if current_time - last_task_gen >= gen_interval:
            # 根据场景决定生成任务数量
            if current_scene == "offpeak":
                num_tasks = random.randint(1, 3)
            elif current_scene == "tidal":
                num_tasks = random.randint(3, 8)
            else:  # incident
                num_tasks = random.randint(5, 15)
            
            # 生成任务
            for _ in range(num_tasks):
                new_task = generate_task_by_scene(current_scene)
                tasks.append(new_task)
                
                try:
                    record_task_arrival(task_public_id(new_task))
                except Exception:
                    pass
                
                task_counter["current"] += 1
                update_task_stats(current_scene, new_task)
            
            last_task_gen = current_time
            
            # 打印统计信息
            print(f"[Simulator] 场景:{current_scene}, 生成{num_tasks}个任务, "
                  f"总任务:{task_stats['total_generated']}, "
                  f"队列长度:{len(tasks)}")
        
        # 更新节点负载
        for node in nodes:
            if node["status"] == "online":
                # 根据场景调整负载变化
                if current_scene == "offpeak":
                    change = random.uniform(-3, 3)
                elif current_scene == "tidal":
                    change = random.uniform(2, 8)
                else:  # incident
                    change = random.uniform(5, 15)
                
                node["cpu"] = round(max(0, min(100, node["cpu"] + change)), 1)
                node["mem"] = round(max(0, min(100, node["mem"] + change * 0.8)), 1)
                
                # 在线预测记录
                try:
                    nid = node.get("id")
                    if nid is not None:
                        rt_predictor.update(node["cpu"], node_id=int(nid))
                except Exception:
                    pass
                
                # 模拟任务处理
                if "queue_len" in node:
                    node["queue_len"] = max(0, int(node["queue_len"]) - random.randint(0, 3))
            
            # 持久化节点快照
            try:
                save_node_load(
                    name=node["name"],
                    cpu=node["cpu"],
                    mem=node["mem"],
                    status=node["status"],
                )
            except Exception:
                pass
        
        # 计算到达率
        current_rate, rate_window = calculate_arrival_rate()
        
        # 获取预测负载
        predicted_load = []
        steps = []
        try:
            pred = get_predictions(steps=10)
            predicted_load = pred.get("predicted_load", []) or []
            steps = pred.get("steps", []) or []
        except Exception:
            pass
        
        # 推送给 WebSocket 客户端
        snapshot = {
            "timestamp": time.time(),
            "current_scene": current_scene,
            "nodes": [
                {
                    "id": n.get("id"),
                    "name": n.get("name"),
                    "cpu": n.get("cpu"),
                    "mem": n.get("mem"),
                    "status": n.get("status"),
                    "queue_len": n.get("queue_len", 0)
                }
                for n in nodes
            ],
            "predicted": {"steps": steps, "predicted_load": predicted_load},
            "task_stats": task_stats,
            "arrival_rate": {
                "current": current_rate,
                "window_avg": rate_window[-1] if rate_window else 0,
                "history": list(rate_window)
            }
        }
        ws_manager.broadcast_threadsafe(snapshot)
        
        time.sleep(1)

def start_simulator():
    """启动模拟器"""
    daemon_thread = threading.Thread(target=_simulate_logic, daemon=True)
    daemon_thread.start()
    print(">>> 负载模拟器已启动（支持平峰/潮汐/事故场景）...")

def get_task_stats():
    """获取任务统计信息"""
    global task_stats
    return {
        **task_stats,
        "queue_length": len(tasks),
        "uptime_seconds": time.time() - task_stats["last_reset_time"]
    }

def reset_task_stats():
    """重置任务统计"""
    global task_stats
    task_stats = {
        "total_generated": 0,
        "offpeak_count": 0,
        "tidal_count": 0,
        "incident_count": 0,
        "predicted_timeout": 0,
        "last_reset_time": time.time()
    }