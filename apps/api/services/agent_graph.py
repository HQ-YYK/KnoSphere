from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from services.tools import get_tool_manager
from langgraph.prebuilt import ToolNode
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from services.search import secure_hybrid_search
from services.llm import get_llm_service
from sqlmodel import Session
from datetime import datetime
import json
from core.auth import get_current_user

# ==================== 状态定义 ====================

class AgentState(TypedDict):
    """代理状态 - 包含完整的思考过程"""
    # 对话历史
    messages: Annotated[List[BaseMessage], add_messages]
    # 检索到的文档
    documents: List[dict]
    # 最终生成内容
    generation: str
    # 当前执行节点
    current_node: str
    # 节点执行历史
    node_history: List[dict]
    # 执行开始时间
    start_time: datetime
    # 错误信息
    error: Optional[str]
    # 重试次数
    retry_count: int
    # 是否相关
    is_relevant: Optional[bool]
    # 添加工具相关字段
    tool_calls: List[dict]  # 工具调用记录
    tool_results: List[dict]  # 工具执行结果
    should_use_tools: bool  # 是否应该使用工具

# ==================== 模型定义 ====================

class DocumentRelevance(BaseModel):
    """文档相关性评估模型"""
    binary_score: str = Field(
        description="检索到的文档是否与问题相关? 返回 'yes' 或 'no'",
        examples=["yes", "no"]
    )
    confidence: float = Field(
        description="评估置信度 (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    reason: str = Field(
        description="评估理由",
        examples=["文档内容直接回答了用户问题", "文档内容与问题无关"]
    )

class QueryRewrite(BaseModel):
    """查询重写模型"""
    rewritten_query: str = Field(
        description="重写后的查询语句",
        examples=["人工智能的基本原理和应用", "机器学习的核心算法有哪些"]
    )
    improvement: str = Field(
        description="重写改进点",
        examples=["更具体", "更专业", "更清晰"]
    )

# ==================== 节点实现 ====================

async def start_node(state: AgentState) -> dict:
    """开始节点 - 初始化状态"""
    return {
        "current_node": "start",
        "start_time": datetime.now(),
        "node_history": [{
            "node": "start",
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }]
    }

async def retrieve_node(state: AgentState, config: dict) -> dict:
    """检索节点 - 智能检索文档"""
    try:
        db = config.get("db")
        if not db:
            raise ValueError("数据库会话未提供")
        
        user_id = config.get("user_id", "")
        
        # 获取最后一条用户消息
        messages = state.get("messages", [])
        if not messages:
            return {"error": "没有找到用户消息"}
        
        last_message = messages[-1]
        query = getattr(last_message, 'content', str(last_message))
        
        # 根据查询复杂度动态调整检索参数
        query_len = len(query)
        top_k = 15 if query_len > 30 else 10
        final_k = 5 if query_len > 30 else 3
        
        # 执行混合检索
        print(f"🔍 执行智能检索: {query[:50]}...")
        
        documents = await secure_hybrid_search(query, db, user_id, top_k=top_k, final_k=final_k)
        
        return {
            "documents": documents,
            "current_node": "retrieve",
            "node_history": state.get("node_history", []) + [{
                "node": "retrieve",
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "documents_count": len(documents),
                "query": query[:100]
            }]
        }
    except Exception as e:
        print(f"❌ 检索节点失败: {e}")
        return {
            "error": f"检索失败: {str(e)}",
            "current_node": "retrieve",
            "node_history": state.get("node_history", []) + [{
                "node": "retrieve",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }]
        }

async def grade_node(state: AgentState, config: dict) -> dict:
    """评估节点 - 评估文档相关性"""
    try:
        documents = state.get("documents", [])
        messages = state.get("messages", [])
        
        if not documents:
            # 如果没有检索到文档，直接标记为不相关
            return {
                "is_relevant": False,
                "current_node": "grade",
                "node_history": state.get("node_history", []) + [{
                    "node": "grade",
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "assessment": "no_documents",
                    "is_relevant": False
                }]
            }
        
        # 获取用户查询
        last_message = messages[-1]
        query = getattr(last_message, 'content', str(last_message))
        
        # 准备文档内容用于评估
        doc_contents = [doc.get("content", "")[:500] for doc in documents[:3]]
        context = "\n\n".join([f"文档{i+1}: {content}" for i, content in enumerate(doc_contents)])
        
        # 使用 LLM 评估相关性
        llm_service = get_llm_service()
        
        # 构建评估提示
        system_prompt = f"""你是一个文档相关性评估专家。请评估以下文档是否能够回答用户的问题。

用户问题: {query}

检索到的文档:
{context}

请严格按照以下格式输出评估结果:
1. binary_score: 如果文档内容能够回答用户问题，返回'yes'，否则返回'no'
2. confidence: 评估置信度 (0.0-1.0)
3. reason: 简要说明评估理由

注意: 即使文档内容不完全匹配，但如果是相关主题，也应考虑为相关。"""

        # 收集评估响应
        full_response = ""
        async for chunk in llm_service.stream_response(system_prompt, "请评估文档相关性"):
            full_response += chunk
        
        # 解析评估结果 (简化解析，实际应用中应使用结构化输出)
        is_relevant = "yes" in full_response.lower() or "相关" in full_response
        
        return {
            "is_relevant": is_relevant,
            "current_node": "grade",
            "node_history": state.get("node_history", []) + [{
                "node": "grade",
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "assessment": full_response[:200],
                "is_relevant": is_relevant,
                "confidence": 0.8 if is_relevant else 0.3
            }]
        }
    except Exception as e:
        print(f"❌ 评估节点失败: {e}")
        return {
            "error": f"评估失败: {str(e)}",
            "current_node": "grade",
            "node_history": state.get("node_history", []) + [{
                "node": "grade",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }]
        }

async def rewrite_node(state: AgentState, config: dict) -> dict:
    """重写节点 - 优化查询语句"""
    try:
        messages = state.get("messages", [])
        last_message = messages[-1]
        original_query = getattr(last_message, 'content', str(last_message))
        
        # 使用 LLM 重写查询
        llm_service = get_llm_service()
        
        system_prompt = f"""你是一个查询优化专家。请重写以下查询，使其更适合文档检索。

原始查询: {original_query}

重写要求:
1. 保持原意，但表达更清晰
2. 如果是模糊查询，尝试使其更具体
3. 如果是专业问题，使用更准确的术语
4. 长度控制在20-50字之间

请直接返回重写后的查询语句，不要添加解释。"""
        
        # 收集重写结果
        rewritten_query = original_query  # 默认使用原查询
        async for chunk in llm_service.stream_response(system_prompt, "请重写查询语句"):
            if chunk.strip():
                rewritten_query = chunk.strip()
                break
        
        return {
            "messages": messages + [HumanMessage(content=rewritten_query)],
            "current_node": "rewrite",
            "node_history": state.get("node_history", []) + [{
                "node": "rewrite",
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "original_query": original_query[:100],
                "rewritten_query": rewritten_query[:100]
            }]
        }
    except Exception as e:
        print(f"❌ 重写节点失败: {e}")
        return {
            "error": f"重写失败: {str(e)}",
            "current_node": "rewrite",
            "node_history": state.get("node_history", []) + [{
                "node": "rewrite",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }]
        }

async def generate_node(state: AgentState, config: dict) -> dict:
    """生成节点 - 生成最终回答"""
    try:
        documents = state.get("documents", [])
        messages = state.get("messages", [])
        
        if not documents:
            return {
                "generation": "抱歉，我没有在知识库中找到相关信息。请尝试重新表述您的问题。",
                "current_node": "generate",
                "node_history": state.get("node_history", []) + [{
                    "node": "generate",
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "note": "no_documents_found"
                }]
            }
        
        # 获取用户查询
        last_message = messages[-1]
        query = getattr(last_message, 'content', str(last_message))
        
        # 准备上下文
        context_parts = []
        for i, doc in enumerate(documents[:3]):  # 最多使用3个文档
            score = doc.get("score", 0)
            title = doc.get("title", "无标题")
            content = doc.get("content", "")
            context_parts.append(f"【文档{i+1} - {title} (相关度: {score:.2%})】")
            context_parts.append(content[:800])  # 限制每个文档长度
            context_parts.append("---")
        
        context_text = "\n".join(context_parts)
        
        # 使用 LLM 生成回答
        llm_service = get_llm_service()
        
        # 收集生成结果
        full_response = ""
        async for chunk in llm_service.stream_response(query, context_text):
            full_response += chunk
        
        return {
            "generation": full_response,
            "current_node": "generate",
            "node_history": state.get("node_history", []) + [{
                "node": "generate",
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "documents_used": len(documents[:3]),
                "response_length": len(full_response)
            }]
        }
    except Exception as e:
        print(f"❌ 生成节点失败: {e}")
        return {
            "error": f"生成失败: {str(e)}",
            "current_node": "generate",
            "node_history": state.get("node_history", []) + [{
                "node": "generate",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }]
        }

async def fallback_node(state: AgentState, config: dict) -> dict:
    """回退节点 - 处理无法回答的情况"""
    return {
        "generation": "抱歉，我无法找到足够的相关信息来回答您的问题。建议您：\n1. 尝试使用不同的关键词\n2. 将问题表述得更具体\n3. 上传相关文档到知识库",
        "current_node": "fallback",
        "node_history": state.get("node_history", []) + [{
            "node": "fallback",
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "note": "fallback_response"
        }]
    }

async def decide_tools_node(state: AgentState, config: dict) -> dict:
    """决定是否使用工具节点"""
    try:
        messages = state.get("messages", [])
        last_message = messages[-1]
        query = getattr(last_message, 'content', str(last_message))
        
        # 使用 LLM 判断是否需要工具
        llm_service = get_llm_service()
        
        system_prompt = f"""分析以下问题，判断是否需要调用外部工具来解答。
        
用户问题: {query}

请分析：
1. 是否需要实时信息（天气、新闻、股票等）？
2. 是否需要计算或单位转换？
3. 是否需要搜索最新网络信息？
4. 是否需要在知识库基础上补充外部信息？

如果需要任何工具，回答"yes"，否则回答"no"。
只回答"yes"或"no"，不要解释。"""
        
        response = ""
        async for chunk in llm_service.stream_response(system_prompt, "请分析是否需要工具"):
            response += chunk
        
        should_use_tools = "yes" in response.lower()
        
        return {
            "should_use_tools": should_use_tools,
            "current_node": "decide_tools",
            "node_history": state.get("node_history", []) + [{
                "node": "decide_tools",
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "decision": should_use_tools,
                "reason": response[:100]
            }]
        }
    except Exception as e:
        print(f"❌ 工具决策节点失败: {e}")
        return {
            "should_use_tools": False,
            "current_node": "decide_tools",
            "node_history": state.get("node_history", []) + [{
                "node": "decide_tools",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }]
        }

async def tools_node(state: AgentState, config: dict) -> dict:
    """工具调用节点"""
    try:
        tool_manager = get_tool_manager()
        tools = tool_manager.get_tools_list()
        
        # 绑定工具到LLM
        llm_service = get_llm_service()
        llm_with_tools = llm_service.bind_tools(tools)
        
        # 获取对话历史
        messages = state.get("messages", [])
        
        # 调用LLM（它会决定使用哪个工具）
        response = await llm_with_tools.ainvoke(messages)
        
        # 检查是否有工具调用
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_calls = []
            tool_results = []
            
            for tool_call in response.tool_calls:
                # 执行工具
                result = await tool_manager.execute_tool(
                    tool_call['name'], 
                    **tool_call['args']
                )
                
                tool_calls.append(tool_call)
                tool_results.append(result)
                
                # 添加工具消息到对话历史
                tool_message = ToolMessage(
                    content=json.dumps(result, ensure_ascii=False),
                    tool_call_id=tool_call.get('id', f"call_{len(tool_calls)}")
                )
                messages.append(tool_message)
            
            return {
                "messages": messages + [response],  # 添加AI的响应
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "current_node": "tools",
                "node_history": state.get("node_history", []) + [{
                    "node": "tools",
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "tools_called": len(tool_calls),
                    "tool_names": [tc['name'] for tc in tool_calls]
                }]
            }
        else:
            # 没有工具调用，直接返回响应
            return {
                "messages": messages + [response],
                "generation": response.content,
                "current_node": "tools",
                "node_history": state.get("node_history", []) + [{
                    "node": "tools",
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "note": "no_tools_called"
                }]
            }
            
    except Exception as e:
        print(f"❌ 工具节点失败: {e}")
        return {
            "error": f"工具调用失败: {str(e)}",
            "current_node": "tools",
            "node_history": state.get("node_history", []) + [{
                "node": "tools",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }]
        }


# ==================== 路由逻辑 ====================

def should_retry(state: AgentState) -> str:
    """判断是否需要重试检索"""
    retry_count = state.get("retry_count", 0)
    if retry_count < 2:  # 最多重试2次
        return "rewrite"
    return "fallback"

def route_after_grade(state: AgentState) -> str:
    """评估后的路由逻辑"""
    is_relevant = state.get("is_relevant")
    
    if is_relevant is None:
        return "generate"  # 如果评估失败，默认生成
    
    if is_relevant:
        return "generate"
    else:
        # 文档不相关，需要重写查询
        return "should_retry"

def route_after_retry(state: AgentState) -> str:
    """重试后的路由逻辑"""
    retry_count = state.get("retry_count", 0)
    if retry_count >= 2:
        return "fallback"
    return "retrieve"

# ==================== 构建工作流 ====================

def create_agent_workflow():
    """创建代理工作流 - 增强版，支持工具调用"""
    
    # 创建状态图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("start", start_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade", grade_node)
    workflow.add_node("rewrite", rewrite_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("decide_tools", decide_tools_node)  # 新增
    workflow.add_node("tools", tools_node)  # 新增
    
    # 设置入口点
    workflow.set_entry_point("start")

    # 先决定是否用工具
    workflow.add_edge("start", "decide_tools")

    # 条件边：决定是否使用工具
    workflow.add_conditional_edges(
        "decide_tools",
        lambda state: "tools" if state.get("should_use_tools") else "retrieve",
        {
            "tools": "tools",
            "retrieve": "retrieve"
        }
    )
    
    # 工具调用后，进入正常的RAG流程或直接生成
    workflow.add_conditional_edges(
        "tools",
        lambda state: "generate" if state.get("generation") else "retrieve",
        {
            "generate": "generate",
            "retrieve": "retrieve"
        }
    )
    
    # 原有的RAG流程保持不变
    workflow.add_edge("retrieve", "grade")
    
    # 条件边：评估后的路由
    workflow.add_conditional_edges(
        "grade",
        route_after_grade,
        {
            "generate": "generate",
            "should_retry": "should_retry"
        }
    )
    
    # 条件边：重试决策
    workflow.add_conditional_edges(
        "should_retry",
        should_retry,
        {
            "rewrite": "rewrite",
            "fallback": "fallback"
        }
    )
    
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("generate", END)
    workflow.add_edge("fallback", END)
    
    # 编译工作流
    app = workflow.compile()
    
    return app

# 全局工作流实例
_agent_workflow = None

def get_agent_workflow():
    """获取代理工作流实例"""
    global _agent_workflow
    if _agent_workflow is None:
        _agent_workflow = create_agent_workflow()
    return _agent_workflow

# ==================== 辅助函数 ====================

def format_workflow_debug(state: AgentState) -> dict:
    """格式化工作流调试信息"""
    return {
        "current_node": state.get("current_node", "unknown"),
        "node_history": state.get("node_history", []),
        "documents_count": len(state.get("documents", [])),
        "generation_length": len(state.get("generation", "")),
        "is_relevant": state.get("is_relevant"),
        "retry_count": state.get("retry_count", 0),
        "error": state.get("error"),
        "execution_time": str(datetime.now() - state.get("start_time", datetime.now()))
    }