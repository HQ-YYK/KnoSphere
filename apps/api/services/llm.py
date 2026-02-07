import os
import json
import asyncio
from typing import AsyncGenerator, Optional
import httpx

class LLMService:
    """大语言模型服务类"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("ALIBABA_API_KEY")
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        
        # 支持多个模型提供商
        self.providers = {
            "deepseek": {
                "base_url": "https://api.deepseek.com/v1",
                "api_key_env": "DEEPSEEK_API_KEY"
            },
            "alibaba": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "api_key_env": "ALIBABA_API_KEY"
            }
        }
    
    def _detect_provider(self) -> str:
        """检测使用哪个提供商"""
        if os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek"
        elif os.getenv("ALIBABA_API_KEY"):
            return "alibaba"
        else:
            # 如果没有配置 API 密钥，返回测试模式
            return "test"
    
    async def stream_response(self, query: str, context: str, max_tokens: int = 2000) -> AsyncGenerator[str, None]:
        """
        流式获取 AI 响应
        
        参数：
        - query: 用户查询
        - context: 检索到的上下文
        - max_tokens: 最大令牌数
        
        返回：
        - 流式响应的字符串生成器
        """
        provider = self._detect_provider()
        
        if provider == "test":
            # 测试模式：返回模拟流式响应
            await self._stream_test_response(query, context)
            return
        
        # 构建 RAG 专用的 Prompt 模板
        system_prompt = f"""你是一个专业的知识库助手，基于以下已知信息回答问题。
        
已知信息：
{context}

请遵循以下规则：
1. 优先使用已知信息回答问题
2. 如果已知信息中没有相关内容，请明确告知用户你不知道
3. 保持回答简洁、准确、专业
4. 不要编造已知信息中没有的内容
5. 如果是技术问题，请提供具体的细节和步骤

现在请回答用户的问题："""
        
        if provider == "deepseek":
            await self._stream_deepseek_response(query, system_prompt, max_tokens)
        elif provider == "alibaba":
            await self._stream_alibaba_response(query, system_prompt, max_tokens)
    
    async def _stream_deepseek_response(self, query: str, system_prompt: str, max_tokens: int) -> AsyncGenerator[str, None]:
        """流式调用 DeepSeek API"""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            yield "❌ 错误：未配置 DeepSeek API Key"
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
    
    async def _stream_alibaba_response(self, query: str, system_prompt: str, max_tokens: int) -> AsyncGenerator[str, None]:
        """流式调用阿里通义千问 API"""
        api_key = os.getenv("ALIBABA_API_KEY")
        if not api_key:
            yield "❌ 错误：未配置阿里通义千问 API Key"
            return
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable"  # 阿里云的流式响应头
        }
        
        data = {
            "model": "qwen-max",  # 或者 qwen-plus, qwen-turbo
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
    
    async def _stream_test_response(self, query: str, context: str) -> AsyncGenerator[str, None]:
        """测试模式：返回模拟流式响应"""
        test_responses = [
            f"📚 基于您提供的知识库，我来回答：{query}\n\n",
            f"📖 检索到的相关文档有 {len(context.split('---'))} 篇。\n\n",
            "🤖 根据这些信息，我可以告诉您：\n\n",
            "这是一个模拟回答，用于测试流式响应功能。\n",
            "要获取真实回答，请在 .env 文件中配置 API 密钥。\n\n",
            "💡 建议：\n",
            "1. 前往 DeepSeek 或阿里百炼官网获取 API Key\n",
            "2. 在 apps/api/.env 文件中配置 DEEPSEEK_API_KEY 或 ALIBABA_API_KEY\n",
            "3. 重启服务器即可使用真实的 AI 对话功能！\n\n",
            "🚀 KnoSphere 期待为您提供更智能的服务！"
        ]
        
        for response in test_responses:
            for char in response:
                yield char
                await asyncio.sleep(0.02)  # 模拟打字效果
            yield "\n"
            await asyncio.sleep(0.1)

# 全局 LLM 服务实例
_llm_service = None

def get_llm_service() -> LLMService:
    """获取 LLM 服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service