# main.py
from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from algorithms.predictor import get_predictions
from algorithms.scheduler import execute_schedule
from backend.models import nodes, task_counter, tasks
from backend.simulator import start_simulator
from backend.ws_manager import manager as ws_manager

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


@app.get("/predict")
def predict_load(steps: int = 10):
    """兼容旧路径：保留 /predict，不影响现有前端联调。"""
    return get_predictions(steps=steps)


@api_v1.websocket("/ws/nodes")
async def ws_nodes(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # 保持连接：客户端消息可忽略（服务端主要负责广播）
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


app.include_router(api_v1)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)