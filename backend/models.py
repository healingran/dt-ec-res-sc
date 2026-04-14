# backend/models.py
nodes = [
    {
        "id": 1,
        "name": "Edge-Node-01",
        "cpu": 10.0,
        "mem": 20.0,
        "status": "online",
        "queue_len": 0,
        # 简化网络能力：用于 SLA 估算的带宽（kbps）
        "bw_kbps": 50_000,
    },
    {
        "id": 2,
        "name": "Edge-Node-02",
        "cpu": 40.0,
        "mem": 50.0,
        "status": "online",
        "queue_len": 0,
        "bw_kbps": 30_000,
    },
    {
        "id": 3,
        "name": "Edge-Node-03",
        "cpu": 85.0,
        "mem": 70.0,
        "status": "online",
        "queue_len": 0,
        "bw_kbps": 20_000,
    },
]
tasks = []
task_counter = {"current": 1}
