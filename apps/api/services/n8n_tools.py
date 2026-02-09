"""
n8n 自动化集成工具
通过 Webhook 调用 n8n 工作流，实现企业级自动化
"""

import os
import httpx
from typing import Dict, Any
from datetime import datetime

class N8nToolManager:
    """n8n 工具管理器"""
    
    def __init__(self):
        self.n8n_url = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")
        self.api_key = os.getenv("N8N_API_KEY", "")
        
    async def trigger_workflow(self, workflow_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """触发 n8n 工作流"""
        try:
            headers = {}
            if self.api_key:
                headers["X-N8N-API-KEY"] = self.api_key
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.n8n_url}/{workflow_id}",
                    json=data,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "workflow_id": workflow_id,
                        "result": response.json(),
                        "status_code": response.status_code,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "workflow_id": workflow_id,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "status_code": response.status_code,
                        "timestamp": datetime.now().isoformat()
                    }
                
        except Exception as e:
            return {
                "success": False,
                "workflow_id": workflow_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # 预定义的工作流工具
    async def send_email_notification(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """发送邮件通知"""
        data = {
            "to": to,
            "subject": subject,
            "body": body,
            "timestamp": datetime.now().isoformat()
        }
        return await self.trigger_workflow("send-email", data)
    
    async def create_jira_ticket(self, project: str, summary: str, description: str, 
                                issue_type: str = "Task") -> Dict[str, Any]:
        """创建 Jira 工单"""
        data = {
            "project": project,
            "summary": summary,
            "description": description,
            "issue_type": issue_type,
            "timestamp": datetime.now().isoformat()
        }
        return await self.trigger_workflow("create-jira-ticket", data)
    
    async def query_database(self, query: str, database: str = "default") -> Dict[str, Any]:
        """查询数据库"""
        data = {
            "query": query,
            "database": database,
            "timestamp": datetime.now().isoformat()
        }
        return await self.trigger_workflow("query-database", data)
    
    async def generate_report(self, report_type: str, start_date: str, 
                             end_date: str, format: str = "pdf") -> Dict[str, Any]:
        """生成报告"""
        data = {
            "report_type": report_type,
            "start_date": start_date,
            "end_date": end_date,
            "format": format,
            "timestamp": datetime.now().isoformat()
        }
        return await self.trigger_workflow("generate-report", data)

# 全局 n8n 管理器实例
_n8n_manager = None

def get_n8n_manager() -> N8nToolManager:
    """获取 n8n 管理器实例"""
    global _n8n_manager
    if _n8n_manager is None:
        _n8n_manager = N8nToolManager()
    return _n8n_manager