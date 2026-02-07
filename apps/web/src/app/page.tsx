import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { FileUpload } from "@/components/file-upload";
import './page.css'

export default function Home() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50 p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-8">
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

        {/* 搜索与快捷操作 */}
        <div className="flex flex-col md:flex-row gap-4 max-w-3xl mx-auto">
          <Input 
            placeholder="输入您的问题或关键词，检索企业知识..." 
            className="bg-zinc-900 border-zinc-800 focus:border-blue-500 flex-1"
          />
          <Button className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white px-6">
            智能搜索
          </Button>
        </div>

        {/* 状态卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="bg-zinc-900/80 border-zinc-800 text-zinc-100 backdrop-blur-sm hover:border-blue-500/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                知识总量
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">0 篇</div>
              <p className="text-zinc-400 text-sm mt-2">上传文档后开始增长</p>
            </CardContent>
          </Card>
          
          <Card className="bg-zinc-900/80 border-zinc-800 text-zinc-100 backdrop-blur-sm hover:border-emerald-500/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                向量存储
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">1536 维</div>
              <p className="text-zinc-400 text-sm mt-2">OpenAI text-embedding-3-small</p>
            </CardContent>
          </Card>
          
          <Card className="bg-zinc-900/80 border-zinc-800 text-zinc-100 backdrop-blur-sm hover:border-purple-500/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                响应时间
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">~50ms</div>
              <p className="text-zinc-400 text-sm mt-2">HNSW 索引加速</p>
            </CardContent>
          </Card>
        </div>

        {/* 上传区域 */}
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold text-zinc-100">知识录入</h2>
            <p className="text-zinc-400">上传您的文档，KnoSphere 将自动学习并构建知识网络</p>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <Card className="bg-zinc-900/80 border-zinc-800 backdrop-blur-sm">
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
            
            <Card className="bg-zinc-900/80 border-zinc-800 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-xl flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-gradient-to-r from-purple-500 to-pink-500"></div>
                  最近上传
                </CardTitle>
                <p className="text-zinc-400 text-sm">您最近的文档记录</p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="text-center py-12">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-800/50 mb-4">
                      <div className="text-zinc-500 text-2xl">📁</div>
                    </div>
                    <p className="text-zinc-400">暂无上传记录</p>
                    <p className="text-zinc-500 text-sm mt-2">上传文档后，记录将显示在这里</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </main>
  );
}