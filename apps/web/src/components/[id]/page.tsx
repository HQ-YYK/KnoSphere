"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { withAuth } from "@/contexts/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  ArrowLeft, 
  FileText, 
  Calendar, 
  User, 
  BrainCircuit,
  Network,
  Hash,
  Clock,
  Eye,
  Download,
  ExternalLink,
  Users,
  Building,
  Lightbulb,
  Package,
  MapPin,
  Calendar as CalendarIcon
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import AuthService from "@/lib/auth";

interface DocumentDetail {
  document: {
    id: number;
    title: string;
    content: string;
    created_at: string;
    updated_at: string;
    user_id: number;
    embedding: string;
    graph_extracted: boolean;
  };
  entities: Array<{
    id: number;
    name: string;
    type: string;
    frequency_in_doc: number;
    significance: number;
  }>;
  relations: Array<{
    id: number;
    source_id: number;
    target_id: number;
    relation: string;
    description?: string;
    weight: number;
  }>;
  stats: {
    content_length: number;
    entity_count: number;
    relation_count: number;
    embedding_status: string;
    graph_extracted: string;
    graph_extraction_time?: string;
  };
  preview_contexts: Array<{
    entity: string;
    context: string;
    position: number;
  }>;
}

function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  
  const [documentData, setDocumentData] = useState<DocumentDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"content" | "entities" | "relations">("content");
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  
  const documentId = params.id as string;

  useEffect(() => {
    loadDocument();
  }, [documentId]);

  const loadDocument = async () => {
    setIsLoading(true);
    try {
      const response = await AuthService.secureFetch(
        `http://localhost:8000/documents/${documentId}`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setDocumentData(data);
    } catch (error: any) {
      console.error("加载文档失败:", error);
      toast({
        title: "加载失败",
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
    "EVENT": <CalendarIcon className="w-4 h-4" />
  };

  const entityColors: Record<string, string> = {
    "PERSON": "text-blue-400 bg-blue-500/10",
    "ORGANIZATION": "text-emerald-400 bg-emerald-500/10",
    "CONCEPT": "text-purple-400 bg-purple-500/10",
    "PRODUCT": "text-amber-400 bg-amber-500/10",
    "LOCATION": "text-red-400 bg-red-500/10",
    "EVENT": "text-pink-400 bg-pink-500/10"
  };

  const navigateToGraph = () => {
    router.push(`/graph?document=${documentId}`);
  };

  const navigateToEntity = (entityId: number) => {
    router.push(`/graph?entity=${entityId}`);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-50 p-8">
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="h-[400px] flex items-center justify-center">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 mb-4 animate-pulse">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <p className="text-zinc-400">加载文档详情中...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!documentData) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-50 p-8">
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="h-[400px] flex items-center justify-center">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-red-500 to-orange-500 mb-4">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <p className="text-zinc-400">文档不存在或无权访问</p>
              <Button 
                onClick={() => router.push("/")}
                className="mt-4 bg-zinc-800 hover:bg-zinc-700"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                返回首页
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { document: doc, entities, relations, stats, preview_contexts } = documentData;

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
                <h1 className="text-lg font-semibold text-zinc-100 line-clamp-1">
                  {doc.title}
                </h1>
                <p className="text-xs text-zinc-500">文档详情</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Button
                onClick={navigateToGraph}
                variant="outline"
                size="sm"
                className="border-zinc-700 hover:bg-zinc-800"
              >
                <Network className="w-4 h-4 mr-2" />
                查看知识图谱
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* 主要内容 */}
      <div className="max-w-7xl mx-auto p-4 md:p-8">
        <div className="space-y-6">
          {/* 文档统计卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-400">文档大小</p>
                    <p className="text-xl font-bold text-white">
                      {(stats.content_length / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-blue-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-400">实体数量</p>
                    <p className="text-xl font-bold text-emerald-400">
                      {stats.entity_count}
                    </p>
                  </div>
                  <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                    <BrainCircuit className="w-5 h-5 text-emerald-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-400">关系数量</p>
                    <p className="text-xl font-bold text-purple-400">
                      {stats.relation_count}
                    </p>
                  </div>
                  <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                    <Network className="w-5 h-5 text-purple-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-400">知识图谱</p>
                    <p className="text-xl font-bold text-amber-400">
                      {stats.graph_extracted}
                    </p>
                  </div>
                  <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                    <Hash className="w-5 h-5 text-amber-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 元数据 */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <Calendar className="w-4 h-4" />
                    创建时间
                  </div>
                  <p className="text-zinc-200">
                    {new Date(doc.created_at).toLocaleString("zh-CN")}
                  </p>
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <Clock className="w-4 h-4" />
                    更新时间
                  </div>
                  <p className="text-zinc-200">
                    {new Date(doc.updated_at).toLocaleString("zh-CN")}
                  </p>
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <User className="w-4 h-4" />
                    所属用户
                  </div>
                  <p className="text-zinc-200">ID: {doc.user_id}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 标签页 */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>文档内容分析</CardTitle>
                <div className="flex items-center gap-2">
                  <Button
                    variant={activeTab === "content" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setActiveTab("content")}
                    className={activeTab === "content" 
                      ? "bg-blue-600 hover:bg-blue-700" 
                      : "bg-zinc-800 hover:bg-zinc-700"
                    }
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    内容
                  </Button>
                  <Button
                    variant={activeTab === "entities" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setActiveTab("entities")}
                    className={activeTab === "entities" 
                      ? "bg-emerald-600 hover:bg-emerald-700" 
                      : "bg-zinc-800 hover:bg-zinc-700"
                    }
                  >
                    <BrainCircuit className="w-4 h-4 mr-2" />
                    实体 ({entities.length})
                  </Button>
                  <Button
                    variant={activeTab === "relations" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setActiveTab("relations")}
                    className={activeTab === "relations" 
                      ? "bg-purple-600 hover:bg-purple-700" 
                      : "bg-zinc-800 hover:bg-zinc-700"
                    }
                  >
                    <Network className="w-4 h-4 mr-2" />
                    关系 ({relations.length})
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {activeTab === "content" && (
                <div className="space-y-6">
                  {/* 文档内容 */}
                  <ScrollArea className="h-[500px] rounded-lg bg-zinc-900/30 p-6 border border-zinc-800">
                    <div className="prose prose-invert max-w-none">
                      <div className="whitespace-pre-wrap text-zinc-300 leading-relaxed">
                        {doc.content}
                      </div>
                    </div>
                  </ScrollArea>
                  
                  {/* 实体上下文 */}
                  {preview_contexts.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold text-zinc-100 mb-4">
                        实体出现位置
                      </h3>
                      <div className="space-y-3">
                        {preview_contexts.map((context, idx) => (
                          <Card key={idx} className="bg-zinc-900/30 border-zinc-800">
                            <CardContent className="p-4">
                              <div className="flex items-start gap-3">
                                <Badge 
                                  variant="outline" 
                                  className="border-transparent bg-blue-500/10 text-blue-300"
                                >
                                  {context.entity}
                                </Badge>
                                <div className="flex-1">
                                  <div 
                                    className="text-sm text-zinc-400"
                                    dangerouslySetInnerHTML={{ 
                                      __html: context.context.replace(/\*\*(.*?)\*\*/g, '<span class="text-blue-400 font-semibold">$1</span>')
                                    }}
                                  />
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {activeTab === "entities" && (
                <div>
                  <div className="mb-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {entities.map((entity) => (
                      <Card 
                        key={entity.id}
                        className={`bg-zinc-900/30 border-zinc-800 hover:bg-zinc-900/50 transition-colors cursor-pointer ${
                          selectedEntity === entity.name ? "ring-2 ring-blue-500" : ""
                        }`}
                        onClick={() => {
                          setSelectedEntity(entity.name === selectedEntity ? null : entity.name);
                          navigateToEntity(entity.id);
                        }}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start gap-3">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                              entityColors[entity.type]?.split(" ")[1] || "bg-zinc-800"
                            }`}>
                              {entityIcons[entity.type] || <BrainCircuit className="w-5 h-5" />}
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center justify-between">
                                <h4 className="font-medium text-zinc-100">{entity.name}</h4>
                                <Badge 
                                  variant="outline" 
                                  className={`text-xs border-transparent ${
                                    entityColors[entity.type]?.split(" ")[0] || "text-zinc-400"
                                  } ${
                                    entityColors[entity.type]?.split(" ")[1] || "bg-zinc-800/50"
                                  }`}
                                >
                                  {entity.type}
                                </Badge>
                              </div>
                              <div className="mt-2 flex items-center justify-between text-sm">
                                <div className="flex items-center gap-4">
                                  <span className="text-zinc-500">
                                    出现: {entity.frequency_in_doc} 次
                                  </span>
                                  <span className="text-zinc-500">
                                    相关度: {(entity.significance * 100).toFixed(0)}%
                                  </span>
                                </div>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-6 px-2 text-zinc-500 hover:text-zinc-300"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigateToEntity(entity.id);
                                  }}
                                >
                                  <ExternalLink className="w-3 h-3" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                  
                  {selectedEntity && (
                    <div className="mt-6">
                      <Card className="bg-zinc-900/30 border-zinc-800">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="font-medium text-zinc-100">
                              选中实体: {selectedEntity}
                            </h4>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => navigateToEntity(
                                entities.find(e => e.name === selectedEntity)?.id || 0
                              )}
                              className="border-zinc-700 hover:bg-zinc-800"
                            >
                              查看知识图谱
                            </Button>
                          </div>
                          <p className="text-sm text-zinc-400">
                            该实体在此文档中出现 {entities.find(e => e.name === selectedEntity)?.frequency_in_doc} 次，
                            相关度为 {(entities.find(e => e.name === selectedEntity)?.significance || 0) * 100}%。
                            点击上方按钮可在知识图谱中查看该实体的详细信息。
                          </p>
                        </CardContent>
                      </Card>
                    </div>
                  )}
                </div>
              )}
              
              {activeTab === "relations" && (
                <div>
                  {relations.length === 0 ? (
                    <div className="text-center py-12">
                      <Network className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
                      <p className="text-zinc-500">此文档尚未提取出关系</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {relations.map((relation) => {
                        const sourceEntity = entities.find(e => e.id === relation.source_id);
                        const targetEntity = entities.find(e => e.id === relation.target_id);
                        
                        return (
                          <Card key={relation.id} className="bg-zinc-900/30 border-zinc-800">
                            <CardContent className="p-4">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <Badge 
                                    variant="outline" 
                                    className={`border-transparent ${
                                      entityColors[sourceEntity?.type || ""]?.split(" ")[1] || "bg-zinc-800/50"
                                    }`}
                                  >
                                    {sourceEntity?.name || `ID: ${relation.source_id}`}
                                  </Badge>
                                  <span className="text-zinc-500 mx-2">→</span>
                                  <Badge 
                                    variant="outline" 
                                    className={`border-transparent ${
                                      entityColors[targetEntity?.type || ""]?.split(" ")[1] || "bg-zinc-800/50"
                                    }`}
                                  >
                                    {targetEntity?.name || `ID: ${relation.target_id}`}
                                  </Badge>
                                </div>
                                <Badge 
                                  variant="outline" 
                                  className="border-purple-500/30 text-purple-300 bg-purple-500/10"
                                >
                                  {relation.relation}
                                </Badge>
                              </div>
                              
                              {relation.description && (
                                <p className="text-sm text-zinc-400 mt-2">
                                  {relation.description}
                                </p>
                              )}
                              
                              <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
                                <span>权重: {relation.weight.toFixed(2)}</span>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-6 px-2"
                                  onClick={() => navigateToGraph()}
                                >
                                  在图中查看
                                </Button>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default withAuth(DocumentDetailPage, [
  { resource: "documents", action: "read" }
]);