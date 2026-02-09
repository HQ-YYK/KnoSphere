"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { 
  Search, 
  Filter, 
  Network, 
  Users, 
  Building, 
  Lightbulb, 
  Package, 
  MapPin, 
  Calendar,
  Eye,
  EyeOff,
  RefreshCw,
  ExternalLink
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import AuthService from "@/lib/auth";
import dynamic from "next/dynamic";

// 动态加载 ForceGraph2D 组件，禁用 SSR
const ForceGraph2D = dynamic(
  () => import("react-force-graph-2d"),
  { ssr: false }
);

interface GraphNode {
  id: number;
  name: string;
  type: string;
  description?: string;
  group: number;
  frequency: number;
  confidence: number;
  documents: number;
}

interface GraphLink {
  source: number;
  target: number;
  relation: string;
  weight: number;
  description?: string;
  source_context?: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  stats: {
    total_entities: number;
    total_edges: number;
    entity_types: Record<string, number>;
  };
}

interface EntityDetails {
  entity: {
    id: number;
    name: string;
    type: string;
    description?: string;
    frequency: number;
    confidence: number;
  };
  relationships: {
    outgoing: Array<{
      id: number;
      source_id: number;
      target_id: number;
      relation: string;
      description?: string;
    }>;
    incoming: Array<{
      id: number;
      source_id: number;
      target_id: number;
      relation: string;
      description?: string;
    }>;
    total: number;
  };
  documents: Array<{
    id: number;
    title: string;
    content_preview?: string;
    created_at: string;
  }>;
  stats: {
    document_count: number;
    relationship_count: number;
  };
}

export function KnowledgeGraph() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [], stats: { total_entities: 0, total_edges: 0, entity_types: {} } });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedLink, setSelectedLink] = useState<GraphLink | null>(null);
  const [entityDetails, setEntityDetails] = useState<EntityDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<string | null>(null);
  const [showLabels, setShowLabels] = useState(true);
  const [graphMode, setGraphMode] = useState<"2d" | "3d">("2d");
  const [highlightNodes, setHighlightNodes] = useState(new Set<number>());
  const [highlightLinks, setHighlightLinks] = useState(new Set<number>());
  const graphRef = useRef<any>();

  const router = useRouter();
  const { toast } = useToast();
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [selectedDocPreview, setSelectedDocPreview] = useState<any>(null);
  const [showDocumentSheet, setShowDocumentSheet] = useState(false);

  // 颜色映射
  const nodeColors: Record<string, string> = {
    "PERSON": "#3b82f6",     // 蓝色
    "ORGANIZATION": "#10b981", // 绿色
    "CONCEPT": "#8b5cf6",    // 紫色
    "PRODUCT": "#f59e0b",    // 黄色
    "LOCATION": "#ef4444",   // 红色
    "EVENT": "#ec4899"       // 粉色
  };

  // 图标映射
  const nodeIcons: Record<string, React.ReactNode> = {
    "PERSON": <Users className="w-3 h-3" />,
    "ORGANIZATION": <Building className="w-3 h-3" />,
    "CONCEPT": <Lightbulb className="w-3 h-3" />,
    "PRODUCT": <Package className="w-3 h-3" />,
    "LOCATION": <MapPin className="w-3 h-3" />,
    "EVENT": <Calendar className="w-3 h-3" />
  };

  // 加载图谱数据
  const loadGraphData = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await AuthService.secureFetch("http://localhost:8000/graph/data");
      const data = await response.json();
      setGraphData(data);
    } catch (error) {
      console.error("加载图谱数据失败:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 加载实体详情
  const loadEntityDetails = useCallback(async (entityId: number) => {
    try {
      const response = await AuthService.secureFetch(`http://localhost:8000/graph/entity/${entityId}`);
      const data = await response.json();
      setEntityDetails(data);
    } catch (error) {
      console.error("加载实体详情失败:", error);
    }
  }, []);

  // 初始加载
  useEffect(() => {
    loadGraphData();
  }, [loadGraphData]);

  // 添加加载文档预览的函数
  const loadDocumentPreview = async (docId: number) => {
    try {
      const response = await AuthService.secureFetch(
        `http://localhost:8000/documents/${docId}`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setSelectedDocPreview(data);
      setShowDocumentSheet(true);
    } catch (error: any) {
      console.error("加载文档预览失败:", error);
      toast({
        title: "加载失败",
        description: error.message,
        variant: "destructive"
      });
    }
  };


  // 节点点击处理
  const handleNodeClick = useCallback((node: any) => {
    // 如果是文档节点，直接跳转
    if (node.is_document) {
      router.push(`/documents/${node.document_id}`);
      return;
    }
    
    setSelectedNode(node);
    
    // 如果有主要文档，显示文档预览
    if (node.primary_doc_id) {
      setSelectedDocId(node.primary_doc_id);
      loadDocumentPreview(node.primary_doc_id);
    } else {
      // 否则显示实体详情
      loadEntityDetails(node.id);
    }
    
    // 高亮相关节点和边
    const connectedNodeIds = new Set<number>();
    const connectedLinkIndexes = new Set<number>();
    
    graphData.links.forEach((link: any, index: number) => {
      if (link.source === node.id || link.target === node.id) {
        connectedLinkIndexes.add(index);
        if (link.source === node.id) connectedNodeIds.add(link.target);
        if (link.target === node.id) connectedNodeIds.add(link.source);
      }
    });
    
    setHighlightNodes(connectedNodeIds);
    setHighlightLinks(connectedLinkIndexes);
    
    // 自动聚焦到节点
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 1000);
      graphRef.current.zoom(2, 1000);
    }
  }, [graphData, loadEntityDetails, router]);

  // 在节点的 Tooltip 中添加文档信息
  const getNodeTooltip = useCallback((node: any) => {
    let tooltip = `<strong>${node.name}</strong><br/>`;
    tooltip += `<small class="text-zinc-400">${node.type}</small><br/>`;
    
    if (node.documents && node.documents.length > 0) {
      tooltip += `<hr class="my-1 border-zinc-700"/>`;
      tooltip += `<small class="text-zinc-300">关联文档:</small><br/>`;
      node.documents.slice(0, 3).forEach((doc: any) => {
        tooltip += `<small class="text-zinc-400">• ${doc.title}</small><br/>`;
      });
      if (node.documents.length > 3) {
        tooltip += `<small class="text-zinc-500">...还有${node.documents.length - 3}个</small>`;
      }
    }
    
    return tooltip;
  }, []);

  // 边点击处理
  const handleLinkClick = useCallback((link: GraphLink) => {
    setSelectedLink(link);
    setSelectedNode(null);
    setEntityDetails(null);
    
    // 高亮相关节点
    const connectedNodes = new Set<number>();
    connectedNodes.add(link.source);
    connectedNodes.add(link.target);
    setHighlightNodes(connectedNodes);
    
    // 高亮相关边
    const connectedLinks = new Set<number>();
    graphData.links.forEach((l, index) => {
      if (l.source === link.source || l.source === link.target || 
          l.target === link.source || l.target === link.target) {
        connectedLinks.add(index);
      }
    });
    setHighlightLinks(connectedLinks);
  }, [graphData]);

  // 背景点击处理
  const handleBackgroundClick = () => {
    setSelectedNode(null);
    setSelectedLink(null);
    setEntityDetails(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
    
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 50);
    }
  };

  // 过滤数据
  const filteredNodes = graphData.nodes.filter(node => {
    if (filterType && node.type !== filterType) return false;
    if (searchQuery && !node.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const filteredLinks = graphData.links.filter(link => {
    const sourceNode = graphData.nodes.find(n => n.id === link.source);
    const targetNode = graphData.nodes.find(n => n.id === link.target);
    return sourceNode && targetNode && 
           filteredNodes.includes(sourceNode) && 
           filteredNodes.includes(targetNode);
  });

  // 绘制自定义节点
  const paintNode = useCallback((node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const size = 5 + Math.log(node.frequency || 1) * 2;
    const color = nodeColors[node.type] || "#6b7280";
    
    // 绘制节点圆
    ctx.beginPath();
    ctx.arc(node.x!, node.y!, size, 0, 2 * Math.PI, false);
    ctx.fillStyle = selectedNode?.id === node.id ? "#ffffff" : 
                    highlightNodes.has(node.id) ? "#fbbf24" : color;
    ctx.fill();
    
    // 绘制边框
    ctx.strokeStyle = selectedNode?.id === node.id ? "#000000" : "#ffffff";
    ctx.lineWidth = 1 / globalScale;
    ctx.stroke();
    
    // 绘制标签
    if (showLabels && globalScale > 0.5) {
      const fontSize = 12 / globalScale;
      ctx.font = `${fontSize}px Sans-Serif`;
      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(node.name, node.x!, node.y! + size + fontSize);
    }
  }, [selectedNode, highlightNodes, showLabels]);

  // 绘制自定义边
  const paintLink = useCallback((link: GraphLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const sourceNode = graphData.nodes.find(n => n.id === link.source);
    const targetNode = graphData.nodes.find(n => n.id === link.target);
    
    if (!sourceNode || !targetNode) return;
    
    // 计算线条宽度
    const lineWidth = Math.max(1 / globalScale, link.weight * 3);
    
    // 线条颜色
    const isHighlighted = selectedLink === link || highlightLinks.has(
      graphData.links.findIndex(l => l === link)
    );
    const color = isHighlighted ? "#fbbf24" : "#4b5563";
    
    // 绘制线条
    ctx.beginPath();
    ctx.moveTo(sourceNode.x!, sourceNode.y!);
    ctx.lineTo(targetNode.x!, targetNode.y!);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
    
    // 绘制关系标签
    if (showLabels && globalScale > 0.8) {
      const midX = (sourceNode.x! + targetNode.x!) / 2;
      const midY = (sourceNode.y! + targetNode.y!) / 2;
      
      const fontSize = 10 / globalScale;
      ctx.font = `${fontSize}px Sans-Serif`;
      ctx.fillStyle = "#d1d5db";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      
      // 背景框
      const textWidth = ctx.measureText(link.relation).width;
      const padding = 2 / globalScale;
      ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
      ctx.fillRect(
        midX - textWidth / 2 - padding,
        midY - fontSize / 2 - padding,
        textWidth + padding * 2,
        fontSize + padding * 2
      );
      
      // 文字
      ctx.fillStyle = "#ffffff";
      ctx.fillText(link.relation, midX, midY);
    }
  }, [graphData, selectedLink, highlightLinks, showLabels]);

  if (isLoading) {
    return (
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardContent className="h-[600px] flex items-center justify-center">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 mb-4">
              <Network className="w-6 h-6 text-white animate-pulse" />
            </div>
            <p className="text-zinc-400">加载知识图谱中...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-400">实体总数</p>
                <p className="text-2xl font-bold text-white">{graphData.stats.total_entities}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                <Network className="w-5 h-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-400">关系总数</p>
                <p className="text-2xl font-bold text-white">{graphData.stats.total_edges}</p>
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
                <p className="text-sm text-zinc-400">人物实体</p>
                <p className="text-2xl font-bold text-white">{graphData.stats.entity_types.PERSON || 0}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                <Users className="w-5 h-5 text-green-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-400">组织实体</p>
                <p className="text-2xl font-bold text-white">{graphData.stats.entity_types.ORGANIZATION || 0}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                <Building className="w-5 h-5 text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：控制面板 */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg">图谱控制</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 搜索 */}
              <div>
                <label className="text-sm text-zinc-400 mb-2 block">搜索实体</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-500" />
                  <Input
                    placeholder="输入实体名称..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 bg-zinc-800 border-zinc-700"
                  />
                </div>
              </div>
              
              {/* 实体类型过滤 */}
              <div>
                <label className="text-sm text-zinc-400 mb-2 block">实体类型</label>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant={filterType === null ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterType(null)}
                    className="bg-zinc-800 hover:bg-zinc-700"
                  >
                    全部
                  </Button>
                  {Object.entries(graphData.stats.entity_types).map(([type, count]) => (
                    <Button
                      key={type}
                      variant={filterType === type ? "default" : "outline"}
                      size="sm"
                      onClick={() => setFilterType(filterType === type ? null : type)}
                      className="bg-zinc-800 hover:bg-zinc-700"
                    >
                      <span className="mr-2">{nodeIcons[type] || <Network className="w-3 h-3" />}</span>
                      {type} ({count})
                    </Button>
                  ))}
                </div>
              </div>
              
              {/* 显示选项 */}
              <div>
                <label className="text-sm text-zinc-400 mb-2 block">显示选项</label>
                <div className="flex gap-2">
                  <Button
                    variant={showLabels ? "default" : "outline"}
                    size="sm"
                    onClick={() => setShowLabels(!showLabels)}
                    className="flex-1 bg-zinc-800 hover:bg-zinc-700"
                  >
                    {showLabels ? <Eye className="w-4 h-4 mr-2" /> : <EyeOff className="w-4 h-4 mr-2" />}
                    {showLabels ? "隐藏标签" : "显示标签"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={loadGraphData}
                    className="bg-zinc-800 hover:bg-zinc-700"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              
              {/* 图例 */}
              <div>
                <label className="text-sm text-zinc-400 mb-2 block">图例</label>
                <div className="space-y-2">
                  {Object.entries(nodeColors).map(([type, color]) => (
                    <div key={type} className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-sm text-zinc-300">{type}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
          
          {/* 选中实体详情 */}
          {selectedNode && entityDetails && (
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: nodeColors[selectedNode.type] }} />
                  {selectedNode.name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-zinc-400">类型</p>
                  <Badge variant="outline" className="mt-1 border-transparent" style={{ 
                    backgroundColor: `${nodeColors[selectedNode.type]}20`,
                    color: nodeColors[selectedNode.type]
                  }}>
                    {nodeIcons[selectedNode.type]}
                    <span className="ml-1">{selectedNode.type}</span>
                  </Badge>
                </div>
                
                {selectedNode.description && (
                  <div>
                    <p className="text-sm text-zinc-400">描述</p>
                    <p className="text-sm text-zinc-300 mt-1">{selectedNode.description}</p>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-zinc-400">出现频率</p>
                    <p className="text-lg font-bold text-white">{selectedNode.frequency}</p>
                  </div>
                  <div>
                    <p className="text-sm text-zinc-400">置信度</p>
                    <p className="text-lg font-bold text-white">{(selectedNode.confidence * 100).toFixed(0)}%</p>
                  </div>
                </div>
                
                {/* 关系 */}
                <div>
                  <p className="text-sm text-zinc-400">关系 ({entityDetails.relationships.total})</p>
                  <ScrollArea className="h-32 mt-2">
                    <div className="space-y-2">
                      {entityDetails.relationships.outgoing.map((rel) => {
                        const targetEntity = graphData.nodes.find(n => n.id === rel.target_id);
                        return (
                          <div key={rel.id} className="text-sm bg-zinc-800/50 rounded p-2">
                            <div className="flex items-center justify-between">
                              <span className="text-zinc-300">{rel.relation}</span>
                              <Badge variant="outline" size="sm" className="text-xs">
                                出向
                              </Badge>
                            </div>
                            <div className="text-zinc-500 text-xs mt-1">
                              目标: {targetEntity?.name || rel.target_id}
                            </div>
                          </div>
                        );
                      })}
                      {entityDetails.relationships.incoming.map((rel) => {
                        const sourceEntity = graphData.nodes.find(n => n.id === rel.source_id);
                        return (
                          <div key={rel.id} className="text-sm bg-zinc-800/50 rounded p-2">
                            <div className="flex items-center justify-between">
                              <span className="text-zinc-300">{rel.relation}</span>
                              <Badge variant="outline" size="sm" className="text-xs">
                                入向
                              </Badge>
                            </div>
                            <div className="text-zinc-500 text-xs mt-1">
                              来源: {sourceEntity?.name || rel.source_id}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </ScrollArea>
                </div>
                
                {/* 相关文档 */}
                {entityDetails.documents.length > 0 && (
                  <div>
                    <p className="text-sm text-zinc-400">相关文档 ({entityDetails.documents.length})</p>
                    <ScrollArea className="h-32 mt-2">
                      <div className="space-y-2">
                        {entityDetails.documents.map((doc) => (
                          <div 
                            key={doc.id} 
                            className="text-sm bg-zinc-800/50 rounded p-2 hover:bg-zinc-800/70 cursor-pointer"
                            onClick={() => window.open(`/documents/${doc.id}`, '_blank')}
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-zinc-300 truncate">{doc.title}</span>
                              <ExternalLink className="w-3 h-3 text-zinc-500" />
                            </div>
                            <div className="text-zinc-500 text-xs mt-1 truncate">
                              {doc.content_preview}
                            </div>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
        
        {/* 右侧：图谱可视化 */}
        <div className="lg:col-span-2">
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">知识图谱可视化</CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="border-emerald-500/30 text-emerald-300">
                    {filteredNodes.length} 节点, {filteredLinks.length} 边
                  </Badge>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleBackgroundClick}
                    className="bg-zinc-800 hover:bg-zinc-700"
                  >
                    重置视图
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[600px] rounded-lg overflow-hidden border border-zinc-800">
                {filteredNodes.length === 0 ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center">
                      <Network className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
                      <p className="text-zinc-500">没有找到匹配的实体</p>
                      <p className="text-sm text-zinc-600 mt-2">尝试调整搜索条件或过滤类型</p>
                    </div>
                  </div>
                ) : (
                  <ForceGraph2D
                    ref={graphRef}
                    graphData={{ nodes: filteredNodes, links: filteredLinks }}
                    nodeLabel={getNodeTooltip}
                    nodeAutoColorBy="type"
                    linkLabel="relation"
                    linkWidth={1}
                    linkDirectionalArrowLength={3}
                    linkDirectionalArrowRelPos={1}
                    nodeCanvasObject={paintNode}
                    linkCanvasObject={paintLink}
                    onNodeClick={handleNodeClick}
                    onLinkClick={handleLinkClick}
                    onBackgroundClick={handleBackgroundClick}
                    backgroundColor="#0a0a0a"
                    cooldownTicks={100}
                    warmupTicks={50}
                  />
                )}
              </div>
              
              {/* 提示信息 */}
              <div className="mt-4 text-sm text-zinc-500 flex items-center justify-between">
                <div>
                  <span className="inline-flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                    点击节点查看详情
                  </span>
                  <span className="mx-4">•</span>
                  <span className="inline-flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                    拖拽节点进行探索
                  </span>
                </div>
                <div>
                  缩放: 鼠标滚轮 • 移动: 拖拽背景
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 添加文档预览侧边栏 */}
      <Sheet open={showDocumentSheet} onOpenChange={setShowDocumentSheet}>
        <SheetContent className="w-full sm:max-w-2xl bg-zinc-950 border-l border-zinc-800 overflow-y-auto">
          <SheetHeader className="mb-6">
            <SheetTitle className="text-xl">
              {selectedDocPreview?.document?.title || "文档预览"}
            </SheetTitle>
            <p className="text-sm text-zinc-500">
              点击"查看完整文档"以查看更多详情
            </p>
          </SheetHeader>
          
          {selectedDocPreview ? (
            <div className="space-y-6">
              {/* 文档基本信息 */}
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardContent className="p-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-zinc-400">文档大小</span>
                      <span className="text-sm text-zinc-300">
                        {(selectedDocPreview.stats.content_length / 1024).toFixed(1)} KB
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-zinc-400">实体数量</span>
                      <span className="text-sm text-emerald-300">
                        {selectedDocPreview.stats.entity_count}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-zinc-400">关系数量</span>
                      <span className="text-sm text-purple-300">
                        {selectedDocPreview.stats.relation_count}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              {/* 文档内容预览 */}
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardContent className="p-4">
                  <h4 className="font-medium text-zinc-100 mb-3">内容预览</h4>
                  <ScrollArea className="h-64">
                    <div className="prose prose-invert max-w-none">
                      <div className="text-sm text-zinc-300 whitespace-pre-wrap">
                        {selectedDocPreview.document.content?.slice(0, 1000) || "无内容"}
                        {selectedDocPreview.document.content?.length > 1000 && "..."}
                      </div>
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
              
              {/* 实体列表 */}
              {selectedDocPreview.entities.length > 0 && (
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardContent className="p-4">
                    <h4 className="font-medium text-zinc-100 mb-3">主要实体</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedDocPreview.entities.slice(0, 10).map((entity: any) => (
                        <Badge
                          key={entity.id}
                          variant="outline"
                          className={`cursor-pointer hover:opacity-80 ${
                            entityColors[entity.type]?.split(" ")[0] || "text-zinc-400"
                          } ${
                            entityColors[entity.type]?.split(" ")[1] || "bg-zinc-800/50"
                          }`}
                          onClick={() => {
                            setShowDocumentSheet(false);
                            // 在这里可以跳转到实体的详情或者高亮实体
                          }}
                        >
                          {entityIcons[entity.type]}
                          <span className="ml-1">{entity.name}</span>
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
              
              {/* 操作按钮 */}
              <div className="flex gap-3">
                <Button
                  onClick={() => router.push(`/documents/${selectedDocId}`)}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  查看完整文档
                </Button>
                <Button
                  onClick={() => {
                    setShowDocumentSheet(false);
                    router.push(`/graph?document=${selectedDocId}`);
                  }}
                  variant="outline"
                  className="border-zinc-700 hover:bg-zinc-800"
                >
                  <Network className="w-4 h-4 mr-2" />
                  查看图谱
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-zinc-600 animate-spin mx-auto mb-4" />
                <p className="text-zinc-500">加载文档预览中...</p>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}