# algorithms/train_model.py
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

class LSTMPredictor(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
    
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

if __name__ == "__main__":
    os.makedirs("algorithms/model_save", exist_ok=True)
    
    print("🚀 训练更好的模型...")
    
    # 生成更真实的数据
    np.random.seed(42)
    time = np.arange(0, 3000)
    
    # 更真实的负载模式
    trend = 0.003 * time
    seasonal = 12 * np.sin(2 * np.pi * time / 48) + 8 * np.sin(2 * np.pi * time / 168)
    noise = np.random.normal(0, 2, len(time))
    
    load = 50 + trend + seasonal + noise
    load = np.clip(load, 20, 95)
    
    df = pd.DataFrame({'timestamp': time, 'load': load})
    df.to_csv('algorithms/data/load_data.csv', index=False)
    print(f"✅ 生成 {len(df)} 条数据，范围: {load.min():.1f}% - {load.max():.1f}%")
    
    # 归一化
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(load.reshape(-1, 1))
    joblib.dump(scaler, 'algorithms/model_save/scaler.joblib')
    print("✅ Scaler 已保存")
    
    # 构造数据
    window = 30
    X, y = [], []
    for i in range(len(data_scaled) - window):
        X.append(data_scaled[i:i+window])
        y.append(data_scaled[i+window])
    
    X = torch.tensor(np.array(X), dtype=torch.float32)
    y = torch.tensor(np.array(y), dtype=torch.float32)
    print(f"✅ 训练数据: {len(X)} 条")
    
    # 训练
    model = LSTMPredictor()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()
    
    print("\n开始训练（100轮）...")
    best_loss = float('inf')
    
    for epoch in range(100):
        model.train()
        optimizer.zero_grad()
        output = model(X)
        loss = criterion(output, y)
        loss.backward()
        optimizer.step()
        
        if loss < best_loss:
            best_loss = loss
            torch.save(model.state_dict(), 'algorithms/model_save/lstm_model.pth')
        
        if (epoch + 1) % 20 == 0:
            print(f"Epoch {epoch+1}/100, Loss: {loss.item():.6f}")
    
    print(f"\n✅ 训练完成！最佳损失: {best_loss:.6f}")
    
    # 测试预测
    model.eval()
    with torch.no_grad():
        last_seq = data_scaled[-window:].reshape(1, window, 1)
        preds = []
        for _ in range(10):
            pred = model(torch.tensor(last_seq, dtype=torch.float32))
            preds.append(pred.item())
            last_seq = np.roll(last_seq, -1, axis=1)
            last_seq[0, -1, 0] = pred.item()
        
        preds_real = scaler.inverse_transform(np.array(preds).reshape(-1, 1))
        print(f"\n真实值 (最后10个): {load[-10:].flatten()}")
        print(f"预测值 (未来10步): {preds_real.flatten()}")
    
    print("\n✅ 模型已保存到 algorithms/model_save/lstm_model.pth")