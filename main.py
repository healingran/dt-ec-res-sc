import asyncio
import copy
import random
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from algorithms.predictor import get_predictions
from algorithms.scheduler import execute_schedule
from backend import dashboard_state
from backend import database as db
from backend.models import nodes, task_counter, tasks
from backend.simulator import start_simulator
from backend.ws_manager import manager as ws_manager

import uvicorn


_dashboard_ws_clients: List[WebSocket] = []


def _build_dashboard_payload() -> dict:
    """dashboard 推送：节点快照 + 节点1真实历史 + LSTM 预测序列。"""
    n1 = next((n for n in nodes if n.get("id") == 1), None)
    if n1 is not None and "cpu" in n1:
        dashboard_state.append_node1_cpu(n1["cpu"])

    real = list(dashboard_state.CPU_HISTORY)
    predicted_load: list = []
    pred_steps: list = []
    try:
        pred = get_predictions(steps=15)
        predicted_load = pred.get("predicted_load") or []
        pred_steps = pred.get("steps") or []
    except Exception:
        predicted_load = []
        pred_steps = []

    return {
        "nodes": copy.deepcopy(nodes),
        "chart": {
            "real": real,
            "predicted": predicted_load,
            "pred_steps": pred_steps,
        },
    }


async def _dashboard_broadcast_loop() -> None:
    while True:
        await asyncio.sleep(2)
        if not _dashboard_ws_clients:
            continue
        payload = _build_dashboard_payload()
        dead: List[WebSocket] = []
        for ws in list(_dashboard_ws_clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in _dashboard_ws_clients:
                _dashboard_ws_clients.remove(ws)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    task = asyncio.create_task(_dashboard_broadcast_loop())
    monitor_task = asyncio.create_task(_monitor_broadcast_loop())
    yield
    task.cancel()
    monitor_task.cancel()
    try:
        await task
        await monitor_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=_lifespan)

# 允许本地前端页面（8080 等端口）跨域访问 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:63342",
        "http://localhost:63342",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动模拟器（含：SQLite 持久化 + WebSocket 广播）
start_simulator()

api_v1 = APIRouter(prefix="/api/v1")


@app.on_event("startup")
async def _ws_manager_bind_loop() -> None:
    """让 simulator 线程里的 broadcast 能尽早挂到当前事件循环（不依赖首个客户端）。"""
    ws_manager.set_loop(asyncio.get_running_loop())


class ExperimentCreate(BaseModel):
    experiment_name: str


class TaskCreate(BaseModel):
    cpu_need: float = Field(..., ge=0)
    task_type: str = Field("sensor_fusion")
    deadline_ms: int = Field(100, ge=1)
    data_size_kb: float = Field(256.0, ge=0)


class SceneSwitchRequest(BaseModel):
    mode: str


class TaskGenerateRequest(BaseModel):
    count: int = 10


class TaskBatchRequest(BaseModel):
    count: int = 50


class IncidentTriggerRequest(BaseModel):
    count: int = 100


class SchedulerStrategyRequest(BaseModel):
    strategy: str


class ExperimentStopRequest(BaseModel):
    experiment_id: str


# 全局状态
current_scene_mode = "offpeak"
current_scheduler_strategy = "least_load"
current_experiment = None
scene_config = {
    "offpeak": {"base_load": 10, "burst_intensity": 0.5},
    "peak": {"base_load": 50, "burst_intensity": 0.8},
    "incident": {"base_load": 80, "burst_intensity": 1.0}
}
_monitor_ws_clients: List[WebSocket] = []


async def _monitor_broadcast_loop() -> None:
    """实时大屏广播循环：每2秒推送节点和任务更新"""
    while True:
        await asyncio.sleep(2)
        if not _monitor_ws_clients:
            continue
        
        payload_nodes = {
            "type": "nodes_update",
            "nodes": copy.deepcopy(nodes)
        }
        
        payload_tasks = {
            "type": "tasks_update",
            "tasks": copy.deepcopy(tasks)
        }
        
        dead: List[WebSocket] = []
        for ws in list(_monitor_ws_clients):
            try:
                await ws.send_json(payload_nodes)
                await ws.send_json(payload_tasks)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in _monitor_ws_clients:
                _monitor_ws_clients.remove(ws)


@api_v1.get("/health")
def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@api_v1.get("/scene/current")
def get_current_scene():
    """获取当前场景模式"""
    config = scene_config.get(current_scene_mode, scene_config["offpeak"])
    return {
        "mode": current_scene_mode,
        "base_load": config["base_load"],
        "burst_intensity": config["burst_intensity"]
    }


@api_v1.post("/scene/switch")
def switch_scene(request: SceneSwitchRequest):
    """切换场景模式"""
    global current_scene_mode
    if request.mode not in scene_config:
        return {"error": f"Invalid scene mode: {request.mode}"}
    
    current_scene_mode = request.mode
    config = scene_config[current_scene_mode]
    
    # 更新节点负载以反映场景变化
    for node in nodes:
        base_load = config["base_load"]
        variation = random.uniform(-10, 10)
        node["cpu"] = max(0, min(100, base_load + variation))
        node["mem"] = max(0, min(100, base_load * 0.8 + variation))
    
    return {
        "mode": current_scene_mode,
        "base_load": config["base_load"],
        "burst_intensity": config["burst_intensity"],
        "message": f"Scene switched to {current_scene_mode}"
    }


@api_v1.post("/tasks/generate")
def generate_tasks(request: TaskGenerateRequest):
    """生成指定数量的任务"""
    task_types = ["normal", "compute", "io", "collision_warning"]
    generated = 0
    
    for _ in range(request.count):
        task_type = random.choices(
            task_types, 
            weights=[0.6, 0.2, 0.15, 0.05] if current_scene_mode != "incident" else [0.3, 0.2, 0.2, 0.3],
            k=1
        )[0]
        
        cpu_need = random.uniform(5, 30)
        if task_type == "collision_warning":
            cpu_need = random.uniform(10, 50)
        
        new_task = {
            "task_id": f"task_{task_counter['current']}",
            "cpu_need": cpu_need,
            "task_type": task_type,
            "status": "waiting",
            "created_at": datetime.now().isoformat(),
            "deadline": None,
            "estimated_delay": None
        }
        
        if task_type == "collision_warning":
            deadline_seconds = random.randint(5, 30)
            new_task["deadline"] = (datetime.now().timestamp() + deadline_seconds) * 1000
            new_task["estimated_delay"] = random.randint(3, 25)
        
        tasks.append(new_task)
        task_counter["current"] += 1
        generated += 1
    
    return {"generated": generated, "message": f"Generated {generated} tasks"}


@api_v1.post("/tasks/batch")
def generate_batch_tasks(request: TaskBatchRequest):
    """批量生成任务"""
    return generate_tasks(TaskGenerateRequest(count=request.count))


@api_v1.post("/incident/trigger")
def trigger_incident(request: IncidentTriggerRequest):
    """触发事故：注入大量collision_warning任务"""
    generated = 0
    
    for _ in range(request.count):
        cpu_need = random.uniform(15, 45)
        deadline_seconds = random.randint(3, 15)
        
        new_task = {
            "task_id": f"incident_{task_counter['current']}",
            "cpu_need": cpu_need,
            "task_type": "collision_warning",
            "status": "waiting",
            "created_at": datetime.now().isoformat(),
            "deadline": (datetime.now().timestamp() + deadline_seconds) * 1000,
            "estimated_delay": random.randint(2, 12)
        }
        
        tasks.append(new_task)
        task_counter["current"] += 1
        generated += 1
    
    # 增加节点负载
    for node in nodes:
        node["cpu"] = min(100, node["cpu"] + random.uniform(10, 30))
        node["mem"] = min(100, node["mem"] + random.uniform(5, 20))
    
    return {"injected": generated, "message": f"Incident triggered: {generated} collision_warning tasks"}


@api_v1.post("/experiments/start")
def start_experiment_api():
    """开始实验"""
    global current_experiment
    experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    current_experiment = {
        "experiment_id": experiment_id,
        "status": "running",
        "start_time": datetime.now().isoformat(),
        "scene_mode": current_scene_mode,
        "scheduler_strategy": current_scheduler_strategy
    }
    
    # 清空现有任务
    tasks.clear()
    
    return {
        "experiment_id": experiment_id,
        "status": "running",
        "start_time": current_experiment["start_time"],
        "message": "Experiment started"
    }


@api_v1.post("/experiments/stop")
def stop_experiment_api(request: ExperimentStopRequest = None):
    """停止实验"""
    global current_experiment
    
    if current_experiment is None:
        return {"error": "No running experiment"}
    
    current_experiment["status"] = "stopped"
    current_experiment["end_time"] = datetime.now().isoformat()
    
    return {
        "experiment_id": current_experiment["experiment_id"],
        "status": "stopped",
        "end_time": current_experiment["end_time"],
        "message": "Experiment stopped"
    }


@api_v1.post("/experiments/reset")
def reset_experiment():
    """重置实验"""
    global current_experiment
    
    current_experiment = None
    tasks.clear()
    
    for node in nodes:
        node["cpu"] = random.uniform(10, 30)
        node["mem"] = random.uniform(20, 40)
        node["queue_len"] = 0
    
    return {"message": "Experiment reset"}


@api_v1.get("/experiments/current")
def get_current_experiment():
    """获取当前实验信息"""
    if current_experiment is None:
        return {"experiment_id": None, "status": None}
    
    return current_experiment


@api_v1.get("/scheduler/current")
def get_current_scheduler():
    """获取当前调度策略"""
    return {"strategy": current_scheduler_strategy}


@api_v1.post("/scheduler/strategy")
def set_scheduler_strategy(request: SchedulerStrategyRequest):
    """设置调度策略"""
    global current_scheduler_strategy
    
    valid_strategies = ["least_load", "round_robin", "shortest_queue", "sla_predict"]
    if request.strategy not in valid_strategies:
        return {"error": f"Invalid strategy: {request.strategy}"}
    
    current_scheduler_strategy = request.strategy
    
    return {
        "strategy": current_scheduler_strategy,
        "message": f"Scheduler strategy set to {current_scheduler_strategy}"
    }


@api_v1.websocket("/ws")
async def ws_monitor(websocket: WebSocket):
    """实时大屏WebSocket接口"""
    await websocket.accept()
    _monitor_ws_clients.append(websocket)
    
    try:
        # 立即发送当前状态
        await websocket.send_json({
            "type": "nodes_update",
            "nodes": copy.deepcopy(nodes)
        })
        
        await websocket.send_json({
            "type": "tasks_update",
            "tasks": copy.deepcopy(tasks)
        })
        
        # 保持连接，使用try-except捕获断开连接的情况
        while True:
            try:
                msg = await websocket.receive()
                if msg["type"] == "websocket.disconnect":
                    break
            except WebSocketDisconnect:
                break
            except Exception:
                break
            
    except Exception:
        pass
    finally:
        if websocket in _monitor_ws_clients:
            _monitor_ws_clients.remove(websocket)


@app.websocket("/ws")
async def ws_monitor_root(websocket: WebSocket):
    """根路径WebSocket接口（兼容）"""
    await websocket.accept()
    _monitor_ws_clients.append(websocket)
    
    try:
        # 立即发送当前状态
        await websocket.send_json({
            "type": "nodes_update",
            "nodes": copy.deepcopy(nodes)
        })
        
        await websocket.send_json({
            "type": "tasks_update",
            "tasks": copy.deepcopy(tasks)
        })
        
        # 保持连接，使用try-except捕获断开连接的情况
        while True:
            try:
                msg = await websocket.receive()
                if msg["type"] == "websocket.disconnect":
                    break
            except WebSocketDisconnect:
                break
            except Exception:
                break
            
    except Exception:
        pass
    finally:
        if websocket in _monitor_ws_clients:
            _monitor_ws_clients.remove(websocket)


@api_v1.get("/nodes")
def get_all_nodes_v1():
    return {"nodes": nodes}


@api_v1.get("/tasks")
def get_all_tasks_v1():
    return {"pending_tasks": len(tasks), "tasks": tasks}


@api_v1.post("/task")
def create_new_task_v1(
    cpu_need: float,
    task_type: str = "sensor_fusion",
    deadline_ms: int = 100,
    data_size_kb: float = 256.0,
):
    new_task = {
        "id": task_counter["current"],
        "cpu_need": cpu_need,
        "task_type": task_type,
        "deadline_ms": int(deadline_ms),
        "data_size_kb": float(data_size_kb),
        "status": "waiting",
    }
    tasks.append(new_task)
    task_counter["current"] += 1
    return {"message": "任务创建成功", "task": new_task}


@api_v1.post("/tasks")
def create_new_task_json_v1(payload: TaskCreate):
    # 与旧接口共用入队逻辑，确保行为一致
    return create_new_task_v1(
        cpu_need=float(payload.cpu_need),
        task_type=str(payload.task_type),
        deadline_ms=int(payload.deadline_ms),
        data_size_kb=float(payload.data_size_kb),
    )


@api_v1.post("/schedule")
def trigger_schedule_v1(strategy: str = "least_load"):
    return execute_schedule(strategy)


@api_v1.get("/predict")
def predict_load_v1(steps: int = 10):
    """LSTM 负载预测，steps 为预测步数，默认 10"""
    return get_predictions(steps=steps)


@api_v1.post("/experiments")
def create_experiment_v1(payload: ExperimentCreate):
    return db.create_experiment(payload.experiment_name)


@api_v1.post("/experiments/{experiment_id}/start")
def start_experiment_v1(experiment_id: int):
    return db.start_experiment(experiment_id)


@api_v1.post("/experiments/{experiment_id}/stop")
def stop_experiment_v1(experiment_id: int):
    return db.stop_experiment(experiment_id)


@api_v1.get("/experiments")
def list_experiments_v1():
    return {"experiments": db.list_experiments()}


@api_v1.get("/experiments/{experiment_id}")
def get_experiment_v1(experiment_id: int):
    try:
        return db.get_experiment(experiment_id)
    except KeyError as e:
        return {"error": str(e)}


@api_v1.get("/experiments/{experiment_id}/history/nodes")
def get_experiment_nodes_history_v1(experiment_id: int, limit: int = 500, offset: int = 0):
    try:
        return db.get_nodes_history(experiment_id, limit=limit, offset=offset)
    except Exception as e:
        return {"error": str(e)}


# ---- 兼容旧路径：供静态前端直接访问（不带 /api/v1 前缀） ----


@app.get("/nodes")
def get_all_nodes():
    return get_all_nodes_v1()


@app.get("/tasks")
def get_all_tasks():
    return get_all_tasks_v1()


@app.post("/task")
def create_new_task(cpu_need: float):
    return create_new_task_v1(cpu_need)


@app.post("/schedule")
def trigger_schedule(strategy: str = "least_load"):
    return trigger_schedule_v1(strategy)


@app.get("/predict")
def predict_load(steps: int = 10):
    """兼容旧路径：保留 /predict，不影响现有前端联调。"""
    return get_predictions(steps=steps)


async def _ws_nodes_session(websocket: WebSocket) -> None:
    """保持长连接并接收任意客户端帧。"""
    await ws_manager.connect(websocket)
    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket)


@api_v1.websocket("/ws/nodes")
async def ws_nodes(websocket: WebSocket):
    await _ws_nodes_session(websocket)


@app.websocket("/ws/nodes")
async def ws_nodes_root_alias(websocket: WebSocket):
    """兼容联调常用路径 ws://host:8000/ws/nodes（带前缀的完整路径为 /api/v1/ws/nodes）。"""
    await _ws_nodes_session(websocket)


@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    """dashboard 专用：统一每 2s 广播一次（含真实历史 + 预测序列）。"""
    await websocket.accept()
    _dashboard_ws_clients.append(websocket)
    try:
        try:
            await websocket.send_json(_build_dashboard_payload())
        except Exception:
            pass
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _dashboard_ws_clients:
            _dashboard_ws_clients.remove(websocket)


app.include_router(api_v1)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        ws_ping_interval=20.0,
        ws_ping_timeout=20.0,
    )
