"""
模拟器状态快照（只读视图）。

比赛分支已在 main.py 中维护场景、策略与任务队列；此处提供与文档一致的聚合结构，
避免再维护一套独立的 SimulatorState，防止与 current_scene_mode 分叉。
"""
from __future__ import annotations

import time
from typing import Any, Dict


def build_sim_state_snapshot(
    *,
    scene_mode: str,
    scene_config: Dict[str, Dict[str, float]],
    pending_task_count: int,
    task_counter_next: int,
    scheduler_strategy: str,
    experiment: Any,
) -> Dict[str, Any]:
    cfg = scene_config.get(scene_mode) or scene_config.get("offpeak", {})
    return {
        "current_mode": scene_mode,
        "base_load": cfg.get("base_load"),
        "burst_intensity": cfg.get("burst_intensity"),
        "pending_tasks": pending_task_count,
        "task_counter_next": task_counter_next,
        "scheduler_strategy": scheduler_strategy,
        "experiment": experiment,
        "timestamp": time.time(),
    }
