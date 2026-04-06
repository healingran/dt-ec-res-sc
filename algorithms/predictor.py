# algorithms/predictor.py
import torch
import torch.nn as nn
import numpy as np
import os
import pickle
from collections import deque
from pathlib import Path
from typing import List, Optional

from backend.models import nodes

# 定义模型
class LSTMPredictor(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
    
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

# 全局变量
MODEL_PATH = "algorithms/model_save/lstm_model.pth"
SCALER_PATH = "algorithms/model_save/scaler.pkl"
WINDOW_SIZE = 30

# 存储实时节点历史数据
_node_history: deque = deque(maxlen=200)

# 模型和 scaler 全局变量
_model: Optional[LSTMPredictor] = None
_scaler: Optional[object] = None


def _get_base_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def update_node_history(cpu_value: float = None):
    """更新节点历史数据（从 nodes 或直接传值）"""
    if cpu_value is not None:
        _node_history.append(float(cpu_value))
    else:
        node1 = next((n for n in nodes if n.get("id") == 1), None)
        if node1:
            _node_history.append(node1["cpu"])
            return True
        return False
    return True


def get_realtime_history() -> List[float]:
    """获取实时历史数据"""
    return list(_node_history)


def clear_node_history():
    """清空历史数据"""
    _node_history.clear()
    print("✅ [Predictor] 历史数据已清空")


def load_model():
    """从磁盘加载模型（Save/Load 机制）"""
    global _model, _scaler
    
    model_path = os.path.join(_get_base_path(), MODEL_PATH)
    scaler_path = os.path.join(_get_base_path(), SCALER_PATH)
    
    if os.path.exists(model_path) and os.path.exists(scaler_path):
        _model = LSTMPredictor()
        _model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        _model.eval()
        
        with open(scaler_path, 'rb') as f:
            _scaler = pickle.load(f)
        
        print("✅ [Predictor] 模型已从磁盘加载")
        return True
    else:
        print(f"⚠️ [Predictor] 模型文件不存在 ({model_path})，请先运行 python algorithms/train_model.py")
        return False


def save_model(model, scaler):
    """保存模型到磁盘"""
    base = _get_base_path()
    model_path = os.path.join(base, MODEL_PATH)
    scaler_path = os.path.join(base, SCALER_PATH)
    
    Path(os.path.dirname(model_path)).mkdir(parents=True, exist_ok=True)
    
    torch.save(model.state_dict(), model_path)
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    
    print(f"✅ [Predictor] 模型已保存到 {model_path}")


def get_predictions(steps: int = 10) -> dict:
    """使用实时 nodes 数据进行预测"""
    global _model, _scaler
    
    if _model is None:
        if not load_model():
            return {
                "steps": list(range(1, steps + 1)),
                "predicted_load": [50.0 + i * 0.5 for i in range(steps)]
            }
    
    update_node_history()
    
    history_data = list(_node_history)
    
    if len(history_data) < WINDOW_SIZE:
        if not history_data:
            node1 = next((n for n in nodes if n.get("id") == 1), None)
            default_val = node1["cpu"] if node1 else 50.0
            history_data = [default_val] * WINDOW_SIZE
        else:
            pad_length = WINDOW_SIZE - len(history_data)
            history_data = [history_data[0]] * pad_length + history_data
    
    history_data = history_data[-WINDOW_SIZE:]
    
    seq = np.array(history_data).reshape(-1, 1)
    if _scaler is not None:
        seq = _scaler.transform(seq)
    
    current_seq = torch.tensor(seq, dtype=torch.float32).view(1, WINDOW_SIZE, 1)
    
    preds = []
    with torch.no_grad():
        for _ in range(steps):
            pred = _model(current_seq)
            preds.append(pred.item())
            current_seq = torch.cat((current_seq[:, 1:, :], pred.view(1, 1, 1)), dim=1)
    
    final_preds = np.array(preds).reshape(-1, 1)
    if _scaler is not None:
        final_preds = _scaler.inverse_transform(final_preds)
    
    return {
        "steps": list(range(1, steps + 1)),
        "predicted_load": [round(float(v), 2) for v in final_preds.flatten()]
    }


# 启动时自动加载
load_model()