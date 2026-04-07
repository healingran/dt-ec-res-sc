# 演示与联调 Runbook（李欣然线）

本手册用于**验收演示、课堂展示、新成员第一次跑通**：后端、大屏、实验 API、调度与导出脚本。

---

## 1. 环境前提

- Windows 10/11（本仓库脚本以 PowerShell 为主）
- Python 3.10+，已执行 `python -m pip install -r requirements.txt`
- 建议使用项目内虚拟环境：`.venv`

---

## 2. 一键启动后端

在项目根目录 `E:\dt-ec-res-sc2`（按你本机路径调整）：

```powershell
.\start_backend.ps1
```

说明：

- 若存在 `.venv`，会自动激活后再执行 `python main.py`
- 服务监听 **`http://127.0.0.1:8000`**
- 控制台出现 `Uvicorn running` 即就绪

**仅检测后端是否已响应**（不启动进程）：

```powershell
.\start_backend.ps1 -HealthOnly
```

成功则打印 `OK` 并以退出码 0 结束；失败退出码 1。

---

## 3. 打开 API 文档（Swagger）

浏览器访问：

`http://127.0.0.1:8000/docs`

可在此按顺序试用接口；字段与路径以 **`docs/api-contract.md`** 为准。

---

## 4. 标准实验流程（P0 演示）

在 Swagger 中依次执行：

1. `POST /api/v1/experiments`，Body：`{"experiment_name": "demo_run_1"}`
2. 记下返回中的 `id`，例如 `1`
3. `POST /api/v1/experiments/1/start`
4. 等待 **5～10 秒**（模拟器持续写入 `nodes` 表）
5. `POST /api/v1/experiments/1/stop`
6. `GET /api/v1/experiments/1/history/nodes?limit=500`

预期：`experiment.status` 为 **`stopped`**，`nodes` 数组含时间窗内快照。

---

## 5. 调度演示（与大屏联动）

1. `POST /api/v1/task?cpu_need=5`（可多次）
2. `POST /api/v1/schedule?strategy=predict_least_load`（或 `least_load` 等）

预期：返回中含 `node_cpu_before` / `node_cpu_after` 等；无任务时返回 `error` 提示。

---

## 6. 打开可视化大屏

**勿使用** `python -m http.server` 直接托管（Windows 下 `.js` MIME 易导致模块脚本失败）。

在**另一终端**：

```powershell
cd E:\dt-ec-res-sc2\frontend
python serve.py
```

浏览器打开：

`http://127.0.0.1:8080/dashboard.html`

前提：后端已在跑；右上角 WS 状态应变为已连接。若异常见 `docs/ws-troubleshooting.md`。

---

## 7. 导出最近一次已结束实验

在后端已生成 `smart_city.db` 的前提下：

```powershell
cd E:\dt-ec-res-sc2
python scripts/export_last_experiment.py --db-path smart_city.db --output-dir output --format json
```

说明见 `scripts/README.md`。

---

## 8. 自动化跑批（可选）

```powershell
# 先启动后端
python scripts/run_experiments.py
```

输出目录默认在 `algorithms/output/experiments/<时间戳>/`。

---

## 9. 常见问题速查

| 现象 | 处理 |
|------|------|
| 大屏 WS 一直未连接 | 是否用 `frontend/serve.py`；是否 `127.0.0.1:8080` 打开；后端是否监听 8000 |
| 首次打开 `/predict` 很慢 | CSV 链路首次会训练模型，属预期；演示可先只开大屏与调度 |
| 导出提示无已完成实验 | 主线结束状态为 **`stopped`**，需先 `stop` 实验；脚本已兼容 `finished` |

---

## 10. 相关文档

- 接口字段与路径：`docs/api-contract.md`
- 表结构：`docs/data-schema.md`
- WebSocket 排查：`docs/ws-troubleshooting.md`
