import os
import httpx
import json

# =====================================================================
# 第一部分：写给大模型看的"工具说明书" (Function Schema)
# =====================================================================
WEATHER_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定中国城市的实时天气信息。当用户询问任何关于天气、气温、下雨等问题时，必须调用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "需要查询的城市名称，例如：北京、广州、深圳。不要带'市'字。"
                }
            },
            "required": ["city"]
        }
    }
}

# =====================================================================
# 第二部分：后端的实际执行逻辑 (Execute Function)
# =====================================================================
async def execute_get_weather(city: str) -> str:
    """
    根据城市名获取天气。
    API Key 从配置文件或环境变量读取
    """
    from app.utils.config_loader import config
    
    # 从配置获取 API Key
    weather_config = config.get_weather_config()
    API_KEY = weather_config.get("api_key") or os.getenv("QWEATHER_API_KEY")
    
    if not API_KEY:
        return json.dumps({"error": "天气 API Key 未配置"})
    
    # 和风天气的查询需要两步：先查 城市ID，再查 实时天气
    geo_url = f"https://geoapi.qweather.com/v2/city/lookup?location={city}&key={API_KEY}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # 1. 查询城市 ID
            geo_response = await client.get(geo_url)
            geo_data = geo_response.json()
            
            if geo_data.get("code") != "200" or not geo_data.get("location"):
                return json.dumps({"error": f"抱歉，没有找到 '{city}' 的地理信息，请换个城市名试试。"})
                
            location_id = geo_data["location"][0]["id"]
            city_name = geo_data["location"][0]["name"]
            
            # 2. 查询该城市的实时天气
            weather_url = f"https://devapi.qweather.com/v7/weather/now?location={location_id}&key={API_KEY}"
            weather_response = await client.get(weather_url)
            weather_data = weather_response.json()
            
            if weather_data.get("code") == "200":
                now = weather_data["now"]
                # 构造返回给大模型的数据
                result = {
                    "city": city_name,
                    "weather": now["text"],        # 比如：晴、多云
                    "temperature": now["temp"],    # 气温，摄氏度
                    "feels_like": now["feelsLike"],# 体感温度
                    "wind_dir": now["windDir"],    # 风向
                    "humidity": now["humidity"]    # 湿度百分比
                }
                # 将结果转为字符串返回给大模型
                return json.dumps(result, ensure_ascii=False)
            else:
                return json.dumps({"error": "天气API接口返回异常，请稍后再试。"})
                
        except Exception as e:
            return json.dumps({"error": f"请求天气服务失败: {str(e)}"})

# 简单的本地测试入口
if __name__ == "__main__":
    import asyncio
    # 填入 API Key 后，运行此文件测试：
    print("测试获取广州天气...")
    result = asyncio.run(execute_get_weather("广州"))
    print(result)