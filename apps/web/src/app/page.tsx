"use client";

import { withAuth } from "@/contexts/AuthContext";
import { AgenticChatBox } from "@/components/agentic-chat-box";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileUpload } from "@/components/file-upload";
import { BrainCircuit, Database, Cpu, Sparkles, Shield, User } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { KnowledgeGraph } from "@/components/knowledge-graph";
import { GraphRAGQuery } from "@/components/graph-rag-query";
import { MonitoringDashboard } from "@/components/monitoring-dashboard";

function HomePage() {
  const { user, logout } = useAuth();

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50">
      {/* 顶部导航栏 */}
      <header className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center">
                <BrainCircuit className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
                KnoSphere
              </h1>
              <Badge variant="outline" className="border-emerald-500/30 text-emerald-300">
                <Shield className="w-3 h-3 mr-1" />
                安全模式
              </Badge>
            </div>

            {/* 用户信息 */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-zinc-800/50 px-3 py-1.5 rounded-lg">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500/20 to-emerald-500/20 flex items-center justify-center">
                  <User className="w-4 h-4 text-blue-400" />
                </div>
                <div className="text-sm">
                  <div className="font-medium text-zinc-100">{user?.username}</div>
                  <div className="text-xs text-zinc-500">
                    {user?.permissions?.admin ? '管理员' : '用户'}
                  </div>
                </div>
              </div>
              <button
                onClick={logout}
                className="px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg text-zinc-300 transition-colors"
              >
                退出
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 主要内容 */}
      <div className="max-w-7xl mx-auto p-4 md:p-8">
        <div className="space-y-8">
          {/* 欢迎信息 */}
          <section className="text-center space-y-4 py-8">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
              欢迎回来，{user?.username}！
            </h2>
            <p className="text-lg text-zinc-400">
              您的知识库已安全隔离，仅您可见
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Badge variant="secondary" className="bg-blue-500/10 text-blue-300">
                <Shield className="w-3 h-3 mr-1" />
                行级安全 (RLS)
              </Badge>
              <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-300">
                <Database className="w-3 h-3 mr-1" />
                向量加密
              </Badge>
              <Badge variant="secondary" className="bg-purple-500/10 text-purple-300">
                <Cpu className="w-3 h-3 mr-1" />
                JWT 认证
              </Badge>
              {user?.permissions?.admin && (
                <Badge variant="secondary" className="bg-amber-500/10 text-amber-300">
                  <Sparkles className="w-3 h-3 mr-1" />
                  管理员权限
                </Badge>
              )}
            </div>
          </section>

          {/* 主要功能区域 */}
          <Tabs defaultValue="chat" className="w-full">
            <TabsList className="grid w-full md:w-auto grid-cols-5 md:inline-flex bg-zinc-900/50 border border-zinc-800">
              <TabsTrigger value="chat" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-600 data-[state=active]:to-emerald-600">
                智能对话
              </TabsTrigger>
              <TabsTrigger value="graph" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-pink-600">
                知识图谱
              </TabsTrigger>
              <TabsTrigger value="upload" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-emerald-600 data-[state=active]:to-teal-600">
                知识录入
              </TabsTrigger>
              {user?.permissions?.admin && (
                <>
                  <TabsTrigger value="monitoring" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-amber-600 data-[state=active]:to-orange-600">
                    系统监控
                  </TabsTrigger>
                  <TabsTrigger value="admin" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-red-600 data-[state=active]:to-rose-600">
                    管理面板
                  </TabsTrigger>
                </>
              )}
            </TabsList>
            
            <TabsContent value="chat" className="space-y-6">
              <Card className="bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-xl flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 animate-pulse"></div>
                    智能助手（支持工具调用）
                  </CardTitle>
                  <p className="text-zinc-400 text-sm">
                    支持搜索、天气查询、计算、单位转换等多种工具调用
                  </p>
                </CardHeader>
                <CardContent>
                  <AgenticChatBox />
                </CardContent>
              </Card>
            </TabsContent>

            {/* 知识图谱标签页 */}
            <TabsContent value="graph" className="space-y-6">
              <Card className="bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-xl flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 animate-pulse"></div>
                    知识图谱探索
                  </CardTitle>
                  <p className="text-zinc-400 text-sm">
                    可视化您的知识库，发现实体之间的隐藏关系
                  </p>
                </CardHeader>
                <CardContent>
                  <KnowledgeGraph />
                </CardContent>
              </Card>
              
              <Card className="bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-xl flex items-center gap-2">
                    <BrainCircuit className="w-5 h-5 text-blue-400" />
                    GraphRAG 深度查询
                  </CardTitle>
                  <p className="text-zinc-400 text-sm">
                    结合文档内容和知识图谱的智能查询，回答复杂问题
                  </p>
                </CardHeader>
                <CardContent>
                  <GraphRAGQuery />
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="upload" className="space-y-6">
              <FileUpload />
            </TabsContent>
            
            {user?.permissions?.admin && (
              <TabsContent value="monitoring" className="space-y-6">
                <Card className="bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle className="text-xl flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 animate-pulse"></div>
                      系统监控仪表板
                    </CardTitle>
                    <p className="text-zinc-400 text-sm">
                      实时监控 AI 系统性能、成本和健康状况
                    </p>
                  </CardHeader>
                  <CardContent>
                    <MonitoringDashboard />
                  </CardContent>
                </Card>
              </TabsContent>
            )}
          </Tabs>
        </div>
      </div>
    </main>
  );
}

// 使用高阶组件保护路由
export default withAuth(HomePage, [
  { resource: "documents", action: "read" }
]);