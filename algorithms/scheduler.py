# algorithms/scheduler.py
import random
from backend.models import nodes, tasks  # 跨文件夹去 backend 拿数据
from backend.tasks_history import record_task_assigned, task_public_id
from algorithms.predictive_policy import pick_node_by_prediction
from algorithms.realtime_predictor import default_predictor

rr_index = 0


def _predicted_pressure() -> float:
    """用在线预测序列估算“未来拥堵压力”（0~100）。"""
    try:
        rt = default_predictor()
        pred = rt.predict(steps=10)
        vals = pred.get("predicted_load", []) or []
        if not vals:
            return 0.0
        avg = sum(float(v) for v in vals) / len(vals)
        return max(0.0, min(100.0, float(avg)))
    except Exception:
        return 0.0


def _service_time_ms(task_type: str) -> float:
    t = str(task_type or "").lower()
    if t == "collision_warning":
        return 8.0
    if t == "sensor_fusion":
        return 45.0
    if t == "traffic_optimization":
        return 120.0
    return 60.0


def _compute_time_ms(cpu_need: float, *, task_type: str, node_cpu: float) -> float:
    # 简化估算：不同任务类型的“每单位算力需求”的耗时不同；节点越忙越慢
    t = str(task_type or "").lower()
    if t == "collision_warning":
        per_unit = 2.0
    elif t == "sensor_fusion":
        per_unit = 8.0
    elif t == "traffic_optimization":
        per_unit = 14.0
    else:
        per_unit = 10.0

    load_factor = 1.0 + max(0.0, min(100.0, float(node_cpu))) / 100.0
    return float(cpu_need) * per_unit * load_factor


def _network_time_ms(data_size_kb: float, *, node_bw_kbps: float) -> float:
    bw = float(node_bw_kbps) if float(node_bw_kbps) > 0 else 50_000.0
    return (float(data_size_kb) / bw) * 1000.0


def _estimate_total_latency_ms(task: dict, node: dict) -> float:
    task_type = str(task.get("task_type") or "sensor_fusion")
    deadline_ms = task.get("deadline_ms")
    _ = deadline_ms  # keep field for readability

    cpu_need = float(task.get("cpu_need") or 0.0)
    data_size_kb = float(task.get("data_size_kb") or 0.0)

    t_net = _network_time_ms(data_size_kb, node_bw_kbps=float(node.get("bw_kbps") or 50_000.0))
    t_queue = float(node.get("queue_len") or 0) * _service_time_ms(task_type)
    t_cpu = _compute_time_ms(cpu_need, task_type=task_type, node_cpu=float(node.get("cpu") or 0.0))
    return t_net + t_queue + t_cpu


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
        # 预测 + 当前负载融合打分：预测均值 clip 到 0~100 作为压力分
        predicted_pressure = _predicted_pressure()
        beta = 0.3  # 预测项权重：越大越偏向“预防未来拥塞”
        target_node = min(nodes, key=lambda x: float(x["cpu"]) + beta * predicted_pressure)
    elif strategy == "sla_predict":
        # SLA-aware + 预测融合：
        # 1) 估算总时延=传输+排队+计算
        # 2) deadline 约束：超时重罚
        # 3) 预测压力：避免未来拥堵
        predicted_pressure = _predicted_pressure()
        alpha = 0.15  # 当前 cpu 的惩罚权重
        beta = 0.25  # 预测压力权重
        penalty_deadline_miss = 10_000.0

        best = None
        best_meta = None
        for n in nodes:
            est_ms = _estimate_total_latency_ms(current_task, n)
            deadline_ms = current_task.get("deadline_ms")
            meet = True
            drop_reason = ""
            if deadline_ms is not None:
                try:
                    meet = est_ms <= float(deadline_ms)
                except Exception:
                    meet = True

            score = est_ms + alpha * float(n.get("cpu") or 0.0) + beta * float(predicted_pressure)
            if not meet:
                score += penalty_deadline_miss
                drop_reason = "deadline_miss"

            if best is None or score < best_meta["score"]:
                best = n
                best_meta = {
                    "estimated_total_latency_ms": round(float(est_ms), 2),
                    "meet_deadline": bool(meet),
                    "score": round(float(score), 2),
                    "drop_reason": drop_reason,
                    "predicted_pressure": round(float(predicted_pressure), 2),
                }

        target_node = best
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

    resp = {
        "message": "调度成功",
        "strategy": strategy,
        "task_details": current_task,
        "node_id": target_node.get("id"),
        "node_name": target_node.get("name"),
        "node_cpu_before": old_cpu,
        "node_cpu_after": target_node["cpu"],
    }
    if strategy == "sla_predict":
        # best_meta 一定存在于 sla_predict 分支
        resp.update(
            {
                "estimated_total_latency_ms": best_meta["estimated_total_latency_ms"],
                "meet_deadline": best_meta["meet_deadline"],
                "score": best_meta["score"],
                "drop_reason": best_meta["drop_reason"],
                "predicted_pressure": best_meta["predicted_pressure"],
            }
        )
    try:
        record_task_assigned(
            task_public_id(current_task), str(target_node.get("name") or "")
        )
    except Exception:
        pass
    return resp