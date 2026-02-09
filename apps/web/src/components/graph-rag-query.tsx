// components/graph-rag-query.tsx
"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { 
  Search, 
  BrainCircuit, 
  FileText, 
  Network, 
  Users,
  Lightbulb,
  Building,
  Package,
  MapPin,
  Calendar,
  Loader2,
  ExternalLink
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import AuthService from "@/lib/auth";

export function GraphRAGQuery() {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const { toast } = useToast();

  const handleSearch = async () => {
    if (!query.trim()) {
      toast({
        title: "请输入查询内容",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await AuthService.secureFetch("http://localhost:8000/graph/query", {
        method: "POST",
        body: JSON.stringify({ query })
      });

      const data = await response.json();
      setResults(data);
      
      toast({
        title: "查询完成",
        description: `找到 ${data.entities_found?.length || 0} 个相关实体`,
      });
    } catch (error: any) {
      console.error("GraphRAG 查询失败:", error);
      toast({
        title: "查询失败",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const entityIcons: Record<string, React.ReactNode> = {
    "PERSON": <Users className="w-4 h-4" />,
    "ORGANIZATION": <Building className="w-4 h-4" />,
    "CONCEPT": <Lightbulb className="w-4 h-4" />,
    "PRODUCT": <Package className="w-4 h-4" />,
    "LOCATION": <MapPin className="w-4 h-4" />,
    "EVENT": <Calendar className="w-4 h-4" />
  };

  return (
    <div className="space-y-6">
      {/* 查询输入 */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-blue-400" />
            GraphRAG 智能查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-zinc-500" />
              <Input
                placeholder="输入您的问题，系统将结合文档和知识图谱进行深度分析..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="pl-10 h-12 bg-zinc-800 border-zinc-700"
                disabled={isLoading}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <p className="text-sm text-zinc-500">
                支持复杂问题如："谁负责了那个需要用到 pgvector 的项目？"
              </p>
              <Button
                onClick={handleSearch}
                disabled={isLoading || !query.trim()}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    分析中...
                  </>
                ) : (
                  <>
                    <BrainCircuit className="w-4 h-4 mr-2" />
                    智能分析
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 结果展示 */}
      {results && (
        <div className="space-y-6">
          {/* 回答结果 */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg">回答结果</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-invert max-w-none">
                <div className="whitespace-pre-wrap text-zinc-100 leading-relaxed">
                  {results.answer}
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 相关实体 */}
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Network className="w-5 h-5 text-emerald-400" />
                  相关实体 ({results.entities_found?.length || 0})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  <div className="space-y-3">
                    {results.entities_found?.slice(0, 10).map((entity: string, index: number) => {
                      // 尝试从graph数据中获取实体类型
                      const graphEntity = results.graph?.entities?.find((e: any) => e.name === entity);
                      return (
                        <div key={index} className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                              {graphEntity?.type && entityIcons[graphEntity.type] || 
                               <Network className="w-4 h-4 text-emerald-400" />}
                            </div>
                            <div>
                              <p className="font-medium text-zinc-100">{entity}</p>
                              {graphEntity?.type && (
                                <Badge variant="outline" className="text-xs mt-1 border-transparent bg-zinc-700/50">
                                  {graphEntity.type}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* 相关文档 */}
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-400" />
                  相关文档 ({results.documents?.length || 0})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  <div className="space-y-3">
                    {results.documents?.map((doc: any, index: number) => (
                      <div 
                        key={index} 
                        className="p-3 bg-zinc-800/50 rounded-lg hover:bg-zinc-800/70 cursor-pointer group"
                        onClick={() => window.open(`/documents/${doc.id}`, '_blank')}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium text-zinc-100 group-hover:text-blue-300">
                              {doc.title || `文档 ${doc.id}`}
                            </p>
                            {doc.content && (
                              <p className="text-sm text-zinc-500 mt-2 line-clamp-2">
                                {doc.content.slice(0, 200)}...
                              </p>
                            )}
                          </div>
                          <ExternalLink className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 mt-1" />
                        </div>
                        <div className="flex items-center gap-4 mt-3">
                          {doc.score && (
                            <Badge variant="outline" className="text-xs border-transparent bg-blue-500/10">
                              相关度: {(doc.score * 100).toFixed(0)}%
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* 查询统计 */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardContent className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-zinc-800/30 rounded-lg">
                  <p className="text-sm text-zinc-400">查询类型</p>
                  <p className="text-xl font-bold text-white mt-2">GraphRAG</p>
                </div>
                <div className="text-center p-4 bg-zinc-800/30 rounded-lg">
                  <p className="text-sm text-zinc-400">实体数量</p>
                  <p className="text-xl font-bold text-emerald-400 mt-2">{results.entities_found?.length || 0}</p>
                </div>
                <div className="text-center p-4 bg-zinc-800/30 rounded-lg">
                  <p className="text-sm text-zinc-400">路径发现</p>
                  <p className="text-xl font-bold text-purple-400 mt-2">{results.paths_found || 0}</p>
                </div>
                <div className="text-center p-4 bg-zinc-800/30 rounded-lg">
                  <p className="text-sm text-zinc-400">文档引用</p>
                  <p className="text-xl font-bold text-blue-400 mt-2">{results.documents_used?.length || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}