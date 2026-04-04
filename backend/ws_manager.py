import asyncio
import psutil  # 新增：用于获取系统资源使用情况
from typing import Any, Dict, Optional, Set
from datetime import datetime #新增:
from fastapi import WebSocket
import logging  # 新增：用于日志记录

#新增：日志配置，创建日志和终端，将日志同时输出到文件和终端
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [WS] %(message)s',
    handlers=[
        logging.FileHandler('logs/ws.log'),  # 保存到文件
        logging.StreamHandler()  # 同时输出到终端
    ]
)
logger = logging.getLogger(__name__)


#新增：集中管理webSocket连接统计数据（21-53）
class WSStats:
    def __init__(self):
        self.disconnect_count = 0
        self.reconnect_count = 0
        self.last_disconnect_time = None
        self.last_reconnect_time = None
        self.max_connections = 0
        self.current_connections = 0
        
    def to_dict(self):
        """功能：将统计数据转换为字典，方便序列化"""
        return {
            "disconnect_count": self.disconnect_count,
            "reconnect_count": self.reconnect_count,
            "last_disconnect_time": self.last_disconnect_time,
            "last_reconnect_time": self.last_reconnect_time,
            "max_connections": self.max_connections,
            "current_connections": self.current_connections
        }
    
    def get_backend_status(self):
        """功能：获取后端系统状态（CPU、内存使用率）"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem_info = psutil.virtual_memory()
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": mem_info.percent,
            "memory_used_mb": mem_info.used / 1024 / 1024,
            "memory_total_mb": mem_info.total / 1024 / 1024
        }

# 创建全局统计实例
ws_stats = WSStats()

class WSManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

        # 新增：连接统计更新
        ws_stats.reconnect_count += 1
        ws_stats.last_reconnect_time = datetime.now().isoformat()
        ws_stats.current_connections = len(self._connections)
        ws_stats.max_connections = max(ws_stats.max_connections, ws_stats.current_connections)
        
        # 新增：获取后端状态
        backend_status = ws_stats.get_backend_status()
        
        # 新增：记录连接日志
        logger.info(f"连接建立 | "
                    f"时间: {ws_stats.last_reconnect_time} | "
                    f"当前连接数: {ws_stats.current_connections} | "
                    f"CPU: {backend_status['cpu_percent']:.1f}% | "
                    f"内存: {backend_status['memory_percent']:.1f}%")

        if self._loop is None:
            self._loop = asyncio.get_running_loop()

    def disconnect(self, websocket: WebSocket,reason: str = "normal") -> None:
        self._connections.discard(websocket)
        # 新增：断开统计更新
        ws_stats.disconnect_count += 1
        ws_stats.last_disconnect_time = datetime.now().isoformat()
        ws_stats.current_connections = len(self._connections)
            
        # 新增：获取断开时的后端状态
        backend_status = ws_stats.get_backend_status()
            
        # 新增：记录断开日志
        logger.info(f"连接断开 | "
                    f"时间: {ws_stats.last_disconnect_time} | "
                    f"原因: {reason} | "
                    f"当前连接数: {ws_stats.current_connections} | "
                    f"CPU: {backend_status['cpu_percent']:.1f}% | "
                    f"内存: {backend_status['memory_percent']:.1f}%")
            
            # 新增：频繁断连预警
        if ws_stats.disconnect_count > 10 and ws_stats.reconnect_count > 10:
            logger.warning(f"频繁断连检测: "
                            f"断开次数={ws_stats.disconnect_count}, "
                            f"重连次数={ws_stats.reconnect_count}")

   

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        if not self._connections:
            return
        dead: Set[WebSocket] = set()
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception as e:
                # 修改：记录具体的发送错误原因
                logger.error(f"发送失败: {str(e)}")
                # 修改：断开连接时记录原因
                #self.disconnect(ws, reason=f"send_error: {str(e)}")
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws, reason="dead_connection")

    def broadcast_threadsafe(self, payload: Dict[str, Any]) -> None:
        """可从非 async 线程调用的广播方法（例如 simulator 线程）。"""
        if self._loop is None:
            return
        # 新增：广播前的系统状态记录
        backend_status = ws_stats.get_backend_status()
        logger.debug(f"广播消息 | 连接数: {ws_stats.current_connections} | "
                    f"CPU: {backend_status['cpu_percent']:.1f}%")
        
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), self._loop)
    # ========== 新增：get_stats 方法 ==========
    # 功能：异步获取完整的连接统计信息
    async def get_stats(self) -> Dict[str, Any]:
        backend_status = ws_stats.get_backend_status()
        return {
            "connection_stats": ws_stats.to_dict(),
            "backend_status": backend_status,
            "active_connections": len(self._connections),
            "connection_ids": [id(conn) for conn in self._connections]
        }
    
    # ========== 新增：get_quick_stats 方法 ==========
    # 功能：同步获取简化的统计信息（性能更高）
    def get_quick_stats(self) -> Dict[str, Any]:
        """快速获取统计信息（同步方法）"""
        return {
            "disconnect_count": ws_stats.disconnect_count,
            "reconnect_count": ws_stats.reconnect_count,
            "current_connections": ws_stats.current_connections,
            "max_connections": ws_stats.max_connections,
            "last_event": {
                "disconnect": ws_stats.last_disconnect_time,
                "reconnect": ws_stats.last_reconnect_time
            }
        }

manager = WSManager()

# ========== 新增：health_check 函数 ==========
# 功能：WebSocket 服务健康检查端点
async def health_check() -> Dict[str, Any]:
    """WebSocket 服务健康检查"""
    stats = ws_stats.to_dict()
    backend_status = ws_stats.get_backend_status()
    
    # 健康检查标准
    is_healthy = (
        backend_status['cpu_percent'] < 90 and
        backend_status['memory_percent'] < 90 and
        ws_stats.current_connections >= 0
    )
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "connection_stats": stats,
        "backend_status": backend_status,
        "checks": {
            "cpu_ok": backend_status['cpu_percent'] < 90,
            "memory_ok": backend_status['memory_percent'] < 90,
            "connections_ok": ws_stats.current_connections >= 0
        }
    }


