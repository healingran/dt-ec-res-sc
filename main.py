import asyncio
import copy
from contextlib import asynccontextmanager
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
    yield
    task.cancel()
    try:
        await task
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
