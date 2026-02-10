"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  ArrowLeft, 
  FileText, 
  Calendar, 
  User, 
  Globe, 
  Network, 
  Download,
  Trash2,
  Eye,
  EyeOff,
  Copy
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import AuthService from "@/lib/auth";
import { format } from "date-fns";
import { zhCN } from "date-fns/locale";

interface DocumentDetail {
  id: number;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
  user_id: number;
  user_name?: string;
  embedding: boolean;
  graph_extracted: boolean;
  graph_extraction_time?: string;
  file_name?: string;
  file_size?: number;
  file_type?: string;
  entities?: Array<{
    id: number;
    name: string;
    type: string;
    frequency: number;
    confidence: number;
  }>;
}

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showRawContent, setShowRawContent] = useState(false);
  const [activeTab, setActiveTab] = useState<"content" | "entities" | "info">("content");

  const documentId = params.id as string;

  useEffect(() => {
    if (documentId) {
      loadDocument();
    }
  }, [documentId]);

  const loadDocument = async () => {
    setIsLoading(true);
    try {
      const response = await AuthService.secureFetch(`http://localhost:8000/documents/${documentId}`);
      const data = await response.json();
      setDocument(data);
    } catch (error: any) {
      console.error("加载文档失败:", error);
      toast({
        title: "加载失败",
        description: error.message || "无法加载文档详情",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), "yyyy年MM月dd日 HH:mm", { locale: zhCN });
    } catch {
      return dateString;
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "未知";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "已复制",
      description: "内容已复制到剪贴板",
    });
  };

  const deleteDocument = async () => {
    if (!confirm("确定要删除这个文档吗？此操作不可撤销。")) return;

    try {
      const response = await AuthService.secureFetch(`http://localhost:8000/documents/${documentId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        toast({
          title: "删除成功",
          description: "文档已成功删除",
        });
        router.push("/");
      } else {
        throw new Error("删除失败");
      }
    } catch (error: any) {
      toast({
        title: "删除失败",
        description: error.message || "无法删除文档",
        variant: "destructive"
      });
    }
  };

  const navigateToGraph = () => {
    if (document?.graph_extracted) {
      router.push(`/graph?document=${documentId}`);
    } else {
      toast({
        title: "提示",
        description: "该文档尚未提取知识图谱",
        variant: "default"
      });
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-50 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 mb-4">
                <FileText className="w-6 h-6 text-white animate-pulse" />
              </div>
              <p className="text-zinc-400">加载文档中...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-50 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-12">
            <FileText className="w-16 h-16 text-zinc-700 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-zinc-300 mb-2">文档不存在</h2>
            <p className="text-zinc-500 mb-6">请求的文档可能已被删除或您没有访问权限</p>
            <Button
              onClick={() => router.push("/")}
              className="bg-gradient-to-r from-blue-600 to-purple-600"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回首页
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* 返回按钮 */}
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => router.back()}
            className="text-zinc-400 hover:text-zinc-300"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回
          </Button>
        </div>

        {/* 文档头部 */}
        <Card className="bg-zinc-900/50 border-zinc-800 mb-6">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h1 className="text-2xl font-bold text-zinc-100 mb-2">{document.title}</h1>
                <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-500">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    <span>创建: {formatDate(document.created_at)}</span>
                  </div>
                  {document.updated_at && document.updated_at !== document.created_at && (
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      <span>更新: {formatDate(document.updated_at)}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    <span>{document.user_name || `用户 ${document.user_id}`}</span>
                  </div>
                  {document.file_name && (
                    <div className="flex items-center gap-1">
                      <FileText className="w-3 h-3" />
                      <span>{document.file_name}</span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {document.graph_extracted && (
                  <Badge 
                    variant="outline" 
                    className="border-emerald-500/30 text-emerald-300 cursor-pointer hover:bg-emerald-500/10"
                    onClick={navigateToGraph}
                  >
                    <Globe className="w-3 h-3 mr-1" />
                    已提取图谱
                  </Badge>
                )}
                {document.embedding && (
                  <Badge variant="outline" className="border-blue-500/30 text-blue-300">
                    <Network className="w-3 h-3 mr-1" />
                    已向量化
                  </Badge>
                )}
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex flex-wrap gap-2 pt-4 border-t border-zinc-800">
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(document.content)}
                className="border-zinc-700 hover:bg-zinc-800"
              >
                <Copy className="w-3 h-3 mr-2" />
                复制内容
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRawContent(!showRawContent)}
                className="border-zinc-700 hover:bg-zinc-800"
              >
                {showRawContent ? (
                  <>
                    <EyeOff className="w-3 h-3 mr-2" />
                    隐藏原始格式
                  </>
                ) : (
                  <>
                    <Eye className="w-3 h-3 mr-2" />
                    显示原始格式
                  </>
                )}
              </Button>
              {document.file_name && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    // 下载文件逻辑
                    toast({
                      title: "开发中",
                      description: "文件下载功能即将上线",
                    });
                  }}
                  className="border-zinc-700 hover:bg-zinc-800"
                >
                  <Download className="w-3 h-3 mr-2" />
                  下载原文件
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={deleteDocument}
                className="border-red-500/30 text-red-400 hover:bg-red-500/10"
              >
                <Trash2 className="w-3 h-3 mr-2" />
                删除文档
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：内容区域 */}
          <div className="lg:col-span-2">
            <Card className="bg-zinc-900/50 border-zinc-800 h-full">
              <CardHeader>
                <CardTitle className="text-lg">文档内容</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[calc(100vh-300px)]">
                  <div className={`prose prose-invert max-w-none p-4 ${showRawContent ? 'whitespace-pre-wrap' : ''}`}>
                    {document.content}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* 右侧：信息和实体 */}
          <div className="space-y-6">
            {/* 文档信息 */}
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-400" />
                  文档信息
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-zinc-400">ID</span>
                    <code className="text-zinc-300 font-mono">{document.id}</code>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">字符数</span>
                    <span className="text-zinc-300">{document.content.length}</span>
                  </div>
                  {document.file_size && (
                    <div className="flex justify-between">
                      <span className="text-zinc-400">文件大小</span>
                      <span className="text-zinc-300">{formatFileSize(document.file_size)}</span>
                    </div>
                  )}
                  {document.file_type && (
                    <div className="flex justify-between">
                      <span className="text-zinc-400">文件类型</span>
                      <Badge variant="outline" className="text-xs border-transparent bg-zinc-800">
                        {document.file_type}
                      </Badge>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-zinc-400">向量化</span>
                    <Badge 
                      variant="outline" 
                      className={`text-xs border-transparent ${document.embedding ? 'bg-emerald-500/10 text-emerald-300' : 'bg-zinc-800 text-zinc-400'}`}
                    >
                      {document.embedding ? '已完成' : '未处理'}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">知识图谱</span>
                    <Badge 
                      variant="outline" 
                      className={`text-xs border-transparent ${document.graph_extracted ? 'bg-purple-500/10 text-purple-300' : 'bg-zinc-800 text-zinc-400'}`}
                      onClick={navigateToGraph}
                    >
                      {document.graph_extracted ? '已提取' : '未提取'}
                    </Badge>
                  </div>
                  {document.graph_extraction_time && (
                    <div className="flex justify-between">
                      <span className="text-zinc-400">图谱提取时间</span>
                      <span className="text-zinc-300 text-sm">
                        {formatDate(document.graph_extraction_time)}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* 实体列表 */}
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Globe className="w-5 h-5 text-purple-400" />
                  提取的实体 ({document.entities?.length || 0})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {document.entities && document.entities.length > 0 ? (
                  <ScrollArea className="h-64">
                    <div className="space-y-2">
                      {document.entities.map((entity) => (
                        <div
                          key={entity.id}
                          className="flex items-center justify-between p-3 bg-zinc-800/30 rounded-lg hover:bg-zinc-800/50 transition-colors cursor-pointer"
                          onClick={() => router.push(`/graph?entity=${entity.id}`)}
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500/20 to-blue-500/20 flex items-center justify-center">
                              <Globe className="w-4 h-4 text-purple-400" />
                            </div>
                            <div>
                              <div className="font-medium text-zinc-100">{entity.name}</div>
                              <div className="text-xs text-zinc-400 mt-1 flex items-center gap-2">
                                <Badge variant="outline" className="text-xs border-transparent bg-zinc-700">
                                  {entity.type}
                                </Badge>
                                <span>出现 {entity.frequency} 次</span>
                              </div>
                            </div>
                          </div>
                          <ChevronRight className="w-4 h-4 text-zinc-600" />
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                ) : (
                  <div className="text-center py-8 text-zinc-500">
                    <Globe className="w-12 h-12 mx-auto mb-4 text-zinc-700" />
                    <p>该文档暂无提取的实体</p>
                    <p className="text-sm mt-2">上传文档后会自动提取实体和关系</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}