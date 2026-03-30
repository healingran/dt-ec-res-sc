# fix_model.py
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

# 确保保存目录存在
os.makedirs("algorithms/model_save", exist_ok=True)
os.makedirs("algorithms/data", exist_ok=True)

print("="*50)
print("重新生成匹配真实场景的训练数据")
print("="*50)

# 生成更符合真实场景的数据（负载范围 10-100）
np.random.seed(42)

# 生成 2000 个时间点
time = np.arange(0, 2000)

# 模拟真实节点负载模式
trend = 0.005 * time  # 缓慢上升趋势
seasonal = 15 * np.sin(2 * np.pi * time / 48)  # 周期波动
noise = np.random.normal(0, 2, len(time))  # 随机噪声

# 合成负载，范围控制在 10-100 之间
load = 50 + trend + seasonal + noise  # 基础负载 50%
load = np.clip(load, 10, 100)  # 限制在 10-100

# 构造 DataFrame
df = pd.DataFrame({
    'timestamp': time,
    'load': load
})

# 保存为 CSV
df.to_csv('algorithms/data/load_data.csv', index=False)
print(f"✅ 生成 {len(df)} 条数据，负载范围: {load.min():.1f}% - {load.max():.1f}%")

print("\n" + "="*50)
print("重新训练 LSTM 模型")
print("="*50)

# 定义模型
class LSTMPredictor(nn.Module):
    def __init__(self, input_size=1, hidden_size=128, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

# 读取数据
df = pd.read_csv('algorithms/data/load_data.csv')
data = df['load'].values.reshape(-1, 1)

# 归一化
scaler = MinMaxScaler()
data_scaled = scaler.fit_transform(data)
joblib.dump(scaler, 'algorithms/model_save/scaler.joblib')
print(f"✅ Scaler 已保存，数据范围: {data.min():.1f} - {data.max():.1f}")

# 构造数据
window = 30
X, y = [], []
for i in range(len(data_scaled) - window):
    X.append(data_scaled[i:i+window])
    y.append(data_scaled[i+window])

X_train = torch.tensor(np.array(X), dtype=torch.float32)
y_train = torch.tensor(np.array(y), dtype=torch.float32)

print(f"✅ 训练数据: X {X_train.shape}, y {y_train.shape}")

# 训练模型
model = LSTMPredictor()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
criterion = nn.MSELoss()

print("\n开始训练...")
model.train()
for epoch in range(100):
    optimizer.zero_grad()
    output = model(X_train)
    loss = criterion(output, y_train)
    loss.backward()
    optimizer.step()
    
    if (epoch + 1) % 20 == 0:
        print(f"  Epoch {epoch+1}/100, Loss: {loss.item():.6f}")

# 保存模型
torch.save(model.state_dict(), 'algorithms/model_save/lstm_model.pth')
print("\n✅ 模型已保存到 algorithms/model_save/lstm_model.pth")

# 测试预测
print("\n" + "="*50)
print("测试新模型预测")
print("="*50)

# 用最后30个数据预测
last_seq = data_scaled[-window:].reshape(1, window, 1)
model.eval()
with torch.no_grad():
    preds = []
    for _ in range(5):
        pred = model(torch.tensor(last_seq, dtype=torch.float32))
        preds.append(pred.item())
        last_seq = np.roll(last_seq, -1, axis=1)
        last_seq[0, -1, 0] = pred.item()

# 反归一化
preds = np.array(preds).reshape(-1, 1)
preds_real = scaler.inverse_transform(preds)

print(f"最近实际负载: {data[-10:].flatten()}")
print(f"预测未来5步: {preds_real.flatten()}")

print("\n✅ 模型修复完成！")