# algorithms/scheduler.py
import random
from backend.models import nodes, tasks  # 跨文件夹去 backend 拿数据
from algorithms.predictor import get_predictions

rr_index = 0

def execute_schedule(strategy: str):
    global rr_index
    if len(tasks) == 0:
        return {"error": "当前没有待处理的任务"}
        
    current_task = tasks.pop(0)
    
    if strategy == "random":
        target_node = random.choice(nodes)
    elif strategy == "least_load":
        target_node = min(nodes, key=lambda x: x["cpu"])
    elif strategy == "shortest_queue":
        # 最短队列优先：基于每个节点的 queue_len（由 scheduler 增加、simulator 衰减）
        target_node = min(nodes, key=lambda x: x.get("queue_len", 0))
    elif strategy == "predict_least_load":
        # 预测 + 当前负载融合打分：在节点当前 cpu 上叠加未来负载压力因子
        predicted_avg = 0.0
        try:
            pred = get_predictions(steps=10)
            vals = pred.get("predicted_load", []) or []
            if vals:
                predicted_avg = sum(vals) / len(vals)
        except Exception:
            predicted_avg = 0.0

        # 将预测负载映射到 0~100 的“压力分”，与 cpu 同尺度
        predicted_pressure = max(0.0, min(100.0, predicted_avg * 10.0))
        beta = 0.3  # 预测项权重：越大越偏向“预防未来拥塞”
        target_node = min(nodes, key=lambda x: float(x["cpu"]) + beta * predicted_pressure)
    elif strategy == "round_robin":
        target_node = nodes[rr_index % len(nodes)]
        rr_index += 1
    else:
        tasks.insert(0, current_task)
        return {"error": "未知的调度策略"}

    target_node["cpu"] = round(min(100, target_node["cpu"] + current_task["cpu_need"]), 1)
    target_node["queue_len"] = int(target_node.get("queue_len", 0)) + 1
    current_task["status"] = "assigned"
    current_task["assigned_to"] = target_node["name"]
    
    return {
        "message": "调度成功",
        "strategy": strategy,
        "task_details": current_task,
        "node_cpu_after": target_node["cpu"]
    }