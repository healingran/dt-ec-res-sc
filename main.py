# main.py
import asyncio

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from algorithms.predictor import get_predictions
from algorithms.scheduler import execute_schedule
from backend.models import nodes, task_counter, tasks
from backend.simulator import start_simulator
from backend.ws_manager import manager as ws_manager
from backend import database as db

import uvicorn

app = FastAPI()

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


@api_v1.get("/nodes")
def get_all_nodes_v1():
    return {"nodes": nodes}


@api_v1.get("/tasks")
def get_all_tasks_v1():
    return {"pending_tasks": len(tasks), "tasks": tasks}


@api_v1.post("/task")
def create_new_task_v1(cpu_need: float):
    new_task = {
        "id": task_counter["current"],
        "cpu_need": cpu_need,
        "status": "waiting",
    }
    tasks.append(new_task)
    task_counter["current"] += 1
    return {"message": "任务创建成功", "task": new_task}


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


@app.get("/predict")
def predict_load(steps: int = 10):
    """兼容旧路径：保留 /predict，不影响现有前端联调。"""
    return get_predictions(steps=steps)


async def _ws_nodes_session(websocket: WebSocket) -> None:
    """保持长连接并接收任意客户端帧；仅用 receive_text 会在对方发二进制帧时 KeyError 并被误断开。"""
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


app.include_router(api_v1)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        # 协议级 ping/pong，减轻中间设备因「长时间无帧」断开空闲连接
        ws_ping_interval=20.0,
        ws_ping_timeout=20.0,
    )