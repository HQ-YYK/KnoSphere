"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Bot, 
  User, 
  Send, 
  Loader2, 
  BrainCircuit,
  Zap,
  Clock,
  Sparkles,
  Settings
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { ThinkingProcess } from "./thinking-process";
import { Badge } from "@/components/ui/badge";

interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp: Date;
  thinkingSteps?: any[];
  mode?: "full" | "simple" | "agentic";
  workflowId?: string;
  isThinking?: boolean;
  tool_calls?: Array<{  // 工具调用
    name: string;
    args: any;
    result?: any;
  }>;
}

interface ThinkingStep {
  id: string;
  type: string;
  data: string;
  stage?: string;
  progress?: number;
  timestamp: string;
  metadata?: Record<string, any>;
}

export function AgenticChatBox() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "👋 你好！我是 KnoSphere AI 助手，支持思考过程可视化。您可以选择完整模式查看我的思考过程，或简单模式快速获取回答。",
      timestamp: new Date(),
      mode: "full"
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [chatMode, setChatMode] = useState<"full" | "simple" | "agentic">("agentic");
  const [toolExecutions, setToolExecutions] = useState<any[]>([]);
  const [activeTools, setActiveTools] = useState<string[]>([]);
  const [activeThinking, setActiveThinking] = useState<ThinkingStep[]>([]);
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // 自动滚动到底部
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]");
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [messages, activeThinking]);

  // 解析流式响应
  const parseStreamResponse = async (response: Response) => {
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    
    if (!reader) {
      throw new Error("无法读取响应流");
    }
    
    let aiContent = "";
    let thinkingSteps: ThinkingStep[] = [];
    let workflowId = response.headers.get("X-Workflow-ID");
    let streamMode = response.headers.get("X-Stream-Mode") as "full" | "simple";
    
    if (workflowId) {
      setCurrentWorkflowId(workflowId);
    }
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n").filter(line => line.trim());
      
      for (const line of lines) {
        try {
          const message = JSON.parse(line);
          
          // 处理不同类型的消息
          switch (message.type) {
            case "thinking_start":
            case "retrieval_start":
            case "retrieval_end":
            case "generation_start":
            case "generation_end":
            case "complete":
            case "error":
            case "status":
              // 思考步骤
              const thinkingStep: ThinkingStep = {
                id: `${Date.now()}_${thinkingSteps.length}`,
                type: message.type,
                data: message.data || "",
                stage: message.stage,
                progress: message.progress,
                timestamp: message.timestamp || new Date().toISOString(),
                metadata: message.metadata
              };
              
              thinkingSteps.push(thinkingStep);
              
              // 更新活动思考过程
              if (streamMode === "full") {
                setActiveThinking([...thinkingSteps]);
              }
              break;
              
            case "chunk":
              // 内容块
              aiContent += message.data;
              
              // 更新 AI 消息内容
              setMessages(prev => prev.map(msg => 
                msg.id === currentWorkflowId 
                  ? { ...msg, content: aiContent, thinkingSteps }
                  : msg
              ));
              
              // 如果是简单模式，不显示思考过程
              if (streamMode === "simple") {
                setActiveThinking([]);
              }
              break;
          }
        } catch (e) {
          // 如果不是 JSON，可能是原始文本
          if (line.trim()) {
            aiContent += line;
            setMessages(prev => prev.map(msg => 
              msg.id === currentWorkflowId 
                ? { ...msg, content: aiContent }
                : msg
            ));
          }
        }
      }
    }
    
    return { content: aiContent, thinkingSteps, workflowId };
  };

  async function sendMessage() {
    const userMessage = input.trim();
    if (!userMessage || isLoading) return;

    // 根据模式选择不同的端点
    let endpoint = "/chat/stream";
    let requestBody = {
      query: userMessage,
      mode: chatMode === "simple" ? "simple" : "full",
      top_k: 10,
      final_k: 3
    };
    
    if (chatMode === "agentic") {
      endpoint = "/agent/execute";
      requestBody = {
        query: userMessage,
        use_knowledge: true,
        stream: false
      };
    }
    
    // 添加用户消息
    const userMsg: Message = {
      id: `user_${Date.now()}`,
      role: "user",
      content: userMessage,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);
    
    // 添加初始的 AI 消息（空内容）
    const aiMsgId = `ai_${Date.now()}`;
    const aiMsg: Message = {
      id: aiMsgId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      mode: chatMode,
      isThinking: true,
      thinkingSteps: []
    };
    
    setMessages(prev => [...prev, aiMsg]);
    setCurrentWorkflowId(aiMsgId);
    
    // 重置思考过程
    if (chatMode === "full") {
      setActiveThinking([]);
    }
    
    try {
      // 调用后端流式聊天接口
      const response = await fetch("http://localhost:8000/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: userMessage,
          mode: chatMode,
          top_k: 10,
          final_k: 3
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // 解析流式响应
      await parseStreamResponse(response);
      
      // 完成思考
      setMessages(prev => prev.map(msg => 
        msg.id === aiMsgId 
          ? { ...msg, isThinking: false }
          : msg
      ));
      
    } catch (error: any) {
      console.error("聊天请求失败:", error);
      
      // 更新 AI 消息为错误信息
      setMessages(prev => prev.map(msg => 
        msg.id === aiMsgId 
          ? { 
              ...msg, 
              content: `❌ 抱歉，请求失败：${error.message}`,
              isThinking: false
            }
          : msg
      ));
      
      toast({
        title: "请求失败",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
      setActiveThinking([]);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  // 格式化时间
  function formatTime(date: Date) {
    return date.toLocaleTimeString("zh-CN", { 
      hour: "2-digit", 
      minute: "2-digit" 
    });
  }

  // 获取当前正在思考的消息
  const currentThinkingMessage = messages.find(msg => msg.isThinking);

  return (
    <div className="flex flex-col h-full">
      {/* 聊天头部 */}
      <Card className="bg-zinc-900/50 border-zinc-800 mb-4">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center">
                <BrainCircuit className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-zinc-100">KnoSphere AI 助手</h3>
                <p className="text-xs text-zinc-400">支持思考过程可视化</p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Tabs value={chatMode} onValueChange={(v) => setChatMode(v as "full" | "simple" | "agentic")}>
                <TabsList className="bg-zinc-800/50 border border-zinc-700">
                  <TabsTrigger value="agentic" className="data-[state=active]:bg-purple-600">
                    <BrainCircuit className="w-3 h-3 mr-1" />
                    智能模式
                  </TabsTrigger>
                  <TabsTrigger value="full" className="data-[state=active]:bg-blue-600">
                    <Sparkles className="w-3 h-3 mr-1" />
                    完整模式
                  </TabsTrigger>
                  <TabsTrigger value="simple" className="data-[state=active]:bg-emerald-600">
                    <Zap className="w-3 h-3 mr-1" />
                    快速模式
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <div className="flex-1 flex gap-4">
        {/* 左侧：聊天主区域 */}
        <div className="flex-1 flex flex-col">
          <Card className="flex-1 bg-zinc-900/30 border-zinc-800">
            <ScrollArea className="h-[500px] p-4" ref={scrollAreaRef}>
              <div className="space-y-6">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}
                  >
                    {/* 头像 */}
                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                      message.role === "user" 
                        ? "bg-blue-600" 
                        : "bg-gradient-to-br from-blue-500 to-emerald-500"
                    }`}>
                      {message.role === "user" ? (
                        <User className="w-4 h-4 text-white" />
                      ) : (
                        <Bot className="w-4 h-4 text-white" />
                      )}
                    </div>
                    
                    {/* 消息内容 */}
                    <div className={`max-w-[80%] rounded-2xl p-4 ${
                      message.role === "user"
                        ? "bg-blue-600 text-white rounded-tr-none"
                        : "bg-zinc-800/70 text-zinc-100 rounded-tl-none"
                    }`}>
                      <div className="whitespace-pre-wrap break-words">
                        {message.content}
                      </div>
                      
                      {/* 消息时间 */}
                      <div className={`text-xs mt-2 flex items-center justify-between ${
                        message.role === "user" ? "text-blue-200" : "text-zinc-400"
                      }`}>
                        <span>{formatTime(message.timestamp)}</span>
                        {message.mode && (
                          <Badge variant="outline" className="text-xs border-transparent bg-zinc-700/50">
                            {message.mode === "full" ? (
                              <Sparkles className="w-2 h-2 mr-1" />
                            ) : (
                              <Zap className="w-2 h-2 mr-1" />
                            )}
                            {message.mode === "full" ? "完整思考" : "快速回答"}
                          </Badge>
                        )}
                      </div>
                      
                      {/* 思考步骤预览 */}
                      {message.thinkingSteps && message.thinkingSteps.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-zinc-700/50">
                          <div className="flex items-center gap-2 text-xs text-zinc-400 mb-2">
                            <BrainCircuit className="w-3 h-3" />
                            <span>思考过程 ({message.thinkingSteps.length} 步骤)</span>
                          </div>
                          <div className="space-y-1">
                            {message.thinkingSteps.slice(-3).map((step: any, idx: number) => (
                              <div key={idx} className="text-xs text-zinc-500 flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${
                                  step.type === "complete" ? "bg-green-500" :
                                  step.type === "error" ? "bg-red-500" :
                                  "bg-blue-500"
                                }`}></div>
                                <span className="truncate">{step.data}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {message.tool_calls && message.tool_calls.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-purple-700/50">
                          <div className="flex items-center gap-2 text-xs text-purple-400 mb-2">
                            <Wrench className="w-3 h-3" />
                            <span>工具调用 ({message.tool_calls.length} 个)</span>
                          </div>
                          <div className="space-y-2">
                            {message.tool_calls.map((tool: any, idx: number) => (
                              <div key={idx} className="text-xs bg-purple-900/20 rounded p-2">
                                <div className="flex items-center gap-2 mb-1">
                                  <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                                  <span className="font-medium">{tool.name}</span>
                                </div>
                                {tool.result && (
                                  <div className="text-purple-300 text-xs mt-1">
                                    {JSON.stringify(tool.result).slice(0, 100)}...
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                
                {/* 当前思考过程 */}
                {currentThinkingMessage && chatMode === "full" && activeThinking.length > 0 && (
                  <div className="mt-4">
                    <ThinkingProcess 
                      steps={activeThinking}
                      isActive={true}
                    />
                  </div>
                )}
                
                {/* 加载指示器 */}
                {isLoading && !currentThinkingMessage && (
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="bg-zinc-800/70 text-zinc-100 rounded-2xl rounded-tl-none p-4">
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="text-zinc-400">正在思考...</span>
                      </div>
                      <div className="mt-2 flex gap-1">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse delay-150"></div>
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse delay-300"></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </Card>
          
          {/* 输入区域 */}
          <Card className="mt-4 bg-zinc-900/30 border-zinc-800">
            <CardContent className="p-4">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={`输入您的问题... (按 Enter 发送，当前模式: ${chatMode === "full" ? "完整思考" : "快速回答"})`}
                    className="bg-zinc-800 border-zinc-700 focus:border-emerald-500 pr-10"
                    disabled={isLoading}
                  />
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-zinc-500 text-xs">
                    ↵
                  </div>
                </div>
                <Button 
                  onClick={sendMessage} 
                  disabled={!input.trim() || isLoading}
                  className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </div>
              <div className="mt-2 text-xs text-zinc-500 flex justify-between">
                <span>支持技术问题、文档查询、知识检索</span>
                <span>{messages.length} 条消息</span>
              </div>
            </CardContent>
          </Card>
        </div>
        
        {/* 右侧：思考过程侧边栏 */}
        {chatMode === "full" && (
          <div className="w-80 flex flex-col gap-4">
            <Card className="bg-zinc-900/30 border-zinc-800">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <BrainCircuit className="w-4 h-4 text-blue-400" />
                  <h4 className="font-medium text-zinc-100">思考过程说明</h4>
                </div>
                <div className="space-y-2 text-sm text-zinc-400">
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 flex-shrink-0"></div>
                    <span><strong>完整模式</strong>会展示AI的完整思考过程，包括检索、分析、生成等步骤</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0"></div>
                    <span><strong>快速模式</strong>会直接生成回答，适合简单问题或需要快速响应的场景</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-2 h-2 rounded-full bg-purple-500 mt-1.5 flex-shrink-0"></div>
                    <span>系统会自动根据问题复杂度调整检索策略和生成参数</span>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-zinc-900/30 border-zinc-800">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Settings className="w-4 h-4 text-amber-400" />
                  <h4 className="font-medium text-zinc-100">系统状态</h4>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-zinc-400">当前模式</span>
                    <Badge variant={chatMode === "full" ? "default" : "secondary"}>
                      {chatMode === "full" ? "完整思考" : "快速回答"}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-zinc-400">检索策略</span>
                    <span className="text-sm text-zinc-300">平衡模式</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-zinc-400">向量维度</span>
                    <Badge variant="outline" className="text-xs border-zinc-700">
                      1536 维
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-zinc-400">响应延迟</span>
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-zinc-500" />
                      <span className="text-sm text-zinc-300">~500ms</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {currentWorkflowId && (
              <Card className="bg-zinc-900/30 border-zinc-800">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-4 h-4 text-purple-400" />
                    <h4 className="font-medium text-zinc-100">工作流信息</h4>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-zinc-400">工作流ID</span>
                      <code className="text-xs text-zinc-300 bg-zinc-800 px-2 py-1 rounded">
                        {currentWorkflowId.slice(0, 8)}...
                      </code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">开始时间</span>
                      <span className="text-zinc-300">
                        {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">思考步骤</span>
                      <span className="text-zinc-300">
                        {activeThinking.length} 个
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}