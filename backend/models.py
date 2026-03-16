# backend/models.py
nodes = [
    {"id": 1, "name": "Edge-Node-01", "cpu": 10.0, "mem": 20.0, "status": "online"},
    {"id": 2, "name": "Edge-Node-02", "cpu": 40.0, "mem": 50.0, "status": "online"},
    {"id": 3, "name": "Edge-Node-03", "cpu": 85.0, "mem": 70.0, "status": "online"},
]
tasks = []
task_counter = {"current": 1}