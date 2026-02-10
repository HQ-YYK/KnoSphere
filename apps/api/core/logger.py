import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger

# ==================== 全局 logger 实例 ====================
# 在模块级别导出 logger，这样其他模块可以直接导入使用
# 例如：from core.logging import logger

# ==================== 日志配置函数 ====================

def setup_logging():
    """配置结构化日志"""
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 移除默认配置
    logger.remove()
    
    # 控制台输出：开发环境的美化版本
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level="INFO",
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # JSON 文件输出：生产环境的可解析格式
    logger.add(
        log_dir / "knosphere_api.json.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="10 MB",
        compression="zip",
        retention="30 days"
    )
    
    # 详细调试日志：包含工作流状态
    logger.add(
        log_dir / "knosphere_workflow.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[workflow]} | {message}",
        level="DEBUG",
        filter=lambda record: "workflow" in record["extra"],
        rotation="5 MB",
        retention="7 days"
    )
    
    # 错误日志单独存储
    logger.add(
        log_dir / "knosphere_errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}\n{exception}",
        level="ERROR",
        rotation="1 MB",
        retention="90 days"
    )
    
    logger.info(f"✅ 日志系统已初始化，日志目录: {log_dir.absolute()}")
    return logger

# ==================== 初始化日志系统 ====================
# 可选：在模块导入时自动初始化
# 如果不需要自动初始化，可以注释掉下面这行
setup_logging()

# ==================== 结构化日志函数 ====================

class WorkflowLogger:
    """工作流专用日志记录器"""
    
    @staticmethod
    def node_start(node_name: str, state: Optional[dict] = None):
        """记录节点开始"""
        logger.bind(workflow=node_name).info(
            "🚀 节点开始执行",
            extra={
                "node": node_name,
                "state": state if state else {},
                "timestamp": datetime.now().isoformat(),
                "event": "node_start"
            }
        )
    
    @staticmethod
    def node_complete(node_name: str, result: dict, duration: float):
        """记录节点完成"""
        logger.bind(workflow=node_name).info(
            "✅ 节点执行完成",
            extra={
                "node": node_name,
                "result": {k: v for k, v in result.items() if k != "documents"},
                "duration_seconds": round(duration, 3),
                "event": "node_complete"
            }
        )
    
    @staticmethod
    def node_error(node_name: str, error: Exception, state: Optional[dict] = None):
        """记录节点错误"""
        logger.bind(workflow=node_name).error(
            f"❌ 节点执行失败: {str(error)}",
            extra={
                "node": node_name,
                "error": str(error),
                "error_type": type(error).__name__,
                "state": state if state else {},
                "event": "node_error"
            }
        )
    
    @staticmethod
    def workflow_start(query: str, workflow_id: Optional[str] = None):
        """记录工作流开始"""
        workflow_id = workflow_id or f"wf_{datetime.now().timestamp()}"
        logger.bind(workflow="orchestrator").info(
            "🚀 工作流开始执行",
            extra={
                "workflow_id": workflow_id,
                "query": query[:200],
                "timestamp": datetime.now().isoformat(),
                "event": "workflow_start"
            }
        )
        return workflow_id
    
    @staticmethod
    def workflow_complete(workflow_id: str, final_state: dict, total_duration: float):
        """记录工作流完成"""
        logger.bind(workflow="orchestrator").info(
            "🎉 工作流执行完成",
            extra={
                "workflow_id": workflow_id,
                "final_node": final_state.get("current_node"),
                "total_duration_seconds": round(total_duration, 3),
                "documents_processed": len(final_state.get("documents", [])),
                "generation_length": len(final_state.get("generation", "")),
                "retry_count": final_state.get("retry_count", 0),
                "event": "workflow_complete"
            }
        )

    @staticmethod
    def workflow_error(workflow_id: str, error: str, total_duration: float = 0):
        """记录工作流错误"""
        logger.bind(workflow="orchestrator").error(
            f"💥 工作流执行失败: {error}",
            extra={
                "workflow_id": workflow_id,
                "error": error,
                "total_duration_seconds": round(total_duration, 3),
                "event": "workflow_error"
            }
        )
    
    
    @staticmethod
    def retrieval_log(query: str, documents: list, strategy: Optional[str] = None):
        """记录检索日志"""
        logger.bind(workflow="retrieval").debug(
            "🔍 文档检索完成",
            extra={
                "query": query[:200],
                "documents_count": len(documents),
                "strategy": strategy,
                "top_documents": [
                    {
                        "title": doc.get("title", "无标题")[:50],
                        "score": doc.get("score", 0),
                        "content_preview": doc.get("content", "")[:100]
                    }
                    for doc in documents[:3]
                ] if documents else [],
                "event": "retrieval_complete"
            }
        )
    
    @staticmethod
    def generation_log(query: str, context_size: int, response_length: int):
        """记录生成日志"""
        logger.bind(workflow="generation").debug(
            "🤖 AI 生成完成",
            extra={
                "query": query[:200],
                "context_size_chars": context_size,
                "response_length_chars": response_length,
                "token_estimate": int(response_length / 4),  # 粗略估算
                "event": "generation_complete"
            }
        )

# ==================== API 请求日志中间件 ====================

def log_api_request(request_data: dict, endpoint: str, user_agent: Optional[str] = None):
    """记录 API 请求"""
    logger.info(
        "📥 API 请求接收",
        extra={
            "endpoint": endpoint,
            "method": "POST",
            "user_agent": user_agent,
            "request_data": {
                "query": request_data.get("query", "")[:100],
                "top_k": request_data.get("top_k"),
                "final_k": request_data.get("final_k")
            },
            "timestamp": datetime.now().isoformat(),
            "event": "api_request"
        }
    )

def log_api_response(endpoint: str, status_code: int, response_time: float, error: Optional[str] = None):
    """记录 API 响应"""
    if error:
        logger.error(
            "📤 API 响应错误",
            extra={
                "endpoint": endpoint,
                "status_code": status_code,
                "response_time_seconds": round(response_time, 3),
                "error": error,
                "event": "api_response_error"
            }
        )
    else:
        logger.info(
            "📤 API 响应成功",
            extra={
                "endpoint": endpoint,
                "status_code": status_code,
                "response_time_seconds": round(response_time, 3),
                "event": "api_response_success"
            }
        )

# ==================== 性能监控 ====================

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {
            "retrieval_times": [],
            "generation_times": [],
            "workflow_times": [],
            "error_counts": {}
        }
    
    def record_metric(self, metric_type: str, value: float, **kwargs):
        """记录性能指标"""
        if metric_type in self.metrics:
            if isinstance(self.metrics[metric_type], list):
                self.metrics[metric_type].append(value)
                # 保持最近1000个记录
                if len(self.metrics[metric_type]) > 1000:
                    self.metrics[metric_type] = self.metrics[metric_type][-1000:]
        
        # 记录到日志
        logger.debug(
            f"📊 性能指标: {metric_type} = {value:.3f}s",
            extra={
                "metric_type": metric_type,
                "value": value,
                "unit": "seconds",
                **kwargs,
                "event": "performance_metric"
            }
        )
    
    def get_summary(self) -> dict:
        """获取性能摘要"""
        summary = {}
        
        for metric_type, values in self.metrics.items():
            if values and isinstance(values, list):
                summary[metric_type] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p95": sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0]
                }
        
        return summary

# 全局性能监控器
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

# ==================== 健康检查日志 ====================

def log_health_check():
    """记录健康检查"""
    import psutil
    import platform
    
    system_info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage("/").percent,
        "process_memory_mb": psutil.Process().memory_info().rss / 1024 / 1024
    }
    
    logger.info(
        "🏥 系统健康检查",
        extra={
            "system_info": system_info,
            "timestamp": datetime.now().isoformat(),
            "event": "health_check"
        }
    )
    
    return system_info

# ==================== 导出项 ====================
# 明确导出哪些内容可以被其他模块导入
__all__ = [
    'logger',           # loguru logger 实例
    'setup_logging',    # 日志配置函数
    'WorkflowLogger',   # 工作流日志类
    'log_api_request',  # API 请求日志函数
    'log_api_response', # API 响应日志函数
    'PerformanceMonitor', # 性能监控类
    'get_performance_monitor', # 获取性能监控器
    'log_health_check', # 健康检查函数
]