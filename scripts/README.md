# 实验结果导出工具使用指南

## 📋 工具简介

`export_last_experiment.py` 是一个独立的命令行工具，用于从 SQLite 数据库中导出**最近一次完成的实验**及其对应的节点监控数据。

该工具支持：
- ✅ **JSON 格式**：完整的结构化数据，便于程序解析
- ✅ **CSV 格式**：便于 Excel 等工具分析
- ✅ **命令行参数**：灵活配置数据库路径、输出格式、输出目录
- ✅ **自动检测**：自动查找最近一次完成的实验

---

## 📁 文件结构

scripts/
├── export_last_experiment.py # 导出工具主脚本
└── README.md # 本文档
输出目录（默认）：
output/
├── experiment_1负载测试20250405_143000.json
├── experiment_1负载测试20250405_143000_experiments.csv
└── experiment_1负载测试20250405_143000_nodes.csv

---

## 🚀 快速开始

### 1. 确保数据库存在
首先确认你的数据库中有已完成的实验记录：

sql
-- 检查实验记录
SELECT * FROM experiment WHERE status = 'finished' ORDER BY end_time DESC LIMIT 1;
如果没有数据，可以先运行数据生成脚本（如果已创建）：
bash
python scripts/generate_sample_data.py
### 2. 安装依赖
本工具使用 Python 标准库，无需额外安装依赖。

### 3. 导出为 JSON（默认）
bash
python scripts/export_last_experiment.py
### 4. 导出为 CSV
bash
python scripts/export_last_experiment.py --format csv
---

## ⚙️ 命令行参数

| 参数 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--db-path` | 无 | `smart_city.db` | SQLite 数据库文件路径 |
| `--format` | 无 | `json` | 输出格式：`json` 或 `csv` |
| `--output-dir` | 无 | `output` | 输出文件保存目录 |

**示例**：
bash
## 指定自定义数据库路径
python scripts/export_last_experiment.py --db-path my_data.db
## 导出为 CSV 到指定目录
python scripts/export_last_experiment.py --format csv --output-dir exports
---

## 📄 输出文件说明

### JSON 格式输出
文件：`experiment_{id}_{name}_{timestamp}.json`

json
{
"export_info": {
"timestamp": "2025-04-05T14:30:00.123456",
"format": "json",
"experiment_count": 1,
"node_count": 125
},
"experiments": [
{
"id": 1,
"name": "负载压力测试_2025-04-05",
"start_time": 1743840000.0,
"end_time": 1743843600.0,
"status": "finished"
}
],
"nodes": [
{
"node_name": "node-001",
"cpu": 0.65,
"mem": 0.78,
"status": "online",
"timestamp": 1743840123.456
}
]
}

### CSV 格式输出
CSV 格式会生成两个文件：

1. **实验信息文件**：`experiment_{id}_{name}_{timestamp}_experiments.csv`
id,name,start_time,end_time,status
1,负载压力测试_2025-04-05,1743840000.0,1743843600.0,finished
2. **节点信息文件**：`experiment_{id}_{name}_{timestamp}_nodes.csv`
experiment_id,experiment_name,node_name,cpu,mem,status,timestamp
1,负载压力测试_2025-04-05,node-001,0.65,0.78,online,1743840123.456
1,负载压力测试_2025-04-05,node-002,0.42,0.56,online,1743840156.789
---

## 🔍 与历史查询接口的关系

本工具与 Web API 接口 `/api/v1/experiments/{id}/history/nodes` 的功能对比：

| 特性 | 导出工具 | Web API |
|------|----------|---------|
| 数据来源 | 直接读取数据库 | 通过 `db.get_nodes_history()` |
| 输出格式 | JSON/CSV 文件 | JSON 响应（HTTP） |
| 使用场景 | 离线分析、数据备份 | 实时查询、前端展示 |
| 查询条件 | 最近一次完成的实验 | 指定实验ID |

**互补关系**：
- **Web API**：适合实时交互、前端集成
- **导出工具**：适合批量导出、数据备份、离线分析

---

## 🧪 验证导出结果

### 验证 JSON 文件
bash
## 查看文件基本信息
head -n 20 output/experiment_*.json
## 使用 jq 工具查看（如果已安装）
jq '.export_info' output/experiment_*.json
### 验证 CSV 文件
bash
## 查看文件行数
wc -l output/*.csv
## 查看前几行
head -n 5 output/*.csv
---

## ❌ 常见问题

### 1. "未找到已完成的实验记录"
**原因**：数据库中没有 `status='finished'` 的实验记录
**解决**：
sql
-- 检查实验状态
SELECT id, experiment_name, status FROM experiment;
-- 将实验状态更新为 finished
UPDATE experiment SET status = 'finished' WHERE id = 1;
### 2. 数据库文件不存在
**解决**：确保数据库文件路径正确，或先初始化数据库：
bash
python init_db.py
### 3. 输出目录权限问题
**解决**：确保有写入权限，或指定其他目录：
bash
python scripts/export_last_experiment.py --output-dir /tmp/exports
---

## 📞 技术支持

如有问题，请检查：
1. 数据库文件是否存在且有数据
2. Python 版本是否为 3.7+
3. 输出目录是否有写入权限

如需进一步帮助，请联系智能城市平台团队。

---

*文档版本：1.0*  
*最后更新：2025-04-05*  
*工具版本：export_last_experiment.py v1.0*