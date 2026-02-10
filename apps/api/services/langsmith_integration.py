"""
LangSmith 集成服务 - 提供全链路追踪、成本监控和性能分析
2026 企业级 AI 可观测性平台集成
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import threading

# LangSmith 核心
from langsmith import Client, traceable, RunTree
from langsmith.schemas import FeedbackCreate, Run

# 导入现有服务
from core.logger import logger
from models import User, Document, Entity, GraphEdge

# 全局 LangSmith 客户端
_langsmith_client = None

def get_langsmith_client() -> Client:
    """获取 LangSmith 客户端单例"""
    global _langsmith_client
    if _langsmith_client is None:
        # 检查环境变量
        api_key = os.getenv("LANGCHAIN_API_KEY")
        endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
        
        if not api_key:
            logger.warning("⚠️ LangSmith API 密钥未配置，将使用离线模式")
            _langsmith_client = None
        else:
            try:
                _langsmith_client = Client(
                    api_url=endpoint,
                    api_key=api_key,
                    timeout=30.0  # 30秒超时
                )
                logger.info("✅ LangSmith 客户端初始化成功")
            except Exception as e:
                logger.error(f"❌ LangSmith 客户端初始化失败: {e}")
                _langsmith_client = None
    
    return _langsmith_client

class LangSmithMonitor:
    """LangSmith 监控管理器"""
    
    def __init__(self):
        self.client = get_langsmith_client()
        self.project_name = os.getenv("LANGCHAIN_PROJECT", "KnoSphere-Production-2026")
        self.environment = os.getenv("LANGCHAIN_ENVIRONMENT", "development")
        
        # 成本跟踪
        self.cost_tracker = CostTracker()
        
        # 性能监控
        self.performance_monitor = PerformanceMonitor()
        
        # 评估器
        self.evaluator = AutoEvaluator()
        
        # 用户反馈收集
        self.feedback_collector = FeedbackCollector()
    
    def is_enabled(self) -> bool:
        """检查 LangSmith 是否启用"""
        return self.client is not None and os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    
    def start_trace(self, 
                   name: str, 
                   inputs: Dict[str, Any],
                   run_type: str = "chain",
                   metadata: Optional[Dict[str, Any]] = None,
                   tags: Optional[List[str]] = None) -> Optional[RunTree]:
        """开始一个新的追踪"""
        if not self.is_enabled():
            return None
        
        try:
            run_tree = RunTree(
                name=name,
                run_type=run_type,
                inputs=inputs,
                project_name=self.project_name,
                metadata=metadata or {},
                tags=tags or [],
                extra={"environment": self.environment}
            )
            
            # 启动后台线程发送追踪（避免阻塞主流程）
            threading.Thread(
                target=self._submit_trace,
                args=(run_tree,),
                daemon=True
            ).start()
            
            return run_tree
            
        except Exception as e:
            logger.error(f"❌ 启动追踪失败: {e}")
            return None
    
    def _submit_trace(self, run_tree: RunTree):
        """提交追踪到 LangSmith"""
        try:
            self.client.create_run_tree(run_tree)
        except Exception as e:
            logger.error(f"❌ 提交追踪失败: {e}")
    
    def end_trace(self, 
                  run_tree: Optional[RunTree], 
                  outputs: Dict[str, Any],
                  error: Optional[str] = None):
        """结束追踪"""
        if not run_tree or not self.is_enabled():
            return
        
        try:
            run_tree.outputs = outputs
            run_tree.end_time = datetime.utcnow()
            
            if error:
                run_tree.error = error
            
            # 提交结束的追踪
            self.client.update_run_tree(run_tree)
            
            # 记录性能指标
            if not error:
                duration = (run_tree.end_time - run_tree.start_time).total_seconds() * 1000
                self.performance_monitor.record_latency(run_tree.name, duration)
            
        except Exception as e:
            logger.error(f"❌ 结束追踪失败: {e}")
    
    def log_feedback(self,
                    run_id: str,
                    score: float,
                    key: str = "user_feedback",
                    comment: Optional[str] = None,
                    source_info: Optional[Dict[str, Any]] = None):
        """记录用户反馈"""
        if not self.is_enabled():
            return
        
        try:
            feedback = FeedbackCreate(
                key=key,
                score=score,
                comment=comment,
                run_id=run_id,
                source_info=source_info or {}
            )
            
            self.client.create_feedback(feedback)
            logger.info(f"✅ 用户反馈已记录: run_id={run_id}, score={score}")
            
        except Exception as e:
            logger.error(f"❌ 记录反馈失败: {e}")
    
    def record_cost(self,
                   provider: str,
                   model: str,
                   input_tokens: int,
                   output_tokens: int,
                   user_id: Optional[int] = None):
        """记录 Token 消耗成本"""
        self.cost_tracker.record_usage(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            user_id=user_id
        )
    
    def get_performance_report(self, 
                             time_range_hours: int = 24) -> Dict[str, Any]:
        """获取性能报告"""
        return self.performance_monitor.generate_report(time_range_hours)
    
    def get_cost_report(self,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """获取成本报告"""
        return self.cost_tracker.generate_report(start_date, end_date)
    
    def evaluate_response(self,
                         query: str,
                         context: str,
                         response: str,
                         run_id: Optional[str] = None) -> Dict[str, Any]:
        """自动评估响应质量"""
        return self.evaluator.evaluate(query, context, response, run_id)

class CostTracker:
    """Token 成本跟踪器"""
    
    def __init__(self):
        # 模型成本配置（美元/1000 tokens）
        self.model_costs = {
            "deepseek-chat": {
                "input": float(os.getenv("DEEPSEEK_COST_PER_1K_INPUT", 0.00014)),
                "output": float(os.getenv("DEEPSEEK_COST_PER_1K_OUTPUT", 0.00028))
            },
            "qwen-max": {
                "input": float(os.getenv("ALIBABA_COST_PER_1K_INPUT", 0.0004)),
                "output": float(os.getenv("ALIBABA_COST_PER_1K_OUTPUT", 0.0008))
            },
            "gpt-4o-mini": {
                "input": 0.00015,
                "output": 0.0006
            },
            "gpt-3.5-turbo": {
                "input": 0.0005,
                "output": 0.0015
            }
        }
        
        # 成本存储（内存缓存，生产环境应使用 Redis 或数据库）
        self.usage_records = []
    
    def record_usage(self,
                    provider: str,
                    model: str,
                    input_tokens: int,
                    output_tokens: int,
                    user_id: Optional[int] = None):
        """记录 Token 使用情况"""
        try:
            # 计算成本
            cost_config = self.model_costs.get(model, self.model_costs.get("deepseek-chat"))
            if not cost_config:
                logger.warning(f"未知模型成本配置: {model}")
                return
            
            input_cost = (input_tokens / 1000) * cost_config["input"]
            output_cost = (output_tokens / 1000) * cost_config["output"]
            total_cost = input_cost + output_cost
            
            # 记录使用情况
            record = {
                "timestamp": datetime.utcnow(),
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": total_cost,
                "user_id": user_id
            }
            
            self.usage_records.append(record)
            
            # 记录日志
            logger.info(f"💰 Token 使用记录: {model}, "
                       f"输入: {input_tokens}, 输出: {output_tokens}, "
                       f"成本: ${total_cost:.6f}")
            
            # 定期清理旧记录（保留最近7天）
            self._cleanup_old_records()
            
        except Exception as e:
            logger.error(f"❌ 记录 Token 使用失败: {e}")
    
    def _cleanup_old_records(self):
        """清理7天前的记录"""
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        self.usage_records = [
            r for r in self.usage_records 
            if r["timestamp"] > cutoff_time
        ]
    
    def generate_report(self,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """生成成本报告"""
        try:
            # 设置时间范围
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=7)
            if not end_date:
                end_date = datetime.utcnow()
            
            # 筛选记录
            filtered_records = [
                r for r in self.usage_records
                if start_date <= r["timestamp"] <= end_date
            ]
            
            # 按用户统计
            user_stats = {}
            for record in filtered_records:
                user_id = record.get("user_id", "unknown")
                if user_id not in user_stats:
                    user_stats[user_id] = {
                        "total_tokens": 0,
                        "total_cost": 0.0,
                        "requests": 0
                    }
                
                user_stats[user_id]["total_tokens"] += record["input_tokens"] + record["output_tokens"]
                user_stats[user_id]["total_cost"] += record["total_cost"]
                user_stats[user_id]["requests"] += 1
            
            # 按模型统计
            model_stats = {}
            for record in filtered_records:
                model = record["model"]
                if model not in model_stats:
                    model_stats[model] = {
                        "total_tokens": 0,
                        "total_cost": 0.0,
                        "requests": 0
                    }
                
                model_stats[model]["total_tokens"] += record["input_tokens"] + record["output_tokens"]
                model_stats[model]["total_cost"] += record["total_cost"]
                model_stats[model]["requests"] += 1
            
            # 计算总计
            total_tokens = sum(r["input_tokens"] + r["output_tokens"] for r in filtered_records)
            total_cost = sum(r["total_cost"] for r in filtered_records)
            total_requests = len(filtered_records)
            
            return {
                "time_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "summary": {
                    "total_requests": total_requests,
                    "total_tokens": total_tokens,
                    "total_cost": total_cost,
                    "avg_cost_per_request": total_cost / total_requests if total_requests > 0 else 0
                },
                "by_user": user_stats,
                "by_model": model_stats,
                "records_count": len(filtered_records)
            }
            
        except Exception as e:
            logger.error(f"❌ 生成成本报告失败: {e}")
            return {"error": str(e)}

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        # 性能指标存储
        self.metrics = {
            "latency": {},  # 各阶段延迟
            "error_rate": {},  # 各阶段错误率
            "token_usage": {},  # Token 使用情况
            "ttft": []  # 首字延迟
        }
        
        # 阈值配置
        self.ttft_threshold = int(os.getenv("PERFORMANCE_TTFT_THRESHOLD_MS", 2000))
        self.token_limit = int(os.getenv("PERFORMANCE_TOKEN_LIMIT", 4000))
        self.error_rate_threshold = float(os.getenv("PERFORMANCE_ERROR_RATE_THRESHOLD", 0.05))
    
    def record_latency(self, operation: str, latency_ms: float):
        """记录操作延迟"""
        if operation not in self.metrics["latency"]:
            self.metrics["latency"][operation] = []
        
        self.metrics["latency"][operation].append({
            "timestamp": datetime.utcnow(),
            "latency_ms": latency_ms
        })
        
        # 保留最近1000条记录
        if len(self.metrics["latency"][operation]) > 1000:
            self.metrics["latency"][operation] = self.metrics["latency"][operation][-1000:]
    
    def record_ttft(self, ttft_ms: float):
        """记录首字延迟"""
        self.metrics["ttft"].append({
            "timestamp": datetime.utcnow(),
            "ttft_ms": ttft_ms
        })
        
        # 检查是否超过阈值
        if ttft_ms > self.ttft_threshold:
            logger.warning(f"⚠️ TTFT 超过阈值: {ttft_ms}ms > {self.ttft_threshold}ms")
        
        # 保留最近1000条记录
        if len(self.metrics["ttft"]) > 1000:
            self.metrics["ttft"] = self.metrics["ttft"][-1000:]
    
    def record_error(self, operation: str, error_type: str):
        """记录错误"""
        if operation not in self.metrics["error_rate"]:
            self.metrics["error_rate"][operation] = {"total": 0, "errors": 0}
        
        self.metrics["error_rate"][operation]["total"] += 1
        self.metrics["error_rate"][operation]["errors"] += 1
    
    def record_success(self, operation: str):
        """记录成功"""
        if operation not in self.metrics["error_rate"]:
            self.metrics["error_rate"][operation] = {"total": 0, "errors": 0}
        
        self.metrics["error_rate"][operation]["total"] += 1
    
    def check_health(self) -> Dict[str, Any]:
        """检查系统健康状况"""
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 检查 TTFT
        if self.metrics["ttft"]:
            avg_ttft = sum(r["ttft_ms"] for r in self.metrics["ttft"]) / len(self.metrics["ttft"])
            health_status["checks"]["ttft"] = {
                "status": "healthy" if avg_ttft <= self.ttft_threshold else "degraded",
                "value": avg_ttft,
                "threshold": self.ttft_threshold
            }
        
        # 检查错误率
        for operation, stats in self.metrics["error_rate"].items():
            if stats["total"] > 0:
                error_rate = stats["errors"] / stats["total"]
                health_status["checks"][f"error_rate_{operation}"] = {
                    "status": "healthy" if error_rate <= self.error_rate_threshold else "critical",
                    "value": error_rate,
                    "threshold": self.error_rate_threshold
                }
        
        # 更新总体状态
        if any(check["status"] == "critical" for check in health_status["checks"].values()):
            health_status["status"] = "critical"
        elif any(check["status"] == "degraded" for check in health_status["checks"].values()):
            health_status["status"] = "degraded"
        
        return health_status
    
    def generate_report(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """生成性能报告"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
            
            # 筛选 TTFT 数据
            ttft_records = [r for r in self.metrics["ttft"] if r["timestamp"] > cutoff_time]
            
            # 计算统计数据
            report = {
                "time_range_hours": time_range_hours,
                "timestamp": datetime.utcnow().isoformat(),
                "ttft": {
                    "count": len(ttft_records),
                    "avg_ms": sum(r["ttft_ms"] for r in ttft_records) / len(ttft_records) if ttft_records else 0,
                    "p95_ms": self._calculate_percentile([r["ttft_ms"] for r in ttft_records], 95) if ttft_records else 0,
                    "p99_ms": self._calculate_percentile([r["ttft_ms"] for r in ttft_records], 99) if ttft_records else 0,
                    "max_ms": max(r["ttft_ms"] for r in ttft_records) if ttft_records else 0,
                    "threshold_exceeded": sum(1 for r in ttft_records if r["ttft_ms"] > self.ttft_threshold)
                },
                "latency_by_operation": {},
                "error_rates": {},
                "health": self.check_health()
            }
            
            # 各操作延迟统计
            for operation, records in self.metrics["latency"].items():
                recent_records = [r for r in records if r["timestamp"] > cutoff_time]
                if recent_records:
                    latencies = [r["latency_ms"] for r in recent_records]
                    report["latency_by_operation"][operation] = {
                        "count": len(recent_records),
                        "avg_ms": sum(latencies) / len(latencies),
                        "p95_ms": self._calculate_percentile(latencies, 95),
                        "p99_ms": self._calculate_percentile(latencies, 99)
                    }
            
            # 错误率统计
            for operation, stats in self.metrics["error_rate"].items():
                # 这里简化处理，实际应该有时间筛选
                if stats["total"] > 0:
                    report["error_rates"][operation] = {
                        "total_requests": stats["total"],
                        "errors": stats["errors"],
                        "error_rate": stats["errors"] / stats["total"]
                    }
            
            return report
            
        except Exception as e:
            logger.error(f"❌ 生成性能报告失败: {e}")
            return {"error": str(e)}
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index % 1)

class AutoEvaluator:
    """自动评估器"""
    
    def __init__(self):
        self.evaluation_model = os.getenv("EVALUATION_MODEL", "gpt-4o-mini")
        self.evaluation_provider = os.getenv("EVALUATION_MODEL_PROVIDER", "openai")
        
        # 初始化评估模型
        self.eval_llm = self._init_evaluation_model()
    
    def _init_evaluation_model(self):
        """初始化评估模型"""
        try:
            if self.evaluation_provider == "openai":
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=self.evaluation_model,
                    temperature=0.0,  # 评估需要确定性
                    max_tokens=500
                )
            elif self.evaluation_provider == "alibaba":
                from langchain_community.chat_models import ChatTongyi
                return ChatTongyi(
                    model=self.evaluation_model,
                    temperature=0.0,
                    max_tokens=500
                )
            else:
                logger.warning(f"未知评估模型提供商: {self.evaluation_provider}")
                return None
        except Exception as e:
            logger.error(f"❌ 初始化评估模型失败: {e}")
            return None
    
    def evaluate(self,
                query: str,
                context: str,
                response: str,
                run_id: Optional[str] = None) -> Dict[str, Any]:
        """评估响应质量"""
        if not self.eval_llm:
            return {"error": "评估模型未初始化"}
        
        try:
            # 构建评估提示
            system_prompt = """你是一个专业的 AI 响应质量评估专家。
请根据以下标准评估回答质量：

1. **相关性 (Relevance)**: 回答是否直接相关于用户问题 (0-10分)
2. **准确性 (Accuracy)**: 回答是否基于提供的上下文，是否包含幻觉 (0-10分)
3. **完整性 (Completeness)**: 回答是否完整地解决了用户问题 (0-10分)
4. **清晰度 (Clarity)**: 回答是否清晰、易懂 (0-10分)
5. **安全性 (Safety)**: 回答是否安全、无有害内容 (0-10分)

请输出 JSON 格式的评估结果：
{
  "scores": {
    "relevance": 0-10,
    "accuracy": 0-10,
    "completeness": 0-10,
    "clarity": 0-10,
    "safety": 0-10
  },
  "average_score": 0-10,
  "has_hallucination": true/false,
  "reason": "评估理由"
}"""

            evaluation_prompt = f"""
用户问题: {query}

检索到的上下文:
{context[:2000]}

AI 回答:
{response[:2000]}

请评估回答质量:
"""
            
            # 调用评估模型
            eval_response = self.eval_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": evaluation_prompt}
            ])
            
            # 解析响应
            import json
            eval_result = json.loads(eval_response.content)
            
            # 记录评估结果到 LangSmith
            if run_id:
                monitor = get_langsmith_monitor()
                if monitor.is_enabled():
                    monitor.log_feedback(
                        run_id=run_id,
                        score=eval_result["scores"]["accuracy"] / 10.0,  # 归一化到0-1
                        key="auto_evaluation",
                        comment=f"自动评估: {eval_result['reason'][:200]}"
                    )
            
            return eval_result
            
        except Exception as e:
            logger.error(f"❌ 自动评估失败: {e}")
            return {"error": str(e)}

class FeedbackCollector:
    """用户反馈收集器"""
    
    def __init__(self):
        self.client = get_langsmith_client()
    
    def collect_feedback(self,
                        feedback_data: Dict[str, Any]) -> bool:
        """收集用户反馈"""
        try:
            run_id = feedback_data.get("run_id")
            if not run_id:
                logger.warning("缺少 run_id，无法关联反馈")
                return False
            
            # 解析反馈数据
            score = feedback_data.get("score", 0.5)
            comment = feedback_data.get("comment", "")
            feedback_type = feedback_data.get("type", "thumbs")
            user_id = feedback_data.get("user_id")
            
            # 创建反馈
            feedback_key = f"user_{feedback_type}"
            
            if self.client:
                self.client.create_feedback(
                    run_id=run_id,
                    key=feedback_key,
                    score=score,
                    comment=comment,
                    source_info={"user_id": user_id} if user_id else {}
                )
            
            logger.info(f"✅ 用户反馈已收集: run_id={run_id}, score={score}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 收集用户反馈失败: {e}")
            return False
    
    def get_feedback_summary(self,
                           run_id: str) -> Dict[str, Any]:
        """获取反馈摘要"""
        try:
            if not self.client:
                return {"error": "LangSmith 客户端未初始化"}
            
            feedbacks = self.client.list_feedback(run_ids=[run_id])
            
            summary = {
                "run_id": run_id,
                "total_feedback": len(feedbacks),
                "average_score": 0.0,
                "feedback_by_type": {}
            }
            
            if feedbacks:
                total_score = 0.0
                score_count = 0
                
                for feedback in feedbacks:
                    feedback_type = feedback.key
                    score = feedback.score
                    
                    if feedback_type not in summary["feedback_by_type"]:
                        summary["feedback_by_type"][feedback_type] = {
                            "count": 0,
                            "average_score": 0.0,
                            "comments": []
                        }
                    
                    summary["feedback_by_type"][feedback_type]["count"] += 1
                    
                    if score is not None:
                        total_score += score
                        score_count += 1
                        summary["feedback_by_type"][feedback_type]["average_score"] = (
                            (summary["feedback_by_type"][feedback_type]["average_score"] * 
                             (summary["feedback_by_type"][feedback_type]["count"] - 1) + score) /
                            summary["feedback_by_type"][feedback_type]["count"]
                        )
                    
                    if feedback.comment:
                        summary["feedback_by_type"][feedback_type]["comments"].append(feedback.comment)
                
                if score_count > 0:
                    summary["average_score"] = total_score / score_count
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ 获取反馈摘要失败: {e}")
            return {"error": str(e)}

# 装饰器函数
def trace_function(name: str = None, run_type: str = "tool"):
    """追踪装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitor = get_langsmith_monitor()
            
            # 构建输入
            inputs = {
                "args": str(args),
                "kwargs": kwargs
            }
            
            # 开始追踪
            run_tree = monitor.start_trace(
                name=name or func.__name__,
                inputs=inputs,
                run_type=run_type,
                metadata={
                    "function": func.__name__,
                    "module": func.__module__
                }
            )
            
            try:
                # 执行函数
                start_time = time.time()
                result = await func(*args, **kwargs)
                end_time = time.time()
                
                # 记录性能
                duration_ms = (end_time - start_time) * 1000
                monitor.performance_monitor.record_latency(func.__name__, duration_ms)
                
                # 结束追踪
                monitor.end_trace(
                    run_tree=run_tree,
                    outputs={"result": result},
                    error=None
                )
                
                return result
                
            except Exception as e:
                # 记录错误
                monitor.end_trace(
                    run_tree=run_tree,
                    outputs={},
                    error=str(e)
                )
                monitor.performance_monitor.record_error(func.__name__, type(e).__name__)
                raise e
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitor = get_langsmith_monitor()
            
            # 构建输入
            inputs = {
                "args": str(args),
                "kwargs": kwargs
            }
            
            # 开始追踪
            run_tree = monitor.start_trace(
                name=name or func.__name__,
                inputs=inputs,
                run_type=run_type,
                metadata={
                    "function": func.__name__,
                    "module": func.__module__
                }
            )
            
            try:
                # 执行函数
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                # 记录性能
                duration_ms = (end_time - start_time) * 1000
                monitor.performance_monitor.record_latency(func.__name__, duration_ms)
                
                # 结束追踪
                monitor.end_trace(
                    run_tree=run_tree,
                    outputs={"result": result},
                    error=None
                )
                
                return result
                
            except Exception as e:
                # 记录错误
                monitor.end_trace(
                    run_tree=run_tree,
                    outputs={},
                    error=str(e)
                )
                monitor.performance_monitor.record_error(func.__name__, type(e).__name__)
                raise e
        
        # 根据函数类型返回包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# 全局监控器实例
_langsmith_monitor = None

def get_langsmith_monitor() -> LangSmithMonitor:
    """获取 LangSmith 监控器单例"""
    global _langsmith_monitor
    if _langsmith_monitor is None:
        _langsmith_monitor = LangSmithMonitor()
    return _langsmith_monitor