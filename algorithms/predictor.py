# algorithms/predictor.py
"""LSTM 负载预测，供 API 调用"""
import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler

# 缓存：首次请求时训练，后续复用
_model = None
_scaler = None
_data_scaled = None
_window = 30


def _get_base_path():
    """获取项目根目录（main.py 所在目录）"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class LSTMPredictor(nn.Module):
    def __init__(self, input_size=1, hidden_size=128, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out


def _train_and_cache():
    """加载数据、训练模型并缓存"""
    global _model, _scaler, _data_scaled, _window
    base = _get_base_path()
    df = pd.read_csv(os.path.join(base, "algorithms/data/load_data.csv"))
    data = df["load"].values.reshape(-1, 1)

    _scaler = MinMaxScaler()
    _data_scaled = _scaler.fit_transform(data)

    def create_sequences(data, window=30):
        X, y = [], []
        for i in range(len(data) - window):
            X.append(data[i : i + window])
            y.append(data[i + window])
        return np.array(X), np.array(y)

    X, y = create_sequences(_data_scaled, _window)
    split = int(0.8 * len(X))
    X_train, y_train = X[:split], y[:split]

    X_train_t = torch.tensor(X_train, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.float32)

    model = LSTMPredictor()
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    epochs = 100

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        output = model(X_train_t)
        loss = criterion(output, y_train_t)
        loss.backward()
        optimizer.step()
        if (epoch + 1) % 20 == 0:
            print(f"[LSTM] Epoch {epoch+1}/{epochs}, Loss: {loss.item():.6f}")

    _model = model.eval()
    print("[LSTM] 模型训练完成，已缓存")


def get_predictions(steps: int = 10) -> dict:
    """
    获取未来负载预测
    :param steps: 预测步数，默认 10
    :return: {"steps": [...], "predicted_load": [...]}
    """
    global _model, _scaler, _data_scaled
    if _model is None or _scaler is None or _data_scaled is None:
        _train_and_cache()

    with torch.no_grad():
        last_seq = _data_scaled[-_window:].reshape(1, _window, 1)
        future_preds = []
        for _ in range(steps):
            pred = _model(torch.tensor(last_seq, dtype=torch.float32))
            future_preds.append(pred.item())
            last_seq = np.roll(last_seq, -1, axis=1)
            last_seq[0, -1, 0] = pred.item()

    future_preds = np.array(future_preds).reshape(-1, 1)
    future_preds = _scaler.inverse_transform(future_preds)
    values = [round(float(v), 4) for v in future_preds.flatten()]

    return {
        "steps": list(range(1, steps + 1)),
        "predicted_load": values,
    }
