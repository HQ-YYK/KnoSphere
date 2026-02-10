// components/document-preview.tsx
"use client";

import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loader2, FileText, Calendar, User, ExternalLink, ChevronRight, Globe } from "lucide-react";
import AuthService from "@/lib/auth";
import { format } from "date-fns";
import { zhCN } from "date-fns/locale";

interface DocumentPreviewProps {
  documentId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface DocumentData {
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
  entities?: Array<{
    id: number;
    name: string;
    type: string;
    frequency: number;
  }>;
  related_documents?: Array<{
    id: number;
    title: string;
    similarity: number;
  }>;
}

export function DocumentPreview({ documentId, open, onOpenChange }: DocumentPreviewProps) {
  const [document, setDocument] = useState<DocumentData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"content" | "entities" | "related">("content");

  useEffect(() => {
    if (documentId && open) {
      loadDocument(documentId);
    }
  }, [documentId, open]);

  const loadDocument = async (id: number) => {
    setIsLoading(true);
    try {
      const response = await AuthService.secureFetch(`http://localhost:8000/documents/${id}`);
      const data = await response.json();
      setDocument(data);
    } catch (error) {
      console.error("加载文档失败:", error);
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

  const handleOpenDocument = () => {
    if (document?.id) {
      window.open(`/documents/${document.id}`, "_blank");
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-2xl bg-zinc-950 border-l border-zinc-800">
        <SheetHeader className="mb-6">
          <SheetTitle className="text-xl flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-400" />
            文档预览
          </SheetTitle>
          <SheetDescription className="text-zinc-400">
            查看实体相关的原始文档内容
          </SheetDescription>
        </SheetHeader>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin text-blue-400 mx-auto mb-4" />
              <p className="text-zinc-400">加载文档中...</p>
            </div>
          </div>
        ) : document ? (
          <div className="space-y-6">
            {/* 文档标题和元信息 */}
            <div>
              <h2 className="text-lg font-semibold text-zinc-100 mb-2">{document.title}</h2>
              <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-500">
                <div className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  <span>创建: {formatDate(document.created_at)}</span>
                </div>
                {document.updated_at && (
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    <span>更新: {formatDate(document.updated_at)}</span>
                  </div>
                )}
                <div className="flex items-center gap-1">
                  <User className="w-3 h-3" />
                  <span>{document.user_name || `用户 ${document.user_id}`}</span>
                </div>
                {document.graph_extracted && (
                  <Badge variant="outline" className="border-emerald-500/30 text-emerald-300">
                    <Globe className="w-3 h-3 mr-1" />
                    已提取图谱
                  </Badge>
                )}
              </div>
            </div>

            {/* 标签页 */}
            <div className="border-b border-zinc-800">
              <nav className="flex space-x-2">
                <button
                  onClick={() => setActiveTab("content")}
                  className={`px-3 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                    activeTab === "content"
                      ? "bg-zinc-800 text-zinc-100 border-b-2 border-blue-500"
                      : "text-zinc-400 hover:text-zinc-300"
                  }`}
                >
                  内容预览
                </button>
                <button
                  onClick={() => setActiveTab("entities")}
                  className={`px-3 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                    activeTab === "entities"
                      ? "bg-zinc-800 text-zinc-100 border-b-2 border-purple-500"
                      : "text-zinc-400 hover:text-zinc-300"
                  }`}
                >
                  实体 ({document.entities?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("related")}
                  className={`px-3 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                    activeTab === "related"
                      ? "bg-zinc-800 text-zinc-100 border-b-2 border-emerald-500"
                      : "text-zinc-400 hover:text-zinc-300"
                  }`}
                >
                  相关文档
                </button>
              </nav>
            </div>

            {/* 标签页内容 */}
            <ScrollArea className="h-[calc(100vh-300px)]">
              {activeTab === "content" && (
                <div className="prose prose-invert max-w-none">
                  <div className="whitespace-pre-wrap text-zinc-300 leading-relaxed p-4 bg-zinc-900/50 rounded-lg">
                    {document.content}
                  </div>
                </div>
              )}

              {activeTab === "entities" && (
                <div className="space-y-3">
                  {document.entities && document.entities.length > 0 ? (
                    document.entities.map((entity) => (
                      <div
                        key={entity.id}
                        className="flex items-center justify-between p-3 bg-zinc-900/50 rounded-lg hover:bg-zinc-900/70 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
                            <Globe className="w-4 h-4 text-blue-400" />
                          </div>
                          <div>
                            <div className="font-medium text-zinc-100">{entity.name}</div>
                            <div className="text-sm text-zinc-400 flex items-center gap-2 mt-1">
                              <Badge variant="outline" className="text-xs border-transparent bg-zinc-800">
                                {entity.type}
                              </Badge>
                              <span>出现 {entity.frequency} 次</span>
                            </div>
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-zinc-600" />
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-zinc-500">
                      <Globe className="w-12 h-12 mx-auto mb-4 text-zinc-700" />
                      <p>该文档暂无提取的实体</p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "related" && (
                <div className="space-y-3">
                  {document.related_documents && document.related_documents.length > 0 ? (
                    document.related_documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between p-3 bg-zinc-900/50 rounded-lg hover:bg-zinc-900/70 transition-colors cursor-pointer"
                        onClick={() => window.open(`/documents/${doc.id}`, "_blank")}
                      >
                        <div className="flex-1">
                          <div className="font-medium text-zinc-100">{doc.title}</div>
                          <div className="text-sm text-zinc-400 mt-1">
                            相关度: {(doc.similarity * 100).toFixed(1)}%
                          </div>
                        </div>
                        <ExternalLink className="w-4 h-4 text-zinc-600" />
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-zinc-500">
                      <FileText className="w-12 h-12 mx-auto mb-4 text-zinc-700" />
                      <p>暂无相关文档</p>
                    </div>
                  )}
                </div>
              )}
            </ScrollArea>

            {/* 操作按钮 */}
            <div className="pt-4 border-t border-zinc-800">
              <div className="flex items-center justify-between">
                <div className="text-sm text-zinc-500">
                  <span className="text-zinc-300">{document.content.length}</span> 字符
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onOpenChange(false)}
                    className="border-zinc-700 hover:bg-zinc-800"
                  >
                    关闭
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleOpenDocument}
                    className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  >
                    打开完整文档
                  </Button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-zinc-500">
            <FileText className="w-16 h-16 mx-auto mb-4 text-zinc-700" />
            <p>未找到文档或文档已删除</p>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}