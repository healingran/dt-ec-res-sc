"""
Predictive scheduling policy extracted from `origin/wangjin_lstm:algorithms/scheduler.py`,
refactored into a pure function module.

This file DOES NOT modify your existing scheduler or routes.
You can import and call `pick_node_by_prediction(...)` from your current scheduler
if/when you decide to wire it in.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Sequence


def pick_node_by_prediction(
    nodes: Sequence[Dict[str, Any]],
    *,
    get_predictions: Callable[[int], Dict[str, Any]],
    steps: int = 5,
    trend_threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Choose a node based on predicted load trend.

    - `get_predictions(steps)` should return {"predicted_load": [...]}.
    - Current implementation mirrors Wang Jin's logic: if trend rising, pick lowest-cpu node;
      else also pick lowest-cpu node. (Hook is here; you can extend scoring later.)
    """
    if not nodes:
        raise ValueError("nodes is empty")

    try:
        prediction_data = get_predictions(int(steps))
        predicted_loads: List[float] = list(prediction_data.get("predicted_load") or [])
        if len(predicted_loads) < 2:
            return min(nodes, key=lambda x: float(x.get("cpu", 0.0)))

        trend = float(predicted_loads[-1]) - float(predicted_loads[0])
        if trend > float(trend_threshold):
            return min(nodes, key=lambda x: float(x.get("cpu", 0.0)))
        return min(nodes, key=lambda x: float(x.get("cpu", 0.0)))
    except Exception:
        return min(nodes, key=lambda x: float(x.get("cpu", 0.0)))

