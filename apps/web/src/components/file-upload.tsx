"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { 
  Loader2, 
  UploadCloud, 
  CheckCircle, 
  AlertCircle,
  FileText,
  Clock
} from "lucide-react";

interface UploadTask {
  task_id: string;
  document_id: number;
  filename: string;
  file_size_mb: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  stage?: string;
  details?: string;
  created_at: Date;
}

export function FileUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadTasks, setUploadTasks] = useState<UploadTask[]>([]);
  const { toast } = useToast();

  // 轮询任务状态
  useEffect(() => {
    if (uploadTasks.some(task => task.status === 'processing' || task.status === 'pending')) {
      const interval = setInterval(() => {
        updateTaskStatuses();
      }, 3000); // 每3秒更新一次状态
      
      return () => clearInterval(interval);
    }
  }, [uploadTasks]);

  async function updateTaskStatuses() {
    for (const task of uploadTasks) {
      if (task.status === 'processing' || task.status === 'pending') {
        try {
          const response = await fetch(`http://localhost:8000/task/status/${task.task_id}`);
          const data = await response.json();
          
          setUploadTasks(prev => prev.map(t => 
            t.task_id === task.task_id ? {
              ...t,
              status: data.status.toLowerCase(),
              progress: data.progress || 0,
              stage: data.stage || t.stage,
              details: data.details || t.details
            } : t
          ));
          
          // 如果任务完成，显示通知
          if (data.status === 'SUCCESS' && task.status !== 'completed') {
            toast({
              title: "🎉 处理完成",
              description: `${task.filename} 已成功向量化并存储`,
            });
          } else if (data.status === 'FAILURE' && task.status !== 'failed') {
            toast({
              title: "❌ 处理失败",
              description: `${task.filename} 处理失败: ${data.error}`,
              variant: "destructive"
            });
          }
        } catch (error) {
          console.error("更新任务状态失败:", error);
        }
      }
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      // 创建任务记录
      const task: UploadTask = {
        task_id: `temp_${Date.now()}_${i}`,
        document_id: 0,
        filename: file.name,
        file_size_mb: file.size / (1024 * 1024),
        status: 'pending',
        created_at: new Date()
      };
      
      setUploadTasks(prev => [...prev, task]);
      
      try {
        // 准备 FormData
        const formData = new FormData();
        formData.append("file", file);
        
        // 发送上传请求
        const response = await fetch("http://localhost:8000/upload/async", {
          method: "POST",
          body: formData,
        });
        
        const result = await response.json();
        
        if (response.ok) {
          // 更新任务信息
          setUploadTasks(prev => prev.map(t => 
            t.task_id === task.task_id ? {
              ...t,
              task_id: result.task_id,
              document_id: result.document_id,
              status: 'processing',
              stage: '排队中'
            } : t
          ));
          
          toast({
            title: "📤 上传成功",
            description: `${file.name} 已进入处理队列`,
          });
        } else {
          throw new Error(result.detail || "上传失败");
        }
      } catch (error: any) {
        setUploadTasks(prev => prev.map(t => 
          t.task_id === task.task_id ? {
            ...t,
            status: 'failed',
            details: error.message
          } : t
        ));
        
        toast({
          title: "❌ 上传失败",
          description: `${file.name}: ${error.message}`,
          variant: "destructive"
        });
      }
    }
    
    setIsUploading(false);
    event.target.value = ""; // 重置文件输入
  }

  function getStatusIcon(status: UploadTask['status']) {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-amber-500" />;
    }
  }

  function getStatusColor(status: UploadTask['status']) {
    switch (status) {
      case 'completed':
        return "bg-emerald-500/10 text-emerald-300 border-emerald-500/30";
      case 'processing':
        return "bg-blue-500/10 text-blue-300 border-blue-500/30";
      case 'failed':
        return "bg-red-500/10 text-red-300 border-red-500/30";
      default:
        return "bg-amber-500/10 text-amber-300 border-amber-500/30";
    }
  }

  return (
    <div className="space-y-6">
      {/* 上传区域 */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-xl flex items-center gap-2">
            <UploadCloud className="w-5 h-5" />
            文档上传
          </CardTitle>
          <p className="text-zinc-400 text-sm">
            支持 PDF、DOCX、TXT、MD 格式，大文件将自动进入后台处理
          </p>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-6 p-8 border-2 border-dashed border-zinc-800 rounded-xl bg-zinc-900/30 hover:border-blue-500/50 transition-all">
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
                {isUploading ? "上传中..." : "上传文档"}
              </h3>
              <p className="text-sm text-zinc-400">
                拖放文件到此处或点击选择
              </p>
              <p className="text-xs text-zinc-500">
                支持批量上传，大文件将自动进入后台异步处理
              </p>
            </div>
            
            <div className="relative">
              <Input
                type="file"
                className="absolute inset-0 opacity-0 cursor-pointer z-10"
                onChange={handleUpload}
                disabled={isUploading}
                accept=".txt,.md,.pdf,.docx"
                multiple
              />
              <Button 
                variant="default" 
                disabled={isUploading}
                className="relative bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-700 hover:to-emerald-700 text-white px-6 py-3 rounded-lg font-medium"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    上传中...
                  </>
                ) : (
                  <>
                    <UploadCloud className="mr-2 h-4 w-4" />
                    选择文件
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* 任务列表 */}
      {uploadTasks.length > 0 && (
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-xl flex items-center gap-2">
              <FileText className="w-5 h-5" />
              处理任务
              <Badge variant="outline" className="ml-2">
                {uploadTasks.length} 个
              </Badge>
            </CardTitle>
            <p className="text-zinc-400 text-sm">
              文档正在后台处理，您可以继续其他操作
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {uploadTasks.map((task) => (
                <div key={task.task_id} className="border border-zinc-800 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(task.status)}
                      <div>
                        <h4 className="font-medium text-zinc-100">
                          {task.filename}
                        </h4>
                        <p className="text-xs text-zinc-500">
                          {task.file_size_mb.toFixed(2)} MB • {task.created_at.toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline" className={getStatusColor(task.status)}>
                      {task.status === 'pending' && '排队中'}
                      {task.status === 'processing' && '处理中'}
                      {task.status === 'completed' && '已完成'}
                      {task.status === 'failed' && '失败'}
                    </Badge>
                  </div>
                  
                  {task.status === 'processing' && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-zinc-400">{task.stage}</span>
                        <span className="text-zinc-300">{task.progress}%</span>
                      </div>
                      <Progress value={task.progress} className="h-2" />
                      {task.details && (
                        <p className="text-xs text-zinc-500">{task.details}</p>
                      )}
                    </div>
                  )}
                  
                  {task.status === 'completed' && (
                    <div className="text-sm text-emerald-400 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4" />
                      已成功向量化并存储到知识库
                    </div>
                  )}
                  
                  {task.status === 'failed' && (
                    <div className="text-sm text-red-400 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" />
                      {task.details || "处理失败"}
                    </div>
                  )}
                </div>
              ))}
            </div>
            
            {uploadTasks.some(t => t.status === 'processing') && (
              <div className="mt-4 text-center">
                <p className="text-sm text-zinc-500">
                  🔄 自动更新处理进度...
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}