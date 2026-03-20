import pandas as pd
import numpy as np

# 设置随机种子，保证每次生成的数据一样
np.random.seed(42)

# 生成 1000 个时间点
time = np.arange(0, 1000)

# 模拟负载的三个组成部分
trend = 0.01 * time                     # 缓慢上升趋势
seasonal = 5 * np.sin(2 * np.pi * time / 48)  # 周期波动（模拟每天/每周规律）
noise = np.random.normal(0, 0.8, len(time))   # 随机噪声

# 合成最终负载
load = trend + seasonal + noise

# 构造 DataFrame
df = pd.DataFrame({
    'timestamp': time,
    'load': load
})

# 保存为 CSV 文件
df.to_csv('load_data.csv', index=False)

print("✅ load_data.csv 生成成功！")
print("前 5 行数据：")
print(df.head())