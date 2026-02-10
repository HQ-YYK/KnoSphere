"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Activity, 
  TrendingUp, 
  AlertCircle, 
  Clock, 
  DollarSign, 
  Users,
  Server,
  Database,
  Network,
  RefreshCw,
  Download,
  Eye,
  Filter
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import AuthService from "@/lib/auth";

interface PerformanceMetrics {
  ttft: {
    count: number;
    avg_ms: number;
    p95_ms: number;
    p99_ms: number;
    max_ms: number;
    threshold_exceeded: number;
  };
  latency_by_operation: Record<string, any>;
  error_rates: Record<string, any>;
  health: {
    status: string;
    checks: Record<string, any>;
    timestamp: string;
  };
  timestamp: string;
}

interface CostMetrics {
  summary: {
    total_requests: number;
    total_tokens: number;
    total_cost: number;
    avg_cost_per_request: number;
  };
  by_user: Record<string, any>;
  by_model: Record<string, any>;
  time_range: {
    start: string;
    end: string;
  };
}

export function MonitoringDashboard() {
  const [performanceData, setPerformanceData] = useState<PerformanceMetrics | null>(null);
  const [costData, setCostData] = useState<CostMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<"1h" | "24h" | "7d" | "30d">("24h");
  const [activeTab, setActiveTab] = useState<"performance" | "cost" | "health">("performance");
  const { toast } = useToast();

  const loadMetrics = async () => {
    setIsLoading(true);
    try {
      // 加载性能指标
      const perfResponse = await AuthService.secureFetch(
        `http://localhost:8000/monitoring/performance?hours=${
          timeRange === "1h" ? 1 : timeRange === "24h" ? 24 : timeRange === "7d" ? 168 : 720
        }`
      );
      const perfData = await perfResponse.json();
      setPerformanceData(perfData);

      // 加载成本指标
      const costResponse = await AuthService.secureFetch("http://localhost:8000/monitoring/cost");
      const costData = await costResponse.json();
      setCostData(costData);

    } catch (error: any) {
      console.error("加载监控数据失败:", error);
      toast({
        title: "加载失败",
        description: error.message || "无法加载监控数据",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, [timeRange]);

  const getHealthColor = (status: string) => {
    switch (status) {
      case "healthy": return "bg-emerald-500";
      case "degraded": return "bg-amber-500";
      case "critical": return "bg-red-500";
      default: return "bg-zinc-500";
    }
  };

  const formatCost = (cost: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4
    }).format(cost);
  };

  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  if (isLoading) {
    return (
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardContent className="h-64 flex items-center justify-center">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 animate-spin text-blue-400 mx-auto mb-4" />
            <p className="text-zinc-400">加载监控数据中...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* 时间范围和标签页控制 */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-400" />
                <h3 className="font-semibold text-zinc-100">系统监控仪表板</h3>
              </div>
              
              <div className="flex gap-1">
                <Button
                  variant={activeTab === "performance" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setActiveTab("performance")}
                  className="bg-zinc-800 hover:bg-zinc-700"
                >
                  <TrendingUp className="w-3 h-3 mr-2" />
                  性能
                </Button>
                <Button
                  variant={activeTab === "cost" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setActiveTab("cost")}
                  className="bg-zinc-800 hover:bg-zinc-700"
                >
                  <DollarSign className="w-3 h-3 mr-2" />
                  成本
                </Button>
                <Button
                  variant={activeTab === "health" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setActiveTab("health")}
                  className="bg-zinc-800 hover:bg-zinc-700"
                >
                  <Server className="w-3 h-3 mr-2" />
                  健康
                </Button>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="flex gap-1">
                {["1h", "24h", "7d", "30d"].map((range) => (
                  <Button
                    key={range}
                    variant={timeRange === range ? "default" : "outline"}
                    size="sm"
                    onClick={() => setTimeRange(range as any)}
                    className="bg-zinc-800 hover:bg-zinc-700"
                  >
                    {range}
                  </Button>
                ))}
              </div>
              
              <Button
                variant="outline"
                size="sm"
                onClick={loadMetrics}
                className="bg-zinc-800 hover:bg-zinc-700"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 性能标签页 */}
      {activeTab === "performance" && performanceData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 关键指标 */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-400" />
                响应时间
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">平均 TTFT</span>
                  <span className="text-zinc-100">{formatTime(performanceData.ttft.avg_ms)}</span>
                </div>
                <Progress 
                  value={Math.min(100, (performanceData.ttft.avg_ms / 2000) * 100)} 
                  className="h-2"
                />
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">P95 TTFT</span>
                  <span className="text-zinc-100">{formatTime(performanceData.ttft.p95_ms)}</span>
                </div>
                <Progress 
                  value={Math.min(100, (performanceData.ttft.p95_ms / 2000) * 100)} 
                  className="h-2"
                />
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">阈值超标</span>
                  <span className="text-zinc-100">{performanceData.ttft.threshold_exceeded} 次</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 操作延迟 */}
          <Card className="bg-zinc-900/50 border-zinc-800 lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Network className="w-5 h-5 text-purple-400" />
                操作延迟
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-64">
                <div className="space-y-4">
                  {Object.entries(performanceData.latency_by_operation).map(([operation, data]: [string, any]) => (
                    <div key={operation} className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-zinc-400">{operation}</span>
                        <span className="text-zinc-100">{formatTime(data.avg_ms)}</span>
                      </div>
                      <Progress 
                        value={Math.min(100, (data.avg_ms / 1000) * 100)} 
                        className="h-1"
                      />
                      <div className="flex justify-between text-xs text-zinc-500">
                        <span>请求数: {data.count}</span>
                        <span>P95: {formatTime(data.p95_ms)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* 错误率 */}
          <Card className="bg-zinc-900/50 border-zinc-800 lg:col-span-3">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-red-400" />
                错误率监控
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(performanceData.error_rates).map(([operation, data]: [string, any]) => (
                  <div key={operation} className="bg-zinc-800/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-zinc-300 truncate">{operation}</span>
                      <Badge 
                        variant="outline" 
                        className={`text-xs ${
                          data.error_rate > 0.05 
                            ? "border-red-500/30 text-red-400" 
                            : "border-emerald-500/30 text-emerald-400"
                        }`}
                      >
                        {(data.error_rate * 100).toFixed(1)}%
                      </Badge>
                    </div>
                    <div className="text-xs text-zinc-500 space-y-1">
                      <div className="flex justify-between">
                        <span>总请求</span>
                        <span>{data.total_requests}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>错误数</span>
                        <span className="text-red-400">{data.errors}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 成本标签页 */}
      {activeTab === "cost" && costData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 成本概览 */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-400" />
                成本概览
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-emerald-400 mb-2">
                  {formatCost(costData.summary.total_cost)}
                </div>
                <div className="text-sm text-zinc-500">总成本</div>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">总请求数</span>
                  <span className="text-zinc-100">{costData.summary.total_requests}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">总 Token 数</span>
                  <span className="text-zinc-100">{costData.summary.total_tokens.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">平均每次请求成本</span>
                  <span className="text-zinc-100">{formatCost(costData.summary.avg_cost_per_request)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 按用户成本 */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-400" />
                用户成本分布
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-64">
                <div className="space-y-3">
                  {Object.entries(costData.by_user).map(([userId, data]: [string, any]) => (
                    <div key={userId} className="flex items-center justify-between p-3 bg-zinc-800/30 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
                          <Users className="w-4 h-4 text-blue-400" />
                        </div>
                        <div>
                          <div className="font-medium text-zinc-100">用户 {userId}</div>
                          <div className="text-xs text-zinc-400">{data.requests} 次请求</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-medium text-zinc-100">{formatCost(data.total_cost)}</div>
                        <div className="text-xs text-zinc-400">{data.total_tokens.toLocaleString()} tokens</div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* 按模型成本 */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Database className="w-5 h-5 text-purple-400" />
                模型成本分析
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(costData.by_model).map(([model, data]: [string, any]) => (
                  <div key={model} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-400 truncate">{model}</span>
                      <span className="text-zinc-100">{formatCost(data.total_cost)}</span>
                    </div>
                    <Progress 
                      value={(data.total_cost / costData.summary.total_cost) * 100} 
                      className="h-2"
                    />
                    <div className="flex justify-between text-xs text-zinc-500">
                      <span>{data.requests} 次请求</span>
                      <span>{data.total_tokens.toLocaleString()} tokens</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 健康标签页 */}
      {activeTab === "health" && performanceData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 系统健康状态 */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Server className="w-5 h-5 text-amber-400" />
                系统健康状态
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`inline-flex items-center px-4 py-2 rounded-full mb-6 ${
                performanceData.health.status === "healthy" ? "bg-emerald-500/20 text-emerald-400" :
                performanceData.health.status === "degraded" ? "bg-amber-500/20 text-amber-400" :
                "bg-red-500/20 text-red-400"
              }`}>
                <div className={`w-3 h-3 rounded-full mr-2 ${getHealthColor(performanceData.health.status)}`}></div>
                <span className="font-medium capitalize">{performanceData.health.status}</span>
              </div>
              
              <div className="space-y-4">
                {Object.entries(performanceData.health.checks).map(([checkName, check]: [string, any]) => (
                  <div key={checkName} className="flex items-center justify-between p-3 bg-zinc-800/30 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${getHealthColor(check.status)}`}></div>
                      <div>
                        <div className="text-sm text-zinc-100">{checkName.replace(/_/g, ' ')}</div>
                        <div className="text-xs text-zinc-400">
                          {checkName.includes('ttft') ? formatTime(check.value) : `${(check.value * 100).toFixed(1)}%`}
                        </div>
                      </div>
                    </div>
                    <Badge 
                      variant="outline" 
                      className={`text-xs ${
                        check.status === "healthy" ? "border-emerald-500/30 text-emerald-400" :
                        check.status === "degraded" ? "border-amber-500/30 text-amber-400" :
                        "border-red-500/30 text-red-400"
                      }`}
                    >
                      {check.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 健康检查历史 */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-400" />
                监控信息
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-zinc-800/30 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Eye className="w-4 h-4 text-blue-400" />
                    <div>
                      <div className="text-sm text-zinc-100">LangSmith 监控</div>
                      <div className="text-xs text-zinc-400">全链路追踪</div>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-emerald-500/30 text-emerald-400">
                    已启用
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-zinc-800/30 rounded-lg">
                  <div className="flex items-center gap-3">
                    <DollarSign className="w-4 h-4 text-emerald-400" />
                    <div>
                      <div className="text-sm text-zinc-100">成本监控</div>
                      <div className="text-xs text-zinc-400">实时 Token 消耗</div>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-emerald-500/30 text-emerald-400">
                    已启用
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-zinc-800/30 rounded-lg">
                  <div className="flex items-center gap-3">
                    <AlertCircle className="w-4 h-4 text-amber-400" />
                    <div>
                      <div className="text-sm text-zinc-100">自动评估</div>
                      <div className="text-xs text-zinc-400">质量与幻觉检测</div>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-emerald-500/30 text-emerald-400">
                    已启用
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-zinc-800/30 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Clock className="w-4 h-4 text-purple-400" />
                    <div>
                      <div className="text-sm text-zinc-100">性能监控</div>
                      <div className="text-xs text-zinc-400">TTFT 与延迟跟踪</div>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-emerald-500/30 text-emerald-400">
                    已启用
                  </Badge>
                </div>
              </div>
              
              <div className="mt-6 pt-4 border-t border-zinc-800">
                <div className="text-xs text-zinc-500 space-y-1">
                  <div className="flex justify-between">
                    <span>最后更新</span>
                    <span>{new Date(performanceData.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>监控项目</span>
                    <span>KnoSphere-Production-2026</span>
                  </div>
                  <div className="flex justify-between">
                    <span>数据覆盖</span>
                    <span>{timeRange}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}