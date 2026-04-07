# WebSocket 长连接稳定性排查指南

## 📊 监控指标说明

| 指标 | 含义 | 正常范围 | 异常处理 |
|:---|:---|:---|:---|
| `disconnect_count` | 断开次数 | 稳定时应接近 0 | 检查网络、防火墙、客户端代码 |
| `reconnect_count` | 重连次数 | 稳定时应接近 1 | 检查客户端重连逻辑 |
| `current_connections` | 当前连接数 | 0 ~ N | 监控连接数异常波动 |
| `max_connections` | 最大并发连接数 | $\le$ 系统限制 | 监控资源使用情况 |
| `last_disconnect_time` | 最近断开时间 | - | 结合日志排查具体原因 |
| `last_reconnect_time` | 最近重连时间 | 断开后几秒内 | 检查重连间隔是否合理 |

---

## 📂 日志位置

### 1. 实时控制台日志
启动服务后，控制台会实时输出结构化日志：
```log
2025-01-01 12:00:00 - [WS] 连接建立 | 时间: 2025-01-01T12:00:00.123456 | 当前连接数: 1 | CPU: 12.3% | 内存: 45.6%
2025-01-01 12:00:01 - [WS] 连接断开 | 时间: 2025-01-01T12:00:01.789012 | 原因: normal | 当前连接数: 0 | CPU: 15.2% | 内存: 46.1%

### 2.日志文件
日志保存在：
`logs/ws.log`

**如何查看日志**：
# 实时追踪最新日志
tail -f logs/ws.log

# 检索所有断开记录并显示行号
grep -n "断开" logs/ws.log

# 查看最后 20 行日志
tail -n 20 logs/ws.log

**日志文件位置**：
- 相对路径：`logs/ws.log`（相对于项目根目录）

## 🔍 常见问题排查流程

### 1. 频繁断连（断开次数 > 10）
**现象**：日志中出现"频繁断连检测"警告
**排查步骤**：
1. 查看断开原因：`grep -n "原因:" logs/ws.log`
2. 检查后端状态：CPU/内存是否过高
3. 检查网络：客户端与服务器网络是否稳定
4. 检查防火墙：是否拦截了 WebSocket 连接

### 2. 连接数异常波动
**现象**：`current_connections` 大幅波动
**排查步骤**：
1. 查看连接建立/断开时间间隔
2. 检查客户端重连逻辑
3. 检查服务器资源（CPU/内存）是否达到瓶颈

### 3. 发送失败
**现象**：日志中出现"发送失败"错误
**排查步骤**：
1. 查看具体错误信息
2. 检查网络延迟
3. 检查消息大小是否超限
4. 检查客户端接收逻辑

## 🛠️ 健康检查端点

### 获取当前状态
python
import asyncio
from ws_manager import health_check

async def main():
    # 异步获取当前服务状态
    status = await health_check()
    print(status)

if __name__ == "__main__":
    asyncio.run(main())
### 返回结果示例
json
{
  "status": "healthy",
  "timestamp": "2025-01-01T12:00:00.123456",
  "connection_stats": {
    "disconnect_count": 5,
    "reconnect_count": 5,
    "current_connections": 3
  },
  "backend_status": {
    "cpu_percent": 12.3,
    "memory_percent": 45.6
  },
  "checks": {
    "cpu_ok": true,
    "memory_ok": true,
    "connections_ok": true
  }
}
### 健康状态判断标准
- **healthy**：CPU < 90% 且 内存 < 90% 且 连接数 ≥ 0
- **unhealthy**：上述任一条件不满足

## ✅ 交付物确认

- [x] WebSocket 连接/断开次数统计
- [x] 后端状态（CPU/内存）监控
- [x] 断连原因记录
- [x] 频繁断连预警
- [x] 日志文件记录
- [x] 健康检查端点
- [x] 排查指南文档