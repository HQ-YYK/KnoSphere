import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileUpload } from "@/components/file-upload";
import { ChatBox } from "@/components/chat-box";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import './page.css';

export default function Home() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* 顶部装饰 */}
        <section className="text-center space-y-6 py-8">
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 via-emerald-400 to-cyan-400 bg-clip-text text-transparent animate-gradient">
            KnoSphere
          </h1>
          <p className="text-xl text-zinc-400 font-light">2026 企业级智能知识库中枢</p>
          <div className="flex flex-wrap justify-center gap-3">
            <Badge variant="secondary" className="bg-blue-500/10 text-blue-300 hover:bg-blue-500/20">React 19</Badge>
            <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20">FastAPI</Badge>
            <Badge variant="secondary" className="bg-purple-500/10 text-purple-300 hover:bg-purple-500/20">pgvector</Badge>
            <Badge variant="secondary" className="bg-amber-500/10 text-amber-300 hover:bg-amber-500/20">Python 3.14</Badge>
          </div>
        </section>

        {/* 主要功能区域 */}
        <Tabs defaultValue="chat" className="w-full">
          <TabsList className="grid w-full md:w-auto grid-cols-2 md:inline-flex bg-zinc-900/50 border border-zinc-800">
            <TabsTrigger value="chat" className="data-[state=active]:bg-emerald-600">
              智能对话
            </TabsTrigger>
            <TabsTrigger value="upload" className="data-[state=active]:bg-blue-600">
              知识录入
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="chat" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2">
                <ChatBox />
              </div>
              
              <div className="space-y-6">
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="text-lg">💡 使用技巧</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div className="flex items-start gap-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-500 mt-1.5"></div>
                      <span>上传文档后，AI 会自动学习内容</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5"></div>
                      <span>提问时尽量具体，便于精准检索</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-2 h-2 rounded-full bg-purple-500 mt-1.5"></div>
                      <span>AI 回答基于检索到的文档内容</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-2 h-2 rounded-full bg-amber-500 mt-1.5"></div>
                      <span>支持技术文档、产品手册、FAQ 等</span>
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="text-lg">📊 系统状态</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-zinc-400">知识总量</span>
                      <span className="font-semibold">0 篇</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-zinc-400">向量维度</span>
                      <Badge variant="outline" className="border-emerald-500/30 text-emerald-300">
                        1536 维
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-zinc-400">响应速度</span>
                      <Badge variant="outline" className="border-blue-500/30 text-blue-300">
                        ~50ms
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="upload" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-xl flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-gradient-to-r from-blue-500 to-emerald-500"></div>
                    文档上传
                  </CardTitle>
                  <p className="text-zinc-400 text-sm">支持多种格式，自动向量化存储</p>
                </CardHeader>
                <CardContent>
                  <FileUpload />
                </CardContent>
              </Card>
              
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-xl flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-gradient-to-r from-purple-500 to-pink-500"></div>
                    知识库概览
                  </CardTitle>
                  <p className="text-zinc-400 text-sm">您的知识库状态</p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="text-center py-12">
                      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-800/50 mb-4">
                        <div className="text-zinc-500 text-2xl">📁</div>
                      </div>
                      <p className="text-zinc-400">知识库为空</p>
                      <p className="text-zinc-500 text-sm mt-2">
                        上传文档后，您就可以通过聊天界面查询了
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}