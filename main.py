# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.models import nodes, tasks, task_counter
from backend.simulator import start_simulator
from algorithms.scheduler import execute_schedule
from algorithms.predictor import get_predictions
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
        # JetBrains IDE 内置 Web 预览（WebStorm / PhpStorm 等，端口多为 63342）
        "http://127.0.0.1:63342",
        "http://localhost:63342",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动模拟器
start_simulator()

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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)