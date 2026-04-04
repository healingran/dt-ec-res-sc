"""Dashboard 用：节点 1 的 CPU 采样历史，供 WebSocket 推送与真实/预测曲线对齐。"""
from collections import deque

# 边缘节点 1（展示用）的 CPU 历史采样
CPU_HISTORY: deque[float] = deque(maxlen=45)


def append_node1_cpu(cpu: float) -> None:
    CPU_HISTORY.append(round(float(cpu), 2))


def clear_history() -> None:
    CPU_HISTORY.clear()
