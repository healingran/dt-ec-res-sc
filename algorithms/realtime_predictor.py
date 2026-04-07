"""
Realtime predictor extracted from `origin/wangjin_lstm:algorithms/predictor.py`,
but refactored to:
- avoid joblib dependency (uses stdlib pickle)
- avoid side-effect prints on import
- expose a small, testable API

This module is SAFE to import from your existing code without modifying routes/websockets.
"""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Optional

import numpy as np
import torch
import torch.nn as nn


class LSTMPredictor(nn.Module):
    def __init__(self, input_size: int = 1, hidden_size: int = 64, num_layers: int = 2) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


def _load_pickle(path: str):
    import pickle

    with open(path, "rb") as f:
        return pickle.load(f)


@dataclass
class PredictorAssets:
    model: LSTMPredictor
    scaler: Optional[object]  # typically sklearn MinMaxScaler
    window_size: int = 30


class RealtimePredictor:
    def __init__(
        self,
        *,
        model_path: str = "algorithms/model_save/lstm_model.pth",
        scaler_path: str = "algorithms/model_save/scaler.pkl",
        window_size: int = 30,
        history_maxlen: int = 200,
        tracked_node_id: int = 1,
    ) -> None:
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.window_size = int(window_size)
        self.tracked_node_id = int(tracked_node_id)
        self._history: Deque[float] = deque(maxlen=int(history_maxlen))
        self._assets: Optional[PredictorAssets] = None

    def update(self, cpu_value: float, *, node_id: int | None = None) -> None:
        """只写入指定节点（默认 tracked_node_id）的 CPU，避免多节点序列交叉污染。"""
        if node_id is None or int(node_id) != self.tracked_node_id:
            return
        self._history.append(float(cpu_value))

    def clear(self) -> None:
        self._history.clear()

    def _ensure_assets(self) -> PredictorAssets:
        if self._assets is not None:
            return self._assets

        model = LSTMPredictor()
        scaler = None

        if os.path.exists(self.model_path):
            state = torch.load(self.model_path, map_location=torch.device("cpu"))
            model.load_state_dict(state)
            model.eval()
        else:
            # allow running without trained weights; outputs will be arbitrary but code paths work
            model.eval()

        if os.path.exists(self.scaler_path):
            scaler = _load_pickle(self.scaler_path)

        self._assets = PredictorAssets(model=model, scaler=scaler, window_size=self.window_size)
        return self._assets

    def predict(self, steps: int = 10) -> dict:
        assets = self._ensure_assets()
        window = assets.window_size

        history = list(self._history)
        if len(history) < window:
            if not history:
                history = [50.0] * window
            else:
                pad = window - len(history)
                history = [history[0]] * pad + history
        history = history[-window:]

        seq = np.array(history, dtype=float).reshape(-1, 1)
        if assets.scaler is not None:
            seq = assets.scaler.transform(seq)

        current_seq = torch.tensor(seq, dtype=torch.float32).view(1, window, 1)
        preds = []
        with torch.no_grad():
            for _ in range(int(steps)):
                pred = assets.model(current_seq)  # (1, 1)
                preds.append(float(pred.item()))
                current_seq = torch.cat((current_seq[:, 1:, :], pred.view(1, 1, 1)), dim=1)

        final = np.array(preds, dtype=float).reshape(-1, 1)
        if assets.scaler is not None:
            final = assets.scaler.inverse_transform(final)

        return {
            "steps": list(range(1, int(steps) + 1)),
            "predicted_load": [round(float(v), 2) for v in final.flatten()],
        }


def default_predictor() -> RealtimePredictor:
    """
    Process-local singleton predictor.
    Both simulator and scheduler can import this to share one history buffer.
    """
    global _DEFAULT_PREDICTOR
    if _DEFAULT_PREDICTOR is None:
        _DEFAULT_PREDICTOR = RealtimePredictor()
    return _DEFAULT_PREDICTOR


_DEFAULT_PREDICTOR: Optional[RealtimePredictor] = None

