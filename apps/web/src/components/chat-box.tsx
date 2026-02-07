"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card, CardContent } from "@/components/ui/card"
import { Bot, User, Send, Loader2, BookOpen } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  sources?: Array<{
    title: string
    score: number
    content_preview: string
  }>
}

export function ChatBox() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "👋 你好！我是 KnoSphere AI 助手。我可以帮您查询知识库中的文档信息。请告诉我您想了解什么？",
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()

  // 自动滚动到底部
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]")
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [messages])

  async function sendMessage() {
    const userMessage = input.trim()
    if (!userMessage || isLoading) return
    
    // 添加用户消息
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userMessage,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setIsLoading(true)
    
    // 添加初始的 AI 消息（空内容）
    const aiMsgId = (Date.now() + 1).toString()
    const aiMsg: Message = {
      id: aiMsgId,
      role: "assistant",
      content: "",
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, aiMsg])
    
    try {
      // 调用后端聊天接口
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: userMessage,
          top_k: 10,
          final_k: 3
        })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      // 读取流式响应
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      if (!reader) {
        throw new Error("无法读取响应流")
      }
      
      let aiResponse = ""
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value, { stream: true })
        aiResponse += chunk
        
        // 更新 AI 消息内容
        setMessages(prev => prev.map(msg => 
          msg.id === aiMsgId 
            ? { ...msg, content: aiResponse }
            : msg
        ))
      }
      
    } catch (error: any) {
      console.error("聊天请求失败:", error)
      
      // 更新 AI 消息为错误信息
      setMessages(prev => prev.map(msg => 
        msg.id === aiMsgId 
          ? { 
              ...msg, 
              content: `❌ 抱歉，请求失败：${error.message}\n\n请检查：\n1. 后端服务是否正在运行\n2. API Key 是否正确配置\n3. 网络连接是否正常` 
            }
          : msg
      ))
      
      toast({
        title: "请求失败",
        description: error.message,
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // 格式化时间
  function formatTime(date: Date) {
    return date.toLocaleTimeString("zh-CN", { 
      hour: "2-digit", 
      minute: "2-digit" 
    })
  }

  return (
    <Card className="bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
      <CardContent className="p-0">
        <div className="flex flex-col h-[600px]">
          {/* 聊天头部 */}
          <div className="p-4 border-b border-zinc-800">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-zinc-100">KnoSphere AI 助手</h3>
                <p className="text-xs text-zinc-400">基于知识库的智能问答</p>
              </div>
            </div>
          </div>
          
          {/* 消息区域 */}
          <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
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
                      : "bg-emerald-600"
                  }`}>
                    {message.role === "user" ? (
                      <User className="w-4 h-4 text-white" />
                    ) : (
                      <Bot className="w-4 h-4 text-white" />
                    )}
                  </div>
                  
                  {/* 消息内容 */}
                  <div className={`max-w-[70%] rounded-2xl p-4 ${
                    message.role === "user"
                      ? "bg-blue-600 text-white rounded-tr-none"
                      : "bg-zinc-800 text-zinc-100 rounded-tl-none"
                  }`}>
                    <div className="whitespace-pre-wrap break-words">
                      {message.content}
                    </div>
                    
                    {/* 消息时间 */}
                    <div className={`text-xs mt-2 ${
                      message.role === "user" ? "text-blue-200" : "text-zinc-400"
                    }`}>
                      {formatTime(message.timestamp)}
                    </div>
                    
                    {/* 知识来源（仅 AI 消息） */}
                    {message.role === "assistant" && message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-zinc-700/50">
                        <div className="flex items-center gap-2 text-xs text-zinc-400 mb-2">
                          <BookOpen className="w-3 h-3" />
                          <span>知识来源</span>
                        </div>
                        <div className="space-y-2">
                          {message.sources.map((source, index) => (
                            <div key={index} className="text-xs bg-zinc-900/50 rounded p-2">
                              <div className="font-medium">{source.title}</div>
                              <div className="text-zinc-500">{source.content_preview}</div>
                              <div className="text-emerald-400">相关度: {source.score}%</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {/* 加载指示器 */}
              {isLoading && (
                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-zinc-800 text-zinc-100 rounded-2xl rounded-tl-none p-4">
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
          
          {/* 输入区域 */}
          <div className="p-4 border-t border-zinc-800 bg-zinc-900/30">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入您的问题...（按 Enter 发送）"
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
          </div>
        </div>
      </CardContent>
    </Card>
  )
}