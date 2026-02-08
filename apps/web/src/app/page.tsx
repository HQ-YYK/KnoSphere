import { AgenticChatBox } from "@/components/agentic-chat-box";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileUpload } from "@/components/file-upload";
import { BrainCircuit, Database, Cpu, Sparkles } from "lucide-react";
import './page.css'

export default function Home() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* 顶部装饰 */}
        <section className="text-center space-y-6 py-8">
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 via-emerald-400 to-cyan-400 bg-clip-text text-transparent animate-gradient">
            KnoSphere
          </h1>
          <p className="text-xl text-zinc-400 font-light">2026 企业级智能知识库中枢 - Agentic AI</p>
          <div className="flex flex-wrap justify-center gap-3">
            <Badge variant="secondary" className="bg-blue-500/10 text-blue-300 hover:bg-blue-500/20">
              <BrainCircuit className="w-3 h-3 mr-1" />
              思考可视化
            </Badge>
            <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20">
              <Database className="w-3 h-3 mr-1" />
              向量检索
            </Badge>
            <Badge variant="secondary" className="bg-purple-500/10 text-purple-300 hover:bg-purple-500/20">
              <Cpu className="w-3 h-3 mr-1" />
              智能体架构
            </Badge>
            <Badge variant="secondary" className="bg-amber-500/10 text-amber-300 hover:bg-amber-500/20">
              <Sparkles className="w-3 h-3 mr-1" />
              LangGraph
            </Badge>
          </div>
        </section>

        {/* 主要功能区域 */}
        <Tabs defaultValue="chat" className="w-full">
          <TabsList className="grid w-full md:w-auto grid-cols-2 md:inline-flex bg-zinc-900/50 border border-zinc-800">
            <TabsTrigger value="chat" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-600 data-[state=active]:to-emerald-600">
              智能对话
            </TabsTrigger>
            <TabsTrigger value="upload" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-600 data-[state=active]:to-pink-600">
              知识录入
            </TabsTrigger>
            <TabsTrigger value="analytics" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-amber-600 data-[state=active]:to-orange-600">
              分析洞察
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="chat" className="space-y-6">
            <Card className="bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-xl flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-emerald-500 animate-pulse"></div>
                  AI 智能对话
                </CardTitle>
                <p className="text-zinc-400 text-sm">
                  体验 AI 的思考过程，查看每个步骤的详细推理
                </p>
              </CardHeader>
              <CardContent>
                <AgenticChatBox />
              </CardContent>
            </Card>
            
            {/* 系统信息卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center">
                      <BrainCircuit className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <h4 className="font-medium text-zinc-100">思考过程</h4>
                      <p className="text-sm text-zinc-400">查看 AI 的完整推理链路</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card className="bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
                      <Database className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                      <h4 className="font-medium text-zinc-100">向量检索</h4>
                      <p className="text-sm text-zinc-400">1536 维语义搜索</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card className="bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center">
                      <Cpu className="w-5 h-5 text-purple-400" />
                    </div>
                    <div>
                      <h4 className="font-medium text-zinc-100">智能体架构</h4>
                      <p className="text-sm text-zinc-400">基于 LangGraph 的状态机</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          <TabsContent value="upload" className="space-y-6">
            <FileUpload />
          </TabsContent>
          
          <TabsContent value="analytics" className="space-y-6">
            <Card className="bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-xl">📊 系统分析</CardTitle>
                <p className="text-zinc-400 text-sm">KnoSphere 性能与使用统计</p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="text-center py-12">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-800/50 mb-4">
                      <div className="text-zinc-500 text-2xl">📈</div>
                    </div>
                    <p className="text-zinc-400">分析功能开发中</p>
                    <p className="text-zinc-500 text-sm mt-2">
                      即将推出: 对话分析、知识图谱、使用统计
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}