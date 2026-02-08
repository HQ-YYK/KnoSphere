"use client";

import { useState, useEffect } from "react";
import { 
  BrainCircuit, 
  Search, 
  FileText, 
  MessageSquare, 
  CheckCircle2, 
  AlertCircle,
  Loader2,
  Sparkles,
  Cpu,
  Database,
  Network
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ThinkingStep {
  id: string;
  type: 'status' | 'chunk' | 'error' | 'thinking_start' | 'thinking_end' | 
        'retrieval_start' | 'retrieval_end' | 'generation_start' | 'generation_end' | 'complete';
  data: string;
  stage?: string;
  progress?: number;
  timestamp: string;
  metadata?: Record<string, any>;
}

interface ThinkingProcessProps {
  steps: ThinkingStep[];
  currentProgress?: number;
  isActive?: boolean;
  className?: string;
}

export function ThinkingProcess({ 
  steps, 
  currentProgress = 0, 
  isActive = true,
  className 
}: ThinkingProcessProps) {
  const [activeStep, setActiveStep] = useState(0);
  
  // 获取当前阶段
  const currentStage = steps.length > 0 ? steps[steps.length - 1].stage : 'waiting';
  
  // 获取阶段图标
  const getStageIcon = (stage?: string) => {
    switch (stage) {
      case 'thinking':
        return <BrainCircuit className="w-4 h-4" />;
      case 'analysis':
        return <Cpu className="w-4 h-4" />;
      case 'retrieval':
        return <Search className="w-4 h-4" />;
      case 'embedding':
        return <Network className="w-4 h-4" />;
      case 'vector_search':
        return <Database className="w-4 h-4" />;
      case 'reranking':
        return <Sparkles className="w-4 h-4" />;
      case 'context_preparation':
        return <FileText className="w-4 h-4" />;
      case 'generation':
        return <MessageSquare className="w-4 h-4" />;
      default:
        return <BrainCircuit className="w-4 h-4" />;
    }
  };
  
  // 获取阶段名称
  const getStageName = (stage?: string) => {
    switch (stage) {
      case 'thinking':
        return '思考分析';
      case 'analysis':
        return '查询分析';
      case 'retrieval':
        return '知识检索';
      case 'embedding':
        return '向量化';
      case 'vector_search':
        return '向量搜索';
      case 'reranking':
        return '语义重排';
      case 'context_preparation':
        return '上下文准备';
      case 'generation':
        return '生成回答';
      case 'complete':
        return '完成';
      default:
        return stage || '处理中';
    }
  };
  
  // 获取阶段颜色
  const getStageColor = (stage?: string) => {
    switch (stage) {
      case 'thinking':
      case 'analysis':
        return 'text-blue-500 bg-blue-500/10';
      case 'retrieval':
      case 'embedding':
      case 'vector_search':
        return 'text-purple-500 bg-purple-500/10';
      case 'reranking':
        return 'text-pink-500 bg-pink-500/10';
      case 'context_preparation':
        return 'text-amber-500 bg-amber-500/10';
      case 'generation':
        return 'text-emerald-500 bg-emerald-500/10';
      case 'complete':
        return 'text-green-500 bg-green-500/10';
      case 'error':
        return 'text-red-500 bg-red-500/10';
      default:
        return 'text-zinc-500 bg-zinc-500/10';
    }
  };
  
  // 获取阶段背景色
  const getStageBgColor = (stage?: string) => {
    switch (stage) {
      case 'thinking':
      case 'analysis':
        return 'bg-blue-500/5';
      case 'retrieval':
      case 'embedding':
      case 'vector_search':
        return 'bg-purple-500/5';
      case 'reranking':
        return 'bg-pink-500/5';
      case 'context_preparation':
        return 'bg-amber-500/5';
      case 'generation':
        return 'bg-emerald-500/5';
      case 'complete':
        return 'bg-green-500/5';
      case 'error':
        return 'bg-red-500/5';
      default:
        return 'bg-zinc-500/5';
    }
  };

  // 计算进度
  const calculatedProgress = currentProgress > 0 ? currentProgress : 
    steps.length > 0 ? steps[steps.length - 1].progress || 0 : 0;

  return (
    <Card className={cn("bg-zinc-900/30 border-zinc-800 backdrop-blur-sm", className)}>
      <CardContent className="p-4">
        {/* 头部 - 当前阶段 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              "p-2 rounded-lg",
              getStageBgColor(currentStage)
            )}>
              <div className={getStageColor(currentStage).split(' ')[0]}>
                {getStageIcon(currentStage)}
              </div>
            </div>
            <div>
              <h3 className="font-medium text-zinc-100 flex items-center gap-2">
                <span>KnoSphere 思考中</span>
                {isActive && (
                  <div className="flex gap-1">
                    <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse"></div>
                    <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse delay-150"></div>
                    <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse delay-300"></div>
                  </div>
                )}
              </h3>
              <p className="text-sm text-zinc-400">
                当前阶段: {getStageName(currentStage)}
              </p>
            </div>
          </div>
          
          <Badge variant="outline" className={cn(
            "border-transparent",
            getStageColor(currentStage)
          )}>
            {calculatedProgress}%
          </Badge>
        </div>
        
        {/* 进度条 */}
        <Progress value={calculatedProgress} className="h-2 mb-6" />
        
        {/* 思考步骤 */}
        <div className="space-y-3">
          {steps.map((step, index) => (
            <div 
              key={step.id || index}
              className={cn(
                "flex items-start gap-3 p-3 rounded-lg transition-all duration-300",
                index === steps.length - 1 && isActive 
                  ? "bg-zinc-800/50 border border-zinc-700/50" 
                  : "hover:bg-zinc-800/30"
              )}
            >
              {/* 步骤图标 */}
              <div className="flex-shrink-0 mt-0.5">
                {step.type === 'error' ? (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                ) : step.type === 'complete' ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : step.type === 'chunk' ? (
                  <MessageSquare className="w-4 h-4 text-emerald-500" />
                ) : index === steps.length - 1 && isActive ? (
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-zinc-500" />
                )}
              </div>
              
              {/* 步骤内容 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-zinc-200 truncate">
                    {getStageName(step.stage)}
                  </span>
                  {step.progress && (
                    <span className="text-xs text-zinc-500">
                      {step.progress}%
                    </span>
                  )}
                </div>
                <p className="text-sm text-zinc-400">
                  {step.data}
                </p>
                
                {/* 元数据 */}
                {step.metadata && (
                  <div className="mt-2 space-y-1">
                    {step.metadata.documents_count && (
                      <div className="text-xs text-zinc-500 flex items-center gap-1">
                        <Database className="w-3 h-3" />
                        <span>文档: {step.metadata.documents_count} 篇</span>
                      </div>
                    )}
                    {step.metadata.strategy && (
                      <div className="text-xs text-zinc-500 flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        <span>策略: {step.metadata.strategy}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {/* 时间戳 */}
              <div className="flex-shrink-0">
                <span className="text-xs text-zinc-500">
                  {new Date(step.timestamp).toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit',
                    second: '2-digit'
                  })}
                </span>
              </div>
            </div>
          ))}
        </div>
        
        {/* 底部统计 */}
        {steps.length > 0 && (
          <div className="mt-4 pt-4 border-t border-zinc-800">
            <div className="flex items-center justify-between text-sm">
              <div className="text-zinc-400">
                已执行 {steps.length} 个步骤
              </div>
              <div className="flex items-center gap-4">
                {steps.filter(s => s.type === 'retrieval_start').length > 0 && (
                  <div className="flex items-center gap-1 text-zinc-400">
                    <Search className="w-3 h-3" />
                    <span>检索</span>
                  </div>
                )}
                {steps.filter(s => s.type === 'generation_start').length > 0 && (
                  <div className="flex items-center gap-1 text-zinc-400">
                    <MessageSquare className="w-3 h-3" />
                    <span>生成</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// 思考过程展示器 - 用于显示单个思考过程
interface ThinkingProcessDisplayProps {
  workflowId?: string;
  className?: string;
}

export function ThinkingProcessDisplay({ 
  workflowId,
  className 
}: ThinkingProcessDisplayProps) {
  const [steps, setSteps] = useState<ThinkingStep[]>([]);
  const [isActive, setIsActive] = useState(true);
  
  // 模拟接收思考步骤
  useEffect(() => {
    if (!workflowId) return;
    
    const mockSteps: ThinkingStep[] = [
      {
        id: '1',
        type: 'thinking_start',
        data: '开始分析用户问题',
        stage: 'thinking',
        progress: 0,
        timestamp: new Date(Date.now() - 5000).toISOString(),
        metadata: { query: '人工智能的基本原理' }
      },
      {
        id: '2',
        type: 'retrieval_start',
        data: '正在检索相关知识',
        stage: 'retrieval',
        progress: 20,
        timestamp: new Date(Date.now() - 4000).toISOString(),
        metadata: { strategy: 'balanced', top_k: 10 }
      },
      {
        id: '3',
        type: 'status',
        data: '找到 5 篇相关文档',
        stage: 'retrieval',
        progress: 40,
        timestamp: new Date(Date.now() - 3000).toISOString(),
        metadata: { documents_found: 5 }
      },
      {
        id: '4',
        type: 'generation_start',
        data: '正在生成回答',
        stage: 'generation',
        progress: 60,
        timestamp: new Date(Date.now() - 2000).toISOString()
      },
      {
        id: '5',
        type: 'chunk',
        data: '人工智能是计算机科学的一个分支，旨在创造能够执行通常需要人类智能的任务的机器。',
        stage: 'generation',
        progress: 80,
        timestamp: new Date(Date.now() - 1000).toISOString()
      }
    ];
    
    setSteps(mockSteps);
    
    // 模拟完成
    const timer = setTimeout(() => {
      setSteps(prev => [...prev, {
        id: '6',
        type: 'complete',
        data: '思考完成',
        stage: 'complete',
        progress: 100,
        timestamp: new Date().toISOString()
      }]);
      setIsActive(false);
    }, 3000);
    
    return () => clearTimeout(timer);
  }, [workflowId]);
  
  return (
    <ThinkingProcess
      steps={steps}
      isActive={isActive}
      className={className}
    />
  );
}