# algorithms/scheduler.py
import random
from backend.models import nodes, tasks  # 跨文件夹去 backend 拿数据
from algorithms.predictive_policy import pick_node_by_prediction
from algorithms.realtime_predictor import default_predictor

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
    elif strategy == "predictive":
        rt = default_predictor()
        target_node = pick_node_by_prediction(
            nodes,
            get_predictions=lambda steps: rt.predict(steps=steps),
            steps=5,
            trend_threshold=0.5,
        )
    elif strategy == "shortest_queue":
        # 最短队列优先：基于每个节点的 queue_len（由 scheduler 增加、simulator 衰减）
        target_node = min(nodes, key=lambda x: x.get("queue_len", 0))
    elif strategy == "predict_least_load":
        # 预测 + 当前负载融合打分：实时单例引擎 predict() 返回 {"steps": [...], "predicted_load": [...]}
        predicted_avg = 0.0
        try:
            _realtime_predictor = default_predictor()
            pred = _realtime_predictor.predict(steps=10)
            vals = pred.get("predicted_load", []) or []
            if vals:
                predicted_avg = sum(vals) / len(vals)
        except Exception:
            predicted_avg = 0.0

        # 与王瑾分支对齐：预测均值直接 clip 到 0~100 作为压力分
        predicted_pressure = max(0.0, min(100.0, float(predicted_avg)))
        beta = 0.3  # 预测项权重：越大越偏向“预防未来拥塞”
        target_node = min(nodes, key=lambda x: float(x["cpu"]) + beta * predicted_pressure)
    elif strategy == "round_robin":
        target_node = nodes[rr_index % len(nodes)]
        rr_index += 1
    else:
        tasks.insert(0, current_task)
        return {"error": "未知的调度策略"}

    old_cpu = target_node["cpu"]
    target_node["cpu"] = round(min(100, old_cpu + current_task["cpu_need"]), 1)
    target_node["queue_len"] = int(target_node.get("queue_len", 0)) + 1
    current_task["status"] = "assigned"
    current_task["assigned_to"] = target_node["name"]

    return {
        "message": "调度成功",
        "strategy": strategy,
        "task_details": current_task,
        "node_id": target_node.get("id"),
        "node_name": target_node.get("name"),
        "node_cpu_before": old_cpu,
        "node_cpu_after": target_node["cpu"],
    }