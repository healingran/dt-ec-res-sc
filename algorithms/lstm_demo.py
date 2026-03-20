import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

# 设置中文字体（避免乱码）
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 1. 加载数据（从 data 文件夹）
df = pd.read_csv('algorithms/data/load_data.csv')
data = df['load'].values.reshape(-1, 1)

# 2. 归一化
scaler = MinMaxScaler()
data_scaled = scaler.fit_transform(data)

# 3. 构造训练数据
def create_sequences(data, window=30):
    X, y = [], []
    for i in range(len(data) - window):
        X.append(data[i:i+window])
        y.append(data[i+window])
    return np.array(X), np.array(y)

window = 30  
X, y = create_sequences(data_scaled, window)

# 4. 划分训练集 / 测试集
split = int(0.8 * len(X))
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

# 5. 转为 PyTorch 张量
X_train = torch.tensor(X_train, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_test = torch.tensor(y_test, dtype=torch.float32)

# 6. 定义 LSTM 模型
class LSTMPredictor(nn.Module):
    def __init__(self, input_size=1, hidden_size=128, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out

# 7. 训练
model = LSTMPredictor()
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

epochs = 100  
loss_history = []

for epoch in range(epochs):
    model.train()
    optimizer.zero_grad()
    output = model(X_train)
    loss = criterion(output, y_train)
    loss.backward()
    optimizer.step()

    loss_history.append(loss.item())

    if (epoch+1) % 10 == 0:
        print(f'Epoch {epoch+1}/{epochs}, Loss: {loss.item():.6f}')

# 8. 画 Loss 曲线（保存到 output 文件夹）
plt.figure(figsize=(10,4))
plt.plot(loss_history)
plt.title('Loss 下降曲线')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.grid()
plt.savefig('algorithms/output/loss_curve.png')
plt.show()

# 9. 测试集评估
model.eval()
with torch.no_grad():
    y_pred = model(X_test)
    test_loss = criterion(y_pred, y_test)
    print(f"\n📊 测试集 Loss: {test_loss.item():.6f}")

# 10. 画测试集对比（保存到 output 文件夹）
plt.figure(figsize=(12,4))
plt.plot(y_test.numpy(), label='真实值', alpha=0.7)
plt.plot(y_pred.numpy(), label='预测值', alpha=0.7)
plt.title('测试集：真实 vs 预测')
plt.xlabel('时间步')
plt.ylabel('归一化负载')
plt.legend()
plt.grid()
plt.savefig('algorithms/output/test_comparison.png')
plt.show()

# 11. 预测未来 10 步
model.eval()
with torch.no_grad():
    last_seq = data_scaled[-window:].reshape(1, window, 1)
    future_preds = []
    for _ in range(10):
        pred = model(torch.tensor(last_seq, dtype=torch.float32))
        future_preds.append(pred.item())
        last_seq = np.roll(last_seq, -1, axis=1)
        last_seq[0, -1, 0] = pred.item()

# 12. 反归一化
future_preds = np.array(future_preds).reshape(-1, 1)
future_preds = scaler.inverse_transform(future_preds)

# 13. 输出预测结果
print("\n🔮 未来 10 步负载预测：")
for i, val in enumerate(future_preds.flatten()):
    print(f"Step {i+1}: {val:.4f}")

# 14. 保存预测结果为 CSV（到 output 文件夹）
future_df = pd.DataFrame({
    'step': range(1, 11),
    'predicted_load': future_preds.flatten()
})
future_df.to_csv('algorithms/output/prediction_result.csv', index=False)
print("\n📁 预测结果已保存到 algorithms/output/prediction_result.csv")

# 15. 画完整预测图（保存到 output 文件夹）
plt.figure(figsize=(12,5))
plt.plot(df['timestamp'], df['load'], label='历史数据', alpha=0.7)
future_time = np.arange(len(df), len(df) + 10)
plt.plot(future_time, future_preds, 'r--', label='预测', marker='o')
plt.axvline(x=len(df), color='gray', linestyle=':', alpha=0.5)
plt.title('LSTM 负载预测')
plt.xlabel('时间')
plt.ylabel('负载')
plt.legend()
plt.grid()
plt.savefig('algorithms/output/lstm_prediction.png')
plt.show()

print("\n✅ 全部完成！文件保存在：")
print("   - algorithms/output/loss_curve.png")
print("   - algorithms/output/test_comparison.png")
print("   - algorithms/output/lstm_prediction.png")
print("   - algorithms/output/prediction_result.csv")