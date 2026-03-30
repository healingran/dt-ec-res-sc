# algorithms/scheduler.py
from backend.models import nodes, tasks
from algorithms.predictor import get_predictions, clear_node_history

def pick_node_by_prediction(nodes_list):
    """基于 LSTM 预测结果的调度逻辑"""
    try:
        # 获取未来 5 步的预测结果
        prediction_data = get_predictions(steps=5)
        predicted_loads = prediction_data["predicted_load"]
        
        if not predicted_loads or len(predicted_loads) < 2:
            return min(nodes_list, key=lambda x: x['cpu'])
        
        # 计算趋势
        trend = predicted_loads[-1] - predicted_loads[0]
        
        # 获取各节点当前负载
        node_loads = [(n['id'], n['cpu']) for n in nodes_list]
        
        # 根据趋势选择节点
        if trend > 0.5:  # 预测负载上升
            # 选择最空闲的节点
            target = min(nodes_list, key=lambda x: x['cpu'])
        else:  # 预测负载下降或平稳
            # 选择负载最低的节点
            target = min(nodes_list, key=lambda x: x['cpu'])
        
        return target
            
    except Exception as e:
        print(f"⚠️ 预测调度异常: {e}")
        return min(nodes_list, key=lambda x: x['cpu'])

def execute_schedule(strategy="least_load"):
    """执行调度"""
    if not tasks:
        return {"message": "当前没有待处理的任务"}
    
    # 取出任务
    task = tasks.pop(0)
    cpu_need = task['cpu_need']
    
    if strategy == "predictive":
        target_node = pick_node_by_prediction(nodes)
        strategy_name = "LSTM 预测辅助调度"
    else:
        # 默认策略：最小负载优先
        target_node = min(nodes, key=lambda x: x['cpu'])
        strategy_name = "最小负载优先"
    
    # 执行调度
    old_cpu = target_node['cpu']
    new_cpu = old_cpu + cpu_need
    target_node['cpu'] = round(min(100, new_cpu), 2)
    
    return {
        "message": "调度成功",
        "strategy": strategy_name,
        "task_details": task,
        "node_id": target_node['id'],
        "node_cpu_before": old_cpu,
        "node_cpu_after": target_node['cpu']
    }