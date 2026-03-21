<<<<<<< HEAD
# algorithms/scheduler.py
import random
from backend.models import nodes, tasks  # 跨文件夹去 backend 拿数据

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
    elif strategy == "round_robin":
        target_node = nodes[rr_index % len(nodes)]
        rr_index += 1
    else:
        tasks.insert(0, current_task)
        return {"error": "未知的调度策略"}

    target_node["cpu"] = round(min(100, target_node["cpu"] + current_task["cpu_need"]), 1)
    current_task["status"] = "assigned"
    current_task["assigned_to"] = target_node["name"]
    
    return {
        "message": "调度成功",
        "strategy": strategy,
        "task_details": current_task,
        "node_cpu_after": target_node["cpu"]
=======
# algorithms/scheduler.py
import random
from backend.models import nodes, tasks  # 跨文件夹去 backend 拿数据

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
    elif strategy == "round_robin":
        target_node = nodes[rr_index % len(nodes)]
        rr_index += 1
    else:
        tasks.insert(0, current_task)
        return {"error": "未知的调度策略"}

    target_node["cpu"] = round(min(100, target_node["cpu"] + current_task["cpu_need"]), 1)
    current_task["status"] = "assigned"
    current_task["assigned_to"] = target_node["name"]
    
    return {
        "message": "调度成功",
        "strategy": strategy,
        "task_details": current_task,
        "node_cpu_after": target_node["cpu"]
>>>>>>> 401a1f2ae0766c497231bc734755250693c7e6b2
    }