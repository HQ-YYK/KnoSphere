import os
import json
import asyncio
from typing import AsyncGenerator, Optional, List, Dict, Any
import httpx
from datetime import datetime

# 导入我们定义的协议
from .streaming_protocol import AgentMessage, MessageType
from services.langsmith_integration import trace_function

class LLMService:
    """大语言模型服务类 - 支持思考过程可视化"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("ALIBABA_API_KEY")
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
    
    @trace_function(name="LLM-Generation", run_type="llm")
    async def stream_response_with_thinking(
        self, 
        query: str, 
        context: str, 
        max_tokens: int = 2000,
        documents: List[Dict] = None,
        workflow_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        流式获取 AI 响应，包含思考过程
        
        参数:
        - query: 用户查询
        - context: 检索到的上下文
        - max_tokens: 最大令牌数
        - documents: 使用的文档列表
        - workflow_id: 工作流ID
        
        返回:
        - 流式响应的字符串生成器
        """
        # 1. 开始思考
        yield AgentMessage.thinking_start(query, workflow_id)
        await asyncio.sleep(0.1)
        
        # 2. 解析查询复杂度
        complexity = self._analyze_query_complexity(query)
        yield AgentMessage.status(f"分析查询复杂度: {complexity}", stage="analysis", progress=5)
        
        # 3. 如果有文档，展示文档信息
        if documents:
            doc_summary = self._summarize_documents(documents)
            yield AgentMessage.status(
                f"基于 {len(documents)} 篇文档生成回答",
                stage="context_analysis",
                progress=15,
                metadata={
                    "documents_count": len(documents),
                    "documents_summary": doc_summary
                }
            )
            await asyncio.sleep(0.2)
        
        # 4. 构建系统提示
        system_prompt = self._build_system_prompt(query, context, documents)
        yield AgentMessage.status("构建推理框架", stage="framework", progress=25)
        
        # 5. 开始生成
        yield AgentMessage.generation_start()
        await asyncio.sleep(0.1)
        
        # 6. 流式生成回答
        try:
            async for content_chunk in self._stream_generation(query, system_prompt, max_tokens):
                if content_chunk:
                    # 发送内容块
                    yield AgentMessage.chunk(content_chunk)
        except Exception as e:
            yield AgentMessage.error(f"生成失败: {str(e)}", "generation_error")
            raise
        
        # 7. 生成完成
        yield AgentMessage.generation_end()
        yield AgentMessage.complete(workflow_id)
    
    def _analyze_query_complexity(self, query: str) -> str:
        """分析查询复杂度"""
        query_len = len(query)
        if query_len > 100:
            return "高复杂度（需要深度推理）"
        elif query_len > 50:
            return "中复杂度（需要多步推理）"
        else:
            return "低复杂度（可以直接回答）"
    
    def _summarize_documents(self, documents: List[Dict]) -> List[Dict]:
        """总结文档信息"""
        summary = []
        for i, doc in enumerate(documents[:3]):  # 最多显示3个文档
            score = doc.get('score', 0)
            title = doc.get('title', '无标题')[:30]
            summary.append({
                "index": i + 1,
                "title": title,
                "score": f"{score:.1%}" if isinstance(score, (int, float)) else "N/A",
                "relevance": self._score_to_relevance(score)
            })
        return summary
    
    def _score_to_relevance(self, score: float) -> str:
        """分数转换为相关性描述"""
        if score > 0.8:
            return "高度相关"
        elif score > 0.6:
            return "相关"
        elif score > 0.4:
            return "一般相关"
        else:
            return "低相关"
    
    def _build_system_prompt(self, query: str, context: str, documents: List[Dict] = None) -> str:
        """构建系统提示"""
        prompt = f"""你是一个专业的知识库助手，基于以下已知信息回答问题。

用户问题: {query}

已知信息:
{context}

请遵循以下规则:
1. 优先使用已知信息回答问题
2. 如果已知信息中没有相关内容，请明确告知用户你不知道
3. 保持回答简洁、准确、专业
4. 不要编造已知信息中没有的内容

现在请回答用户的问题："""
        
        return prompt
    
    async def _stream_generation(self, query: str, system_prompt: str, max_tokens: int) -> AsyncGenerator[str, None]:
        """流式生成回答"""
        provider = self._detect_provider()
        
        if provider == "test":
            # 测试模式：返回模拟流式响应
            test_response = self._get_test_response(query, system_prompt)
            for i in range(0, len(test_response), 10):
                chunk = test_response[i:i+10]
                yield chunk
                await asyncio.sleep(0.05)
            return
        
        # 实际API调用
        if provider == "deepseek":
            async for chunk in self._stream_deepseek(query, system_prompt, max_tokens):
                yield chunk
        elif provider == "alibaba":
            async for chunk in self._stream_alibaba(query, system_prompt, max_tokens):
                yield chunk
    
    def _get_test_response(self, query: str, system_prompt: str) -> str:
        """获取测试响应"""
        return f"""基于您的问题"{query}"，我来为您分析：

根据检索到的文档，我可以为您提供以下信息：

1. 这是一个模拟回答，展示了思考过程可视化功能
2. 实际使用时，系统会基于您上传的文档生成准确的回答
3. 您可以上传技术文档、产品手册、政策文件等

思考过程：
- 已分析查询意图
- 已检索相关知识库
- 已进行语义匹配
- 正在生成结构化回答

如果您在 .env 文件中配置了真实的 API 密钥，系统将使用实际的 AI 模型为您生成回答。"""
    
    def _detect_provider(self) -> str:
        """检测使用哪个提供商"""
        if os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek"
        elif os.getenv("ALIBABA_API_KEY"):
            return "alibaba"
        else:
            return "test"
    
    async def _stream_deepseek(self, query: str, system_prompt: str, max_tokens: int) -> AsyncGenerator[str, None]:
        """流式调用 DeepSeek API"""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            yield "请配置 DeepSeek API Key"
            return
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST",
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if line.startswith("data: "):
                            data_line = line[6:]  # 去掉 "data: " 前缀
                            if data_line == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data_line)
                                if "choices" in chunk and chunk["choices"]:
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
                                
            except httpx.HTTPError as e:
                yield f"❌ API 调用失败: {str(e)}"
            except Exception as e:
                yield f"❌ 发生错误: {str(e)}"
    
    async def _stream_alibaba(self, query: str, system_prompt: str, max_tokens: int) -> AsyncGenerator[str, None]:
        """流式调用阿里通义千问 API"""
        api_key = os.getenv("ALIBABA_API_KEY")
        if not api_key:
            yield "请配置阿里通义千问 API Key"
            return
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable"
        }
        
        data = {
            "model": "qwen-max",
            "input": {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ]
            },
            "parameters": {
                "result_format": "message",
                "stream": True,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST",
                    "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                    headers=headers,
                    json=data
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if line.startswith("data: "):
                            data_line = line[6:]  # 去掉 "data: " 前缀
                            if data_line == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data_line)
                                if "output" in chunk and "choices" in chunk["output"]:
                                    for choice in chunk["output"]["choices"]:
                                        if "message" in choice and "content" in choice["message"]:
                                            content = choice["message"]["content"]
                                            if content:
                                                yield content
                            except json.JSONDecodeError:
                                continue
                                
            except httpx.HTTPError as e:
                yield f"❌ API 调用失败: {str(e)}"
            except Exception as e:
                yield f"❌ 发生错误: {str(e)}"

# 全局 LLM 服务实例
_llm_service = None

def get_llm_service() -> LLMService:
    """获取 LLM 服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service