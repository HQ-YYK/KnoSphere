"""
KnoSphere 技能插件系统
让 AI 从聊天机器人进化为能够执行实际任务的多模态代理
"""

from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import DuckDuckGoSearchResults
import os
import json
import httpx
from datetime import datetime
from typing import Dict, Any, List
import asyncio
from urllib.parse import quote_plus

# ==================== 网络搜索工具 ====================

@tool
async def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    使用 Tavily AI 搜索网络信息
    
    参数:
    - query: 搜索关键词
    - max_results: 返回结果数量
    """
    try:
        # 检查 API 密钥
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "未配置 TAVILY_API_KEY 环境变量",
                "results": []
            }
        
        # 创建搜索客户端
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        
        # 执行搜索
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",  # basic 或 advanced
            include_answer=True,      # 包含AI生成的答案摘要
            include_raw_content=True  # 包含原始内容
        )
        
        # 格式化结果
        results = []
        if response.get("results"):
            for result in response["results"]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0.0),
                    "published_date": result.get("published_date"),
                    "source": "tavily"
                })
        
        # 如果有AI生成的答案，添加到结果中
        if response.get("answer"):
            results.insert(0, {
                "title": "AI 答案摘要",
                "url": "",
                "content": response["answer"],
                "score": 1.0,
                "source": "tavily_ai"
            })
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": []
        }

@tool
async def duckduckgo_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    使用 DuckDuckGo 进行匿名搜索（备选方案）
    """
    try:
        from duckduckgo_search import DDGS
        
        results = []
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "content": result.get("body", ""),
                    "source": "duckduckgo"
                })
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": []
        }

# ==================== 天气查询工具 ====================

@tool
async def get_weather(city: str = None, lat: float = None, lon: float = None) -> Dict[str, Any]:
    """
    查询指定城市或位置的实时天气情况
    
    参数:
    - city: 城市名称（中文或英文）
    - lat: 纬度
    - lon: 经度
    
    优先使用城市名称，如果未提供则使用经纬度
    """
    try:
        # 如果没有提供城市或坐标，使用默认位置
        if not city and (lat is None or lon is None):
            city = "北京"  # 默认城市
        
        # 如果提供了城市名称，先获取坐标
        if city:
            # 使用 Open-Meteo 的地理编码API
            geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote_plus(city)}&count=1"
            
            async with httpx.AsyncClient() as client:
                geocode_response = await client.get(geocode_url)
                geocode_data = geocode_response.json()
                
                if geocode_data.get("results"):
                    location = geocode_data["results"][0]
                    lat = location["latitude"]
                    lon = location["longitude"]
                    city = location["name"]
                else:
                    # 如果找不到城市，使用默认坐标（北京）
                    lat = 39.9042
                    lon = 116.4074
        
        # 获取天气数据
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"current=temperature_2m,relative_humidity_2m,apparent_temperature,"
            f"precipitation,rain,showers,snowfall,weather_code,cloud_cover,"
            f"wind_speed_10m,wind_direction_10m,wind_gusts_10m&"
            f"timezone=auto&forecast_days=1"
        )
        
        async with httpx.AsyncClient() as client:
            weather_response = await client.get(weather_url)
            weather_data = weather_response.json()
        
        # 解析天气代码
        weather_codes = {
            0: "晴朗",
            1: "主要晴朗",
            2: "部分多云",
            3: "多云",
            45: "有雾",
            48: "有雾",
            51: "小雨",
            53: "中等雨",
            55: "大雨",
            56: "冻雨",
            57: "冻雨",
            61: "小雨",
            63: "中等雨",
            65: "大雨",
            66: "冻雨",
            67: "冻雨",
            71: "小雪",
            73: "中等雪",
            75: "大雪",
            77: "雪粒",
            80: "小雨",
            81: "中等雨",
            82: "大雨",
            85: "小雪",
            86: "大雪",
            95: "雷暴",
            96: "雷暴伴小冰雹",
            99: "雷暴伴大冰雹"
        }
        
        current = weather_data.get("current", {})
        weather_code = current.get("weather_code", 0)
        weather_desc = weather_codes.get(weather_code, "未知")
        
        # 构建天气信息
        weather_info = {
            "success": True,
            "location": {
                "city": city or f"纬度{lat}, 经度{lon}",
                "latitude": lat,
                "longitude": lon,
                "timezone": weather_data.get("timezone", "未知")
            },
            "current": {
                "temperature": f"{current.get('temperature_2m', 0)}°C",
                "feels_like": f"{current.get('apparent_temperature', 0)}°C",
                "humidity": f"{current.get('relative_humidity_2m', 0)}%",
                "weather": weather_desc,
                "weather_code": weather_code,
                "precipitation": f"{current.get('precipitation', 0)}mm",
                "rain": f"{current.get('rain', 0)}mm",
                "showers": f"{current.get('showers', 0)}mm",
                "snowfall": f"{current.get('snowfall', 0)}cm",
                "cloud_cover": f"{current.get('cloud_cover', 0)}%",
                "wind_speed": f"{current.get('wind_speed_10m', 0)}km/h",
                "wind_direction": current.get("wind_direction_10m", 0),
                "wind_gusts": f"{current.get('wind_gusts_10m', 0)}km/h",
                "time": current.get("time", datetime.now().isoformat())
            },
            "recommendation": _get_weather_recommendation(weather_desc, current.get("temperature_2m", 0)),
            "timestamp": datetime.now().isoformat()
        }
        
        return weather_info
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "location": city or f"纬度{lat}, 经度{lon}",
            "timestamp": datetime.now().isoformat()
        }

def _get_weather_recommendation(weather: str, temperature: float) -> str:
    """根据天气和温度生成建议"""
    recommendations = []
    
    if temperature < 0:
        recommendations.append("天气寒冷，请注意保暖，穿戴厚外套、帽子、围巾和手套。")
    elif temperature < 10:
        recommendations.append("天气较冷，建议穿厚外套或羽绒服。")
    elif temperature < 20:
        recommendations.append("天气凉爽，建议穿薄外套或长袖衣服。")
    elif temperature < 30:
        recommendations.append("天气温暖，建议穿短袖或薄衣服。")
    else:
        recommendations.append("天气炎热，请注意防暑降温，多喝水。")
    
    if "雨" in weather:
        recommendations.append("有雨，请携带雨具。")
    if "雪" in weather:
        recommendations.append("有雪，请注意防滑。")
    if "雷暴" in weather:
        recommendations.append("有雷暴，请注意安全，避免户外活动。")
    if "雾" in weather:
        recommendations.append("有雾，能见度低，请注意交通安全。")
    
    if not recommendations:
        recommendations.append("天气适宜，适合户外活动。")
    
    return " ".join(recommendations)

# ==================== 计算器工具 ====================

@tool
async def calculate(expression: str) -> Dict[str, Any]:
    """
    执行数学计算
    
    支持：加减乘除、幂运算、三角函数、对数等
    示例：calculate("(3 + 4) * 2 / 5")
    """
    try:
        # 安全检查：防止执行任意代码
        allowed_chars = set("0123456789+-*/().^!%πe ")
        allowed_functions = ["sin", "cos", "tan", "log", "ln", "sqrt", "abs"]
        
        # 清理表达式
        expr = expression.strip().lower()
        
        # 检查安全性
        for char in expr:
            if char not in allowed_chars and not any(func in expr for func in allowed_functions):
                raise ValueError(f"表达式中包含不安全字符: {char}")
        
        # 替换数学常数
        expr = expr.replace("π", "3.141592653589793").replace("pi", "3.141592653589793")
        expr = expr.replace("e", "2.718281828459045")
        
        # 执行计算（使用eval但要限制）
        # 在实际生产环境中，应该使用更安全的计算库如sympy
        import math
        
        # 定义安全的环境
        safe_globals = {
            "__builtins__": {},
            "math": math,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log10,
            "ln": math.log,
            "sqrt": math.sqrt,
            "abs": abs,
            "pow": pow
        }
        
        result = eval(expr, {"__builtins__": None}, safe_globals)
        
        return {
            "success": True,
            "expression": expression,
            "result": result,
            "formatted": f"{expression} = {result}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "expression": expression,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== 时间工具 ====================

@tool
async def get_current_time(timezone: str = "Asia/Shanghai") -> Dict[str, Any]:
    """
    获取当前时间
    
    参数:
    - timezone: 时区名称，默认Asia/Shanghai
    """
    try:
        from datetime import datetime
        import pytz
        
        # 获取时区
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        
        return {
            "success": True,
            "timezone": timezone,
            "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "day_of_week": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][current_time.weekday()],
            "week_number": current_time.isocalendar()[1],
            "timestamp": current_time.isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "timezone": timezone,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== 单位转换工具 ====================

@tool
async def convert_units(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """
    单位转换工具
    
    支持：长度、重量、温度、速度、时间等
    示例：convert_units(100, "km", "mile")
    """
    try:
        # 定义转换因子
        conversions = {
            # 长度
            "m": {"km": 0.001, "cm": 100, "mm": 1000, "mile": 0.000621371, "yard": 1.09361},
            "km": {"m": 1000, "mile": 0.621371, "yard": 1093.61},
            "cm": {"m": 0.01, "inch": 0.393701},
            "inch": {"cm": 2.54, "m": 0.0254},
            "mile": {"km": 1.60934, "m": 1609.34},
            # 重量
            "kg": {"g": 1000, "lb": 2.20462},
            "g": {"kg": 0.001, "lb": 0.00220462},
            "lb": {"kg": 0.453592, "g": 453.592},
            # 温度（需要特殊处理）
            "celsius": {"fahrenheit": lambda x: x * 9/5 + 32},
            "fahrenheit": {"celsius": lambda x: (x - 32) * 5/9},
            # 速度
            "km/h": {"m/s": 0.277778, "mph": 0.621371},
            "m/s": {"km/h": 3.6, "mph": 2.23694},
            "mph": {"km/h": 1.60934, "m/s": 0.44704},
            # 时间
            "hour": {"minute": 60, "second": 3600},
            "minute": {"hour": 1/60, "second": 60},
            "second": {"hour": 1/3600, "minute": 1/60}
        }
        
        # 检查单位是否支持
        if from_unit not in conversions or to_unit not in conversions.get(from_unit, {}):
            # 尝试反转
            if to_unit in conversions and from_unit in conversions.get(to_unit, {}):
                # 交换单位
                from_unit, to_unit = to_unit, from_unit
                value = 1 / value
            else:
                raise ValueError(f"不支持从 {from_unit} 转换到 {to_unit}")
        
        # 温度转换需要特殊处理
        if from_unit in ["celsius", "fahrenheit"]:
            converter = conversions[from_unit][to_unit]
            result = converter(value)
        else:
            factor = conversions[from_unit][to_unit]
            result = value * factor
        
        return {
            "success": True,
            "original": f"{value} {from_unit}",
            "converted": f"{result:.4f} {to_unit}",
            "value": result,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "original": f"{value} {from_unit}",
            "target_unit": to_unit,
            "timestamp": datetime.now().isoformat()
        }

# ==================== 货币转换工具 ====================

@tool
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    """
    货币转换工具
    
    使用免费汇率API
    """
    try:
        # 使用 ExchangeRate-API
        api_key = os.getenv("EXCHANGERATE_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "未配置 EXCHANGERATE_API_KEY 环境变量",
                "suggestion": "请从 https://exchangerate-api.com/ 获取免费API密钥"
            }
        
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{from_currency.upper()}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()
        
        if data.get("result") != "success":
            raise ValueError(f"汇率API错误: {data.get('error-type', 'unknown')}")
        
        rates = data.get("conversion_rates", {})
        if to_currency.upper() not in rates:
            raise ValueError(f"不支持的目标货币: {to_currency}")
        
        rate = rates[to_currency.upper()]
        result = amount * rate
        
        return {
            "success": True,
            "amount": amount,
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "exchange_rate": rate,
            "result": result,
            "formatted": f"{amount} {from_currency.upper()} = {result:.2f} {to_currency.upper()}",
            "timestamp": datetime.now().isoformat(),
            "last_updated": data.get("time_last_update_utc", "")
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "timestamp": datetime.now().isoformat()
        }

# ==================== 工具管理器 ====================

class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        self.tools = {
            "web_search": web_search,
            "duckduckgo_search": duckduckgo_search,
            "get_weather": get_weather,
            "calculate": calculate,
            "get_current_time": get_current_time,
            "convert_units": convert_units,
            "convert_currency": convert_currency
        }
    
    def get_tools_list(self) -> List:
        """获取工具列表"""
        return list(self.tools.values())
    
    def get_tool_by_name(self, name: str):
        """根据名称获取工具"""
        return self.tools.get(name)
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        tool = self.get_tool_by_name(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"未找到工具: {tool_name}",
                "available_tools": list(self.tools.keys())
            }
        
        try:
            result = await tool.ainvoke(kwargs)
            return {
                "success": True,
                "tool": tool_name,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_tools_description(self) -> List[Dict[str, Any]]:
        """获取工具描述"""
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append({
                "name": name,
                "description": tool.description,
                "args": tool.args_schema.schema() if hasattr(tool, 'args_schema') else {}
            })
        return descriptions

# 全局工具管理器实例
_tool_manager = None

def get_tool_manager() -> ToolManager:
    """获取工具管理器实例"""
    global _tool_manager
    if _tool_manager is None:
        _tool_manager = ToolManager()
    return _tool_manager