import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-slate-100 p-8">
      {/* 背景效果 - 添加一些装饰性元素 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl"></div>
      </div>

      <div className="relative z-10 max-w-5xl mx-auto space-y-12">
        {/* 顶部标题 - 玻璃态效果 */}
        <section className="text-center space-y-4">
          <div className="inline-block p-8 rounded-2xl bg-slate-800/30 backdrop-blur-md border border-slate-700/50">
            <h1 className="text-6xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 via-emerald-400 to-cyan-400 bg-clip-text text-transparent">
              KnoSphere
            </h1>
            <p className="text-slate-300 text-lg mt-4">2026 企业级智能知识库中枢</p>
            <div className="flex justify-center gap-2 mt-4">
              <Badge variant="secondary" className="bg-blue-500/20 text-blue-300 border-blue-500/30 backdrop-blur-sm">React 19</Badge>
              <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30 backdrop-blur-sm">FastAPI</Badge>
              <Badge variant="secondary" className="bg-purple-500/20 text-purple-300 border-purple-500/30 backdrop-blur-sm">pgvector</Badge>
            </div>
          </div>
        </section>

        {/* 搜索与快捷操作 */}
        <div className="flex gap-4 max-w-2xl mx-auto">
          <Input 
            placeholder="检索您的企业知识..." 
            className="bg-gray-800 border-gray-700 text-gray-100 focus:border-blue-500 focus:ring-blue-500"
          />
          <Button className="bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400">
            搜索
          </Button>
        </div>

        {/* 状态卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm text-gray-100 hover:border-blue-500/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-gray-300">知识总量</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">1,284 篇</div>
              <p className="text-gray-400 text-sm mt-1">持续增长中</p>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm text-gray-100 hover:border-emerald-500/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-gray-300">向量存储</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">1536 维</div>
              <p className="text-gray-400 text-sm mt-1">OpenAI text-embedding-3-small</p>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm text-gray-100 hover:border-purple-500/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-gray-300">响应时间</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">~50ms</div>
              <p className="text-gray-400 text-sm mt-1">HNSW 索引加速</p>
            </CardContent>
          </Card>
        </div>

        {/* 上传区域 */}
        <Card className="bg-gray-800/50 border-gray-700 backdrop-blur-sm max-w-3xl mx-auto">
          <CardHeader>
            <CardTitle className="text-xl text-white">上传新文档</CardTitle>
            <p className="text-gray-400 text-sm">支持 PDF、DOCX、TXT、Markdown 格式</p>
          </CardHeader>
          <CardContent>
            <div className="border-2 border-dashed border-gray-600 rounded-lg p-12 text-center hover:border-blue-500 transition-colors cursor-pointer bg-gray-900/30">
              <div className="space-y-4">
                <div className="text-gray-500">
                  <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                  </svg>
                </div>
                <p className="text-gray-300">拖拽文件到此处或点击上传</p>
                <p className="text-gray-500 text-sm">文件将自动转换为向量并加入知识库</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}