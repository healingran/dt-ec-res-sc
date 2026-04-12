import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import requests


API_BASE = os.environ.get("SMARTCITY_API_BASE", "http://127.0.0.1:8000")


@dataclass
class ExperimentRunConfig:
    experiment_name: str
    strategy: str
    tasks: List[float]
    pause_s: float = 0.1
    settle_s: float = 6.0


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def post(path: str, **kwargs):
    return requests.post(f"{API_BASE}{path}", timeout=20, **kwargs)


def get(path: str, **kwargs):
    return requests.get(f"{API_BASE}{path}", timeout=20, **kwargs)


def create_experiment(name: str) -> Dict:
    r = post("/api/v1/experiments", json={"experiment_name": name})
    r.raise_for_status()
    return r.json()


def start_experiment(exp_id: int) -> Dict:
    r = post(f"/api/v1/experiments/{exp_id}/start")
    r.raise_for_status()
    return r.json()


def stop_experiment(exp_id: int) -> Dict:
    r = post(f"/api/v1/experiments/{exp_id}/stop")
    r.raise_for_status()
    return r.json()


def create_task(cpu_need: float) -> Dict:
    # FastAPI 默认将简单参数当 query 处理
    r = post("/api/v1/task", params={"cpu_need": cpu_need})
    r.raise_for_status()
    return r.json()


def schedule(strategy: str) -> Dict:
    r = post("/api/v1/schedule", params={"strategy": strategy})
    r.raise_for_status()
    return r.json()


def fetch_nodes_history(exp_id: int, limit: int = 5000) -> Dict:
    r = get(f"/api/v1/experiments/{exp_id}/history/nodes", params={"limit": limit, "offset": 0})
    r.raise_for_status()
    return r.json()


def run_one(cfg: ExperimentRunConfig, out_dir: str) -> None:
    exp = create_experiment(cfg.experiment_name)
    exp_id = exp["id"]
    start = start_experiment(exp_id)

    assignments = []
    for cpu_need in cfg.tasks:
        t = create_task(cpu_need)
        s = schedule(cfg.strategy)
        assignments.append({"task": t, "schedule": s})
        time.sleep(cfg.pause_s)

    time.sleep(cfg.settle_s)
    stop = stop_experiment(exp_id)
    history = fetch_nodes_history(exp_id)

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "experiment_meta.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "api_base": API_BASE,
                "strategy": cfg.strategy,
                "experiment": {"created": exp, "started": start, "stopped": stop},
                "task_count": len(cfg.tasks),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    with open(os.path.join(out_dir, "assignments.json"), "w", encoding="utf-8") as f:
        json.dump(assignments, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, "nodes_history.json"), "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def main():
    # 默认任务序列：可按需要调整
    tasks = [5, 3, 8, 2, 6, 4, 7, 1, 9, 2]
    strategies = [
        "least_load",
        "round_robin",
        "shortest_queue",
        "predict_least_load",
        "sla_predict",
    ]

    root = os.path.join("algorithms", "output", "experiments", _ts())
    for strat in strategies:
        exp_name = f"exp_{strat}_{_ts()}"
        out_dir = os.path.join(root, strat)
        print(f"== Running {strat} -> {out_dir}")
        run_one(ExperimentRunConfig(experiment_name=exp_name, strategy=strat, tasks=tasks), out_dir)

    print("Done. Outputs:", os.path.abspath(root))


if __name__ == "__main__":
    main()

