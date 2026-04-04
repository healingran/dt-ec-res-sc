"""
Extracted + refactored from `origin/wangjin_lstm:algorithms/train_model.py`.

Standalone trainer that:
- optionally generates synthetic load data (same pattern as Wang Jin's script)
- trains an LSTM
- saves model weights + scaler to `algorithms/model_save/`

Does NOT modify any existing API routes, websocket logic, or frontend code.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler


class LSTMPredictor(nn.Module):
    """Matches Wang Jin's model shape (hidden_size=64, num_layers=2 by default)."""

    def __init__(self, input_size: int = 1, hidden_size: int = 64, num_layers: int = 2) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


def _save_pickle(path: str, obj) -> None:
    # Avoid adding dependencies (joblib). sklearn scalers pickle fine.
    import pickle

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(obj, f)


def _load_pickle(path: str):
    import pickle

    with open(path, "rb") as f:
        return pickle.load(f)


def generate_synthetic_load(n: int = 3000, seed: int = 42) -> pd.DataFrame:
    """Same pattern as Wang Jin's train script (trend + multi-seasonal + noise, clipped)."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, n)
    trend = 0.003 * t
    seasonal = 12 * np.sin(2 * np.pi * t / 48) + 8 * np.sin(2 * np.pi * t / 168)
    noise = rng.normal(0, 2, len(t))
    load = 50 + trend + seasonal + noise
    load = np.clip(load, 20, 95)
    return pd.DataFrame({"timestamp": t, "load": load})


def create_sequences(data_scaled: np.ndarray, window: int) -> Tuple[np.ndarray, np.ndarray]:
    x, y = [], []
    for i in range(len(data_scaled) - window):
        x.append(data_scaled[i : i + window])
        y.append(data_scaled[i + window])
    return np.asarray(x), np.asarray(y)


@dataclass(frozen=True)
class TrainConfig:
    window: int = 30
    epochs: int = 100
    lr: float = 1e-3
    hidden_size: int = 64
    num_layers: int = 2
    seed: int = 42


def train(
    series: np.ndarray,
    cfg: TrainConfig,
) -> Tuple[LSTMPredictor, MinMaxScaler, float]:
    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)

    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(series.reshape(-1, 1))

    x, y = create_sequences(data_scaled, cfg.window)
    x_t = torch.tensor(x, dtype=torch.float32)
    y_t = torch.tensor(y, dtype=torch.float32)

    model = LSTMPredictor(hidden_size=cfg.hidden_size, num_layers=cfg.num_layers)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    criterion = nn.MSELoss()

    best_loss = float("inf")
    for epoch in range(cfg.epochs):
        model.train()
        optimizer.zero_grad()
        out = model(x_t)
        loss = criterion(out, y_t)
        loss.backward()
        optimizer.step()

        best_loss = min(best_loss, float(loss.item()))
        if (epoch + 1) % 20 == 0:
            print(f"Epoch {epoch+1}/{cfg.epochs}, Loss: {loss.item():.6f}")

    model.eval()
    return model, scaler, best_loss


def predict_future(
    model: LSTMPredictor,
    scaler: MinMaxScaler,
    series: np.ndarray,
    window: int,
    steps: int,
) -> np.ndarray:
    data_scaled = scaler.transform(series.reshape(-1, 1))
    last_seq = data_scaled[-window:].reshape(1, window, 1)
    preds = []
    with torch.no_grad():
        for _ in range(steps):
            pred = model(torch.tensor(last_seq, dtype=torch.float32)).item()
            preds.append(pred)
            last_seq = np.roll(last_seq, -1, axis=1)
            last_seq[0, -1, 0] = pred

    preds_arr = np.asarray(preds).reshape(-1, 1)
    return scaler.inverse_transform(preds_arr).flatten()


def main() -> int:
    ap = argparse.ArgumentParser(description="Train LSTM model and save artifacts.")
    ap.add_argument("--data-csv", default="", help="Optional CSV with column 'load'. If empty, generate synthetic.")
    ap.add_argument("--out-dir", default=str(Path("algorithms") / "model_save"))
    ap.add_argument("--write-data", action="store_true", help="When generating synthetic, also write to algorithms/data/load_data.csv")
    ap.add_argument("--n", type=int, default=3000, help="Synthetic length")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--window", type=int, default=30)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--steps", type=int, default=10, help="Quick future prediction steps for sanity check")
    args = ap.parse_args()

    cfg = TrainConfig(window=args.window, epochs=args.epochs, lr=args.lr, seed=args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.data_csv:
        df = pd.read_csv(args.data_csv)
        if "load" not in df.columns:
            raise SystemExit("CSV missing 'load' column")
    else:
        df = generate_synthetic_load(n=args.n, seed=args.seed)
        print(f"✅ generated {len(df)} rows, range: {df['load'].min():.1f}% - {df['load'].max():.1f}%")
        if args.write_data:
            data_path = Path("algorithms") / "data" / "load_data.csv"
            data_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(data_path, index=False)
            print(f"✅ wrote {data_path}")

    series = df["load"].to_numpy(dtype=float)
    model, scaler, best_loss = train(series, cfg)

    # Save artifacts (pickle for scaler; torch for weights)
    weights_path = out_dir / "lstm_model.pth"
    scaler_path = out_dir / "scaler.pkl"
    torch.save(model.state_dict(), weights_path)
    _save_pickle(str(scaler_path), scaler)
    print(f"✅ saved model: {weights_path}")
    print(f"✅ saved scaler: {scaler_path}")
    print(f"best_loss={best_loss:.6f}")

    # Quick check prediction
    preds = predict_future(model, scaler, series, window=cfg.window, steps=args.steps)
    print("future_pred=", [round(float(v), 2) for v in preds])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

