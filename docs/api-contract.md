# HTTP / WebSocket 接口契约（EdgeTwin）

本文档描述当前 `main.py` 暴露的**稳定联调约定**，便于前后端与脚本对齐。权威实现以代码为准；变更接口时请同步更新本文件。

**Base URL（本地默认）**：`http://127.0.0.1:8000`  
**OpenAPI**：`GET /docs`（Swagger UI）、`GET /openapi.json`

---

## 1. 通用约定

### 1.1 双路径策略

- **推荐**：`/api/v1/...`（版本化路径）
- **兼容**：根路径同名路由（如 `/nodes`、`/task`），供旧静态页与脚本直接使用

两者语义一致，响应体形状相同。

### 1.2 CORS

允许的来源包括（节选）：`http://127.0.0.1:8080`、`http://localhost:8080`、`http://127.0.0.1:5500`、`http://localhost:5173` 等。  
前端若使用其他 Origin，需在 `main.py` 的 `CORSMiddleware` 中补充。

### 1.3 内容类型

- JSON 接口：`Content-Type: application/json`（`POST /experiments` 使用 JSON body）
- `POST /task`、`POST /schedule` 的标量参数为 **Query**（FastAPI 默认）

### 1.4 实验状态机（SQLite `experiment.status`）

| 值 | 含义 |
|----|------|
| `created` | 已创建，未开始 |
| `running` | 已开始（`start_time` 已写） |
| `stopped` | 已结束（`end_time` 已写） |

导出脚本等若兼容历史数据，可同时接受 `finished`（见 `scripts/export_last_experiment.py`）。

---

## 2. REST 接口一览

### 2.1 节点与任务

| 方法 | 路径（v1 与根路径均存在） | 说明 |
|------|---------------------------|------|
| GET | `/api/v1/nodes` 或 `/nodes` | 当前内存中的节点列表 |
| GET | `/api/v1/tasks` 或 `/tasks` | 待处理任务数 + 任务列表 |
| POST | `/api/v1/task` 或 `/task` | 创建任务 |

**创建任务**

- Query：`cpu_need`（float，必填）
- 成功示例：`{"message": "任务创建成功", "task": {"id": 1, "cpu_need": 5.0, "status": "waiting"}}`

### 2.2 调度

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/schedule` 或 `/schedule` | 对队列中**下一个**任务执行调度 |

- Query：`strategy`（string，默认 `least_load`）
- 可选值（与 `algorithms/scheduler.py` 一致）：`random`、`least_load`、`round_robin`、`shortest_queue`、`predict_least_load`、`predictive`
- 成功：含 `message`、`strategy`、`task_details`、`node_id`、`node_name`、`node_cpu_before`、`node_cpu_after` 等
- 无任务：`{"error": "当前没有待处理的任务"}`
- 未知策略：返回 `error` 并将任务放回队列

### 2.3 预测（CSV 训练链路）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/predict` 或 `/predict` | LSTM 预测（`algorithms.predictor.get_predictions`） |

- Query：`steps`（int，默认 `10`）
- 成功：`{"steps": [1,2,...], "predicted_load": [...]}`

### 2.4 实验（SQLite）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/experiments` | 创建实验 |
| POST | `/api/v1/experiments/{experiment_id}/start` | 开始 |
| POST | `/api/v1/experiments/{experiment_id}/stop` | 停止 |
| GET | `/api/v1/experiments` | 列表 |
| GET | `/api/v1/experiments/{experiment_id}` | 单条 |
| GET | `/api/v1/experiments/{experiment_id}/history/nodes` | 时间窗内节点快照 |

**创建实验**

- Body：`{"experiment_name": "string"}`（JSON）
- 返回：实验对象（含 `id`、`status` 等）

**历史节点**

- Query：`limit`（默认 500）、`offset`（默认 0）
- 成功：`{"experiment": {...}, "nodes": [...]}`
- 异常：可能返回 `{"error": "..."}`

---

## 3. WebSocket

| URL | 用途 |
|-----|------|
| `ws://127.0.0.1:8000/ws/nodes` | 模拟器节点快照广播（JSON，含 `predicted` 等） |
| `ws://127.0.0.1:8000/api/v1/ws/nodes` | 同上（带版本前缀） |
| `ws://127.0.0.1:8000/ws/dashboard` | 大屏专用：约每 2s 推送 `nodes` + `chart`（真实历史 + 预测序列） |

客户端需周期性发送帧（如文本 `ping`）以满足代理保活；详见 `docs/ws-troubleshooting.md`。

---

## 4. 数据库文件

默认 SQLite 路径：**项目根目录下 `smart_city.db`**（与 `backend/database.py` 中 `DB_PATH` 一致）。

---

## 5. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-04-07 | 初版：与当前 `main` 路由及实验状态 `stopped` 对齐 |
