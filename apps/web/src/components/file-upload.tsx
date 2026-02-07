"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { Loader2, UploadCloud } from "lucide-react";

export function FileUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const { toast } = useToast();

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    
    // 准备 FormData
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();
      
      if (response.ok) {
        toast({ 
          title: "🎉 上传成功", 
          description: `${file.name} 已转化为向量存入知识库，向量维度：${result.vector_dimensions}维` 
        });
      } else {
        throw new Error(result.detail || "上传失败");
      }
    } catch (error: any) {
      toast({ 
        title: "❌ 出错啦", 
        description: error.message || "无法连接到后端服务器", 
        variant: "destructive" 
      });
    } finally {
      setIsUploading(false);
      // 重置文件输入
      event.target.value = "";
    }
  }

  return (
    <div className="flex flex-col items-center gap-6 p-8 border-2 border-dashed border-zinc-800 rounded-xl bg-zinc-900/50 hover:border-blue-500/50 transition-all duration-300">
      <div className="relative">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500/20 to-emerald-500/20 flex items-center justify-center">
          <UploadCloud className="w-10 h-10 text-blue-400" />
        </div>
        {isUploading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-20 h-20 rounded-full border-4 border-transparent border-t-blue-500 animate-spin"></div>
          </div>
        )}
      </div>
      
      <div className="text-center space-y-2">
        <h3 className="text-lg font-semibold text-zinc-100">
          {isUploading ? "AI 正在思考并向量化..." : "上传知识文档"}
        </h3>
        <p className="text-sm text-zinc-400">
          支持 PDF, DOCX, TXT, MD 等格式
        </p>
        <p className="text-xs text-zinc-500">
          文件将自动转换为 1536 维向量并存储
        </p>
      </div>
      
      <div className="relative">
        <Input
          type="file"
          className="absolute inset-0 opacity-0 cursor-pointer z-10"
          onChange={handleUpload}
          disabled={isUploading}
          accept=".txt,.md,.pdf,.docx"
        />
        <Button 
          variant="default" 
          disabled={isUploading}
          className="relative bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-700 hover:to-emerald-700 text-white px-6 py-3 rounded-lg font-medium transition-all"
        >
          {isUploading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              处理中...
            </>
          ) : (
            <>
              <UploadCloud className="mr-2 h-4 w-4" />
              选择文件并上传
            </>
          )}
        </Button>
      </div>
    </div>
  );
}