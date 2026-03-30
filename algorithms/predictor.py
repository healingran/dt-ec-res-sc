# algorithms/predictor.py
import torch
import torch.nn as nn
import numpy as np
import os
import joblib
from collections import deque

# 定义与 train_model.py 相同的模型结构
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
SCALER_PATH = "algorithms/model_save/scaler.joblib"
WINDOW_SIZE = 30

# 存储节点历史数据
_node_history = deque(maxlen=200)

def update_node_history(cpu_value):
    """更新节点历史数据"""
    _node_history.append(cpu_value)

def clear_node_history():
    """清空历史数据"""
    _node_history.clear()

# 加载模型
model = LSTMPredictor()
scaler = None

if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
    model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device('cpu')))
    model.eval()
    scaler = joblib.load(SCALER_PATH)
    print("✅ [Predictor] 已成功加载 LSTM 模型")
else:
    print("⚠️ [Predictor] 未找到模型，请先运行 algorithms/train_model.py")

def get_predictions(steps=10):
    """获取预测结果"""
    global _node_history
    
    # 获取历史数据
    history_data = list(_node_history)
    
    # 数据不足时填充
    if len(history_data) < WINDOW_SIZE:
        if not history_data:
            history_data = [50.0] * WINDOW_SIZE
        else:
            pad_length = WINDOW_SIZE - len(history_data)
            history_data = [history_data[0]] * pad_length + history_data
    
    # 只取最后 WINDOW_SIZE 个
    history_data = history_data[-WINDOW_SIZE:]
    
    # 归一化
    seq = np.array(history_data).reshape(-1, 1)
    if scaler:
        seq = scaler.transform(seq)
    
    # 转为 Tensor
    current_seq = torch.tensor(seq, dtype=torch.float32).view(1, WINDOW_SIZE, 1)
    
    # 预测
    preds = []
    with torch.no_grad():
        for _ in range(steps):
            pred = model(current_seq)
            preds.append(pred.item())
            current_seq = torch.cat((current_seq[:, 1:, :], pred.view(1, 1, 1)), dim=1)
    
    # 反归一化
    final_preds = np.array(preds).reshape(-1, 1)
    if scaler:
        final_preds = scaler.inverse_transform(final_preds)
    
    return {
        "steps": list(range(1, steps + 1)),
        "predicted_load": [round(float(v), 2) for v in final_preds.flatten()]
    }