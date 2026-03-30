# main.py
import asyncio
import copy
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.models import nodes, tasks, task_counter
from backend.simulator import start_simulator
from backend import dashboard_state
from algorithms.scheduler import execute_schedule
from algorithms.predictor import get_predictions
import uvicorn

# 启动模拟器（线程）
start_simulator()

# WebSocket 订阅者（单广播循环推送，避免多连接重复采样 CPU 历史）
_dashboard_ws_clients: List[WebSocket] = []


def _build_ws_payload() -> dict:
    """组装 WebSocket 推送：节点快照 + 节点1真实历史 + LSTM 预测序列。"""
    n1 = next((n for n in nodes if n.get("id") == 1), None)
    if n1 is not None:
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
        payload = _build_ws_payload()
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
        # JetBrains IDE 内置 Web 预览（WebStorm / PhpStorm 等，端口多为 63342）
        "http://127.0.0.1:63342",
        "http://localhost:63342",
        # Vite 等常见前端端口
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/nodes")
def get_all_nodes():
    return {"nodes": nodes}


@app.get("/tasks")
def get_all_tasks():
    return {"pending_tasks": len(tasks), "tasks": tasks}


@app.post("/task")
def create_new_task(cpu_need: float):
    new_task = {
        "id": task_counter["current"],
        "cpu_need": cpu_need,
        "status": "waiting"
    }
    tasks.append(new_task)
    task_counter["current"] += 1
    return {"message": "任务创建成功", "task": new_task}


@app.post("/schedule")
def trigger_schedule(strategy: str = "least_load"):
    return execute_schedule(strategy)


@app.get("/predict")
def predict_load(steps: int = 10):
    """LSTM 负载预测，steps 为预测步数，默认 10"""
    return get_predictions(steps=steps)


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """订阅后由后台统一每 2s 广播；连接建立时立即推送一帧。"""
    await websocket.accept()
    _dashboard_ws_clients.append(websocket)
    try:
        try:
            await websocket.send_json(_build_ws_payload())
        except Exception:
            pass
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _dashboard_ws_clients:
            _dashboard_ws_clients.remove(websocket)

# 在 main.py 中添加这个路由（放在其他路由旁边）

@app.post("/reset")
def reset_system():
    """重置系统状态"""
    from backend.models import nodes, tasks, task_counter
    from algorithms.predictor import clear_node_history
    
    # 重置节点
    nodes.clear()
    nodes.append({"id": 1, "name": "Edge-Node-01", "cpu": 10.0, "mem": 20.0, "status": "online"})
    nodes.append({"id": 2, "name": "Edge-Node-02", "cpu": 40.0, "mem": 50.0, "status": "online"})
    nodes.append({"id": 3, "name": "Edge-Node-03", "cpu": 85.0, "mem": 70.0, "status": "online"})
    
    # 重置任务
    tasks.clear()
    task_counter["current"] = 1
    
    # 清空预测历史
    clear_node_history()
    
    return {"message": "系统已重置"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
