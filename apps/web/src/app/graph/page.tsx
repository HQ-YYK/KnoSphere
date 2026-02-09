"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { withAuth } from "@/contexts/AuthContext";
import { KnowledgeGraph } from "@/components/knowledge-graph";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { 
  ArrowLeft, 
  Network, 
  FileText, 
  Filter, 
  X,
  Eye,
  EyeOff,
  RefreshCw,
  Search,
  BrainCircuit
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import AuthService from "@/lib/auth";

function GraphPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { toast } = useToast();
  
  const [graphData, setGraphData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filterDocument, setFilterDocument] = useState<number | null>(null);
  const [filterEntity, setFilterEntity] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [documents, setDocuments] = useState<any[]>([]);
  
  // 从 URL 参数获取过滤条件
  useEffect(() => {
    const docParam = searchParams.get("document");
    const entityParam = searchParams.get("entity");
    
    if (docParam) {
      setFilterDocument(parseInt(docParam));
    }
    if (entityParam) {
      setFilterEntity(parseInt(entityParam));
    }
  }, [searchParams]);
  
  useEffect(() => {
    loadGraphData();
    loadDocuments();
  }, [filterDocument, filterEntity]);
  
  const loadGraphData = async () => {
    setIsLoading(true);
    try {
      let url = "http://localhost:8000/graph/data?include_documents=true";
      
      if (filterDocument) {
        url += `&document_id=${filterDocument}`;
      }
      
      const response = await AuthService.secureFetch(url);
      const data = await response.json();
      setGraphData(data);
    } catch (error: any) {
      console.error("加载图谱数据失败:", error);
      toast({
        title: "加载失败",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const loadDocuments = async () => {
    try {
      const response = await AuthService.secureFetch(
        "http://localhost:8000/documents/recent?limit=50"
      );
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error("加载文档列表失败:", error);
    }
  };
  
  const clearFilters = () => {
    setFilterDocument(null);
    setFilterEntity(null);
    setSearchQuery("");
    router.push("/graph");
  };
  
  const getFilteredDocument = () => {
    if (!filterDocument) return null;
    return documents.find(doc => doc.id === filterDocument);
  };
  
  const filteredDoc = getFilteredDocument();
  
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50">
      {/* 头部 */}
      <header className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Button
                onClick={() => router.push("/")}
                variant="ghost"
                size="sm"
                className="text-zinc-400 hover:text-zinc-300"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                返回
              </Button>
              <div>
                <h1 className="text-lg font-semibold text-zinc-100">
                  知识图谱探索
                </h1>
                <p className="text-xs text-zinc-500">
                  可视化您的知识库，发现隐藏关系
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {filteredDoc && (
                <Badge variant="outline" className="border-blue-500/30 text-blue-300">
                  <FileText className="w-3 h-3 mr-1" />
                  文档: {filteredDoc.title}
                </Badge>
              )}
              <Button
                onClick={clearFilters}
                variant="outline"
                size="sm"
                className="border-zinc-700 hover:bg-zinc-800"
              >
                <X className="w-4 h-4 mr-2" />
                清除过滤
              </Button>
            </div>
          </div>
        </div>
      </header>
      
      {/* 主要内容 */}
      <div className="max-w-7xl mx-auto p-4 md:p-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 左侧控制面板 */}
          <div className="lg:col-span-1 space-y-6">
            {/* 搜索和过滤 */}
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-lg">过滤控制</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* 文档选择 */}
                <div>
                  <label className="text-sm text-zinc-400 mb-2 block">
                    按文档过滤
                  </label>
                  <div className="space-y-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-500" />
                      <Input
                        placeholder="搜索文档..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9 bg-zinc-800 border-zinc-700"
                      />
                    </div>
                    
                    <ScrollArea className="h-48">
                      <div className="space-y-2">
                        <Button
                          variant={filterDocument === null ? "default" : "outline"}
                          className="w-full justify-start bg-zinc-800 hover:bg-zinc-700"
                          onClick={() => setFilterDocument(null)}
                        >
                          <Eye className="w-4 h-4 mr-2" />
                          所有文档
                        </Button>
                        
                        {documents
                          .filter(doc => 
                            !searchQuery || 
                            doc.title.toLowerCase().includes(searchQuery.toLowerCase())
                          )
                          .map((doc) => (
                            <Button
                              key={doc.id}
                              variant={filterDocument === doc.id ? "default" : "outline"}
                              className={`w-full justify-start ${
                                filterDocument === doc.id 
                                  ? "bg-blue-600 hover:bg-blue-700" 
                                  : "bg-zinc-800 hover:bg-zinc-700"
                              }`}
                              onClick={() => {
                                setFilterDocument(doc.id);
                                router.push(`/graph?document=${doc.id}`);
                              }}
                            >
                              <FileText className="w-4 h-4 mr-2" />
                              <span className="truncate">{doc.title}</span>
                            </Button>
                          ))}
                      </div>
                    </ScrollArea>
                  </div>
                </div>
                
                {/* 统计信息 */}
                <div className="pt-4 border-t border-zinc-800">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">实体数量</span>
                      <span className="text-zinc-300">
                        {graphData?.stats?.total_entities || 0}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">关系数量</span>
                      <span className="text-zinc-300">
                        {graphData?.stats?.total_edges || 0}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">文档数量</span>
                      <span className="text-zinc-300">
                        {documents.length}
                      </span>
                    </div>
                  </div>
                </div>
                
                {/* 操作按钮 */}
                <div className="pt-4 border-t border-zinc-800">
                  <div className="flex gap-2">
                    <Button
                      onClick={loadGraphData}
                      variant="outline"
                      className="flex-1 bg-zinc-800 hover:bg-zinc-700"
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      刷新
                    </Button>
                    <Button
                      onClick={() => router.push("/")}
                      className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                    >
                      <BrainCircuit className="w-4 h-4 mr-2" />
                      GraphRAG查询
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* 提示信息 */}
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardContent className="p-4">
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                    <span>点击实体节点查看关联文档</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                    <span>拖拽节点重新布局</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                    <span>使用滚轮缩放图谱</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                    <span>鼠标悬停查看详细信息</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
          
          {/* 右侧图谱区域 */}
          <div className="lg:col-span-3">
            <Card className="bg-zinc-900/50 border-zinc-800 h-full">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xl">
                    知识图谱可视化
                    {filteredDoc && (
                      <span className="text-sm text-zinc-500 ml-2">
                        - {filteredDoc.title}
                      </span>
                    )}
                  </CardTitle>
                  <Badge variant="outline" className="border-emerald-500/30 text-emerald-300">
                    <Network className="w-3 h-3 mr-1" />
                    {graphData?.nodes?.length || 0} 节点, {graphData?.links?.length || 0} 关系
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="h-[600px] flex items-center justify-center">
                    <div className="text-center">
                      <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 mb-4 animate-pulse">
                        <Network className="w-6 h-6 text-white" />
                      </div>
                      <p className="text-zinc-400">加载知识图谱中...</p>
                    </div>
                  </div>
                ) : (
                  <div className="h-[600px] rounded-lg overflow-hidden border border-zinc-800">
                    {graphData?.nodes?.length === 0 ? (
                      <div className="h-full flex items-center justify-center">
                        <div className="text-center">
                          <Network className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
                          <p className="text-zinc-500">没有找到数据</p>
                          <Button
                            onClick={clearFilters}
                            className="mt-4 bg-zinc-800 hover:bg-zinc-700"
                          >
                            清除过滤条件
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <KnowledgeGraph />
                    )}
                  </div>
                )}
                
                {/* 底部提示 */}
                <div className="mt-4 text-sm text-zinc-500 flex items-center justify-between">
                  <div>
                    <span className="inline-flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                      点击节点查看文档
                    </span>
                    <span className="mx-4">•</span>
                    <span className="inline-flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                      右键拖拽移动图谱
                    </span>
                  </div>
                  <div>
                    缩放: 鼠标滚轮 • 重置: 双击背景
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

export default withAuth(GraphPage, [
  { resource: "documents", action: "read" }
]);