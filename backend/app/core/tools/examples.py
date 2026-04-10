"""
测试工具集。

用于测试 Agent 框架的工具示例。
"""

from app.core.tools import register_tool


@register_tool(
    name="calculate",
    description="执行数学计算，支持加减乘除和基本函数",
)
def calculate(expression: str) -> str:
    """计算数学表达式。"""
    try:
        # 安全计算，只允许基本运算
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return f"Error: 表达式包含非法字符"
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@register_tool(
    name="get_weather",
    description="获取指定城市的天气信息",
)
def get_weather(city: str) -> str:
    """获取城市天气。"""
    # 模拟天气数据
    weather_data = {
        "北京": {"weather": "晴", "temperature": "25°C", "humidity": "40%"},
        "上海": {"weather": "多云", "temperature": "28°C", "humidity": "60%"},
        "深圳": {"weather": "雨", "temperature": "24°C", "humidity": "80%"},
    }
    city_weather = weather_data.get(city, {"weather": "未知", "temperature": "N/A", "humidity": "N/A"})
    return f"{city}天气：{city_weather['weather']}，温度：{city_weather['temperature']}，湿度：{city_weather['humidity']}"


@register_tool(
    name="search_info",
    description="搜索信息，返回相关结果",
)
def search_info(keyword: str, category: str = "general") -> str:
    """搜索信息。"""
    # 模拟搜索结果
    results = {
        "python": "Python是一种高级编程语言，由Guido van Rossum创建。",
        "java": "Java是一种面向对象的编程语言，由Sun Microsystems开发。",
        "javascript": "JavaScript是一种脚本语言，用于Web开发。",
    }
    result = results.get(keyword.lower(), f"未找到关于'{keyword}'的信息")
    return f"[{category}] {result}"


@register_tool(
    name="current_time",
    description="获取当前时间",
)
def current_time(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """获取当前时间。"""
    from datetime import datetime
    return datetime.now().strftime(format)
