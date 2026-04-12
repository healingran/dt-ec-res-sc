# SQLite 数据表结构设计文档

## 📊 表结构概览

本项目包含核心数据表，用于存储实验记录、节点监控数据与任务级事件：

| 表名 | 用途 | 记录数（示例） |
|------|------|----------------|
| `experiment` | 存储实验元数据 | 实验个数（如 5 个） |
| `nodes` | 存储节点实时监控数据 | 节点快照数（如 500 条） |
| `tasks_history` | 任务事件（到达、分配、完成、超时） | 与调度次数相关 |

## 📋 1. 实验记录表（experiment）

| 字段名 | 类型 | 约束 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 实验唯一标识，自增主键 | 1, 2, 3, ... |
| `experiment_name` | TEXT | NOT NULL | 实验名称（用户自定义） | "负载测试_2025-04-05" |
| `start_time` | REAL | NULL | 实验开始时间（Unix 时间戳） | 1743840000.0 |
| `end_time` | REAL | NULL | 实验结束时间（Unix 时间戳） | 1743843600.0 |
| `status` | TEXT | DEFAULT 'created' | 实验状态：created / running / finished | "running" |

**表关系**：
- 一个实验（`experiment.id`）对应多个节点监控记录（`nodes` 表，通过时间戳关联）

---

## 📋 2. 节点监控表（nodes）

| 字段名 | 类型 | 约束 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 记录唯一标识，自增主键 | 1001, 1002, ... |
| `node_name` | TEXT | NOT NULL | 节点名称/标识 | "node-001", "server-A" |
| `cpu` | REAL | NOT NULL | CPU 使用率（0.0 ~ 1.0 或 0~100%） | 0.65（表示 65%） |
| `mem` | REAL | NOT NULL | 内存使用率（0.0 ~ 1.0 或 0~100%） | 0.78（表示 78%） |
| `status` | TEXT | NOT NULL | 节点状态 | "online", "offline", "error" |
| `timestamp` | REAL | NOT NULL | 记录时间戳（Unix 时间戳） | 1743840123.456 |

**索引**：
- `idx_nodes_node_name`：加速按节点名查询
- `idx_nodes_timestamp`：加速按时间范围查询

---

## 📋 3. 任务事件表（tasks_history）

| 字段名 | 类型 | 约束 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 行号 | 1, 2, … |
| `task_id` | TEXT | NOT NULL | 任务标识（与内存队列中 `task_id` 或 `id` 一致） | `task_12`, `42` |
| `status` | TEXT | NOT NULL | `arrived` / `assigned` / `completed` / `timeout` | `assigned` |
| `node_name` | TEXT | NULL | 分配到的边缘节点名（仅 `assigned` 时有意义） | `Edge-Node-02` |
| `timestamp` | REAL | NOT NULL | Unix 时间戳 | 1743840123.456 |

**索引**：`idx_tasks_history_task_id`、`idx_tasks_history_ts`

**与实验关联**：与 `nodes` 相同，按**时间窗**与 `experiment.start_time`～`end_time` 对齐查询；导出见 `scripts/export_last_experiment.py`。

---

## 🎯 最小字段口径说明

### 1. 实验记录（experiment）
**必需字段**：
- `experiment_name`：实验名称（必须）
- `status`：状态标识（created/running/finished）

**可选字段**：
- `start_time` / `end_time`：实验时间窗口（可为 NULL，表示未开始/未结束）

### 2. 节点监控（nodes）
**必需字段**：
- `node_name`：节点标识
- `cpu` / `mem`：资源使用率
- `status`：节点状态
- `timestamp`：记录时间

---

## 🔍 数据关联规则

### 1. 实验与节点的关联方式
由于表中没有直接的 `experiment_id` 外键，实验与节点的关联通过**时间窗口**实现：

sql
-- 查询实验期间的所有节点记录
SELECT * FROM nodes
WHERE timestamp BETWEEN
(SELECT start_time FROM experiment WHERE id = 1)
AND
(SELECT end_time FROM experiment WHERE id = 1);

### 2. 状态流转规则
- 实验状态：`created` → `running` → `finished`
- 节点状态：`online` / `offline` / `error`

---

## 📁 样例数据生成脚本

在 `scripts/` 目录下创建 `generate_sample_data.py`：

python
import sqlite3
import time
import random
from datetime import datetime, timedelta
def generate_sample_data(db_path="smart_city.db"):
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 1. 插入实验记录
experiments = [
    ("负载压力测试_2025-04-05", time.time() - 3600, time.time(), "finished"),
    ("网络延迟测试_2025-04-05", time.time() - 1800, None, "running"),
    ("内存泄漏检测_2025-04-04", time.time() - 7200, time.time() - 3600, "finished"),
]

cur.executemany(
    "INSERT INTO experiment (experiment_name, start_time, end_time, status) VALUES (?, ?, ?, ?)",
    experiments
)

# 2. 插入节点监控数据
node_names = ["node-001", "node-002", "node-003", "node-004"]
base_time = time.time() - 3600  # 1小时前开始

for i in range(100):  # 生成100条节点记录
    for node in node_names:
        cur.execute(
            "INSERT INTO nodes (node_name, cpu, mem, status, timestamp) VALUES (?, ?, ?, ?, ?)",
            (
                node,
                round(random.uniform(0.1, 0.9), 2),  # cpu: 10%~90%
                round(random.uniform(0.2, 0.8), 2),  # mem: 20%~80%
                random.choice(["online", "online", "online", "offline", "error"]),
                base_time + i * 60  # 每分钟一条
            )
        )

conn.commit()
conn.close()
print("✅ 样例数据生成完成！")
print(f"   - 实验记录：{len(experiments)} 条")
print(f"   - 节点监控：{100 * len(node_names)} 条")

if name== "main":
generate_sample_data()
---

## 🧪 数据验证脚本

在 `scripts/` 目录下创建 `validate_schema.py`：
python
import sqlite3
def validate_database(db_path="smart_city.db"):
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("🔍 数据库结构验证")
print("=" * 50)

# 1. 检查表是否存在
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print(f"✅ 发现 {len(tables)} 个表：")
for table in tables:
    print(f"   - {table[0]}")

# 2. 检查 experiment 表结构
print("\n📋 experiment 表结构：")
cur.execute("PRAGMA table_info(experiment)")
for col in cur.fetchall():
    print(f"   {col[1]:<20} {col[2]:<10} {'NOT NULL' if col[3] else 'NULL':<10} {col[5] or ''}")

# 3. 检查 nodes 表结构
print("\n📋 nodes 表结构：")
cur.execute("PRAGMA table_info(nodes)")
for col in cur.fetchall():
    print(f"   {col[1]:<20} {col[2]:<10} {'NOT NULL' if col[3] else 'NULL':<10} {col[5] or ''}")

# 4. 检查索引
print("\n🔍 索引检查：")
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
for idx in cur.fetchall():
    print(f"   - {idx[0]}")

# 5. 统计数据量
cur.execute("SELECT COUNT(*) FROM experiment")
exp_count = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM nodes")
node_count = cur.fetchone()[0]

print(f"\n📊 数据统计：")
print(f"   - 实验记录：{exp_count} 条")
print(f"   - 节点监控：{node_count} 条")

conn.close()
if name== "main":
validate_database()

---

## ✅ 交付物检查清单

- [x] `docs/data-schema.md` - 数据表结构设计文档
- [x] `scripts/generate_sample_data.py` - 样例数据生成脚本
- [x] `scripts/validate_schema.py` - 数据验证脚本
- [x] 明确实验记录与节点历史的最小字段口径
- [x] 提供数据关联规则和状态流转说明

---

## 📌 使用说明

1. **初始化数据库**：
bash
python init_db.py
2. **生成样例数据**：
bash
python scripts/generate_sample_data.py
3. **验证数据结构**：
bash
python scripts/validate_schema.py
---

*文档版本：1.0*  
*最后更新：2025-04-05*  
*维护者：智能城市平台团队*