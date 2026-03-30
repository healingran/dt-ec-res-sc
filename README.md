# 🏙️ SmartCity-EdgeTwin: 智慧城市边缘计算资源数字孪生管理平台

## 👥 团队成员与分工
* **负责人 (Lead)**: 李欣然 — 负责项目整体架构设计、仓库维护与环境配置。
* **后端组**: 王瑾、吕子欣、李欣然 — 负责边缘计算任务分配算法研发。
* **开发组**: 金梦婷、张许诺 — 负责后端接口设计与前端可视化对接。

---

## 📂 项目架构说明
为了保证团队开发不混乱，请务必按照以下目录结构存放文件：

```text
SmartCity_Platform/
├── algorithms/      # 核心算法 (负责人: 李欣然、吕子欣、王瑾)
├── backend/         # FastAPI 业务逻辑与 API 接口 (负责人: 李欣然、吕子欣、王瑾)
├── frontend/        # 数字孪生大屏可视化界面 (负责人: 金梦婷、张许诺)
├── scripts/         # 自动化脚本（实验跑批、对比等）
├── main.py          # 项目启动总入口
└── .vscode/         # 团队统一开发配置 (已同步绝对路径规范)
```

---

## 🚀 快速启动

### 1) 安装依赖

```bash
cd E:\SmartCity_Platform
python -m pip install -r requirements.txt
```

### 2) 启动后端（FastAPI）

```bash
cd E:\SmartCity_Platform
python main.py
```

打开接口文档：`http://127.0.0.1:8000/docs`

---

## 🧪 实验 API（/api/v1/experiments）验收步骤

在 Swagger 里按顺序执行：

1. `POST /api/v1/experiments`（创建实验）
2. `POST /api/v1/experiments/{id}/start`（开始实验）
3. 等待 5~10 秒（模拟器持续写入节点快照）
4. `POST /api/v1/experiments/{id}/stop`（停止实验）
5. `GET /api/v1/experiments/{id}/history/nodes`（按时间窗查询实验期间节点快照）

说明：
- `nodes` 表为**历史快照表**（追加写入），可用于历史回放/对比。
- 预测接口保留兼容路径：`GET /predict?steps=10`。

---

## 🧠 调度策略（/api/v1/schedule）

`POST /api/v1/schedule?strategy=<name>`

支持策略：
- `random`
- `round_robin`
- `least_load`
- `shortest_queue`（基于节点 `queue_len`）
- `predict_least_load`（融合 LSTM 预测负载与当前 cpu 打分）

---

## 🤖 自动化实验跑批脚本

脚本：`scripts/run_experiments.py`

要求：后端已启动（默认 `http://127.0.0.1:8000`）

```bash
cd E:\SmartCity_Platform
python scripts/run_experiments.py
```

输出目录：
- `algorithms/output/experiments/<timestamp>/<strategy>/`
  - `experiment_meta.json`：实验元信息
  - `assignments.json`：任务创建与调度返回记录
  - `nodes_history.json`：实验期间节点快照（history/nodes）
