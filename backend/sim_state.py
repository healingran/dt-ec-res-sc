"""
模拟器状态管理
文档要求的模式控制和状态统计
"""
import time
from typing import Dict, Any

class SimulatorState:
    """管理模拟器当前的状态"""

    def __init__(self):
        self.current_mode = "offpeak"
        self.current_intensity = 1
        self.last_mode_change = time.time()

        self.incident_count = 0
        self.last_incident_time = None

        self.total_tasks_generated = 0
        self.total_incidents_injected = 0

    def change_mode(self, mode: str, intensity: int = 1) -> Dict[str, Any]:
        """切换模拟器模式
        对应文档要求的 POST /api/v1/sim/mode
        """
        if mode not in ["offpeak", "peak", "incident"]:
            return {
                "success": False,
                "error": f"无效的模式: {mode}。支持的模式: offpeak, peak, incident"
            }
        
        if intensity < 1 or intensity > 10:
            return {
                "success": False,
                "error": "强度必须在1-10之间"
            }
        
        old_mode = self.current_mode
        self.current_mode = mode
        self.current_intensity = intensity
        self.last_mode_change = time.time()

        return {
            "success": True,
            "message": f"模式已经从 {old_mode} 切换到 {mode}，强度: {intensity}",  # ✅ 修正
            "data": {
                "old_mode": old_mode,
                "new_mode": mode,
                "intensity": intensity,
                "timestamp": time.time()
            }
        }
    
    def inject_incident(self) -> Dict[str, Any]:
        """注入事故任务
        对应文档要求的 POST /api/v1/sim/incident
        """
        self.incident_count += 1
        self.total_incidents_injected += 1
        self.last_incident_time = time.time()
        
        incident_task = {
            "id": f"incident_{self.incident_count}",
            "type": "incident",
            "cpu_need": 5.0,
            "priority": 10,
            "injected_at": time.time(),
            "status": "waiting"
        }
        
        return {
            "success": True,
            "message": f"事故任务已注入，累计注入 {self.incident_count} 次",
            "data": {
                "incident_task": incident_task,
                "total_incidents": self.incident_count,
                "injection_time": time.time()
            }
        }
    
    def get_state(self) -> Dict[str, Any]:
        """获取模拟器当前状态
        对应文档要求的 GET /api/v1/sim/state
        """
        return {
            "current_mode": self.current_mode,
            "current_intensity": self.current_intensity,
            "last_mode_change": self.last_mode_change,
            "uptime": round(time.time() - self.last_mode_change, 2),  # ✅ 添加四舍五入
            
            "incident_stats": {
                "total_injected": self.total_incidents_injected,
                "last_injection": self.last_incident_time,
                "incident_count": self.incident_count
            },
            
            "task_stats": {
                "total_generated": self.total_tasks_generated
            },
            
            "mode_config": {
                "task_arrival_rate": self._get_current_task_rate(),
                "description": self._get_mode_description()
            },
            
            "timestamp": time.time(),
            "system_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }
    
    def _get_current_task_rate(self) -> float:
        """根据当前模式和强度计算任务到达率"""
        if self.current_mode == "offpeak":
            return 0.1 * self.current_intensity
        elif self.current_mode == "peak":
            return 1.0 * self.current_intensity
        else:  # incident
            return 5.0 * self.current_intensity
    
    def _get_mode_description(self) -> str:
        """获取当前模式的描述"""
        descriptions = {
            "offpeak": "平峰模式，低负载运行",
            "peak": "高峰模式，高负载压力测试", 
            "incident": "事故模式，极端负载测试"
        }
        return descriptions.get(self.current_mode, "未知模式")

# 创建全局实例
simulator_state = SimulatorState()