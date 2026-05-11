import json
import asyncio
import httpx
from bs4 import BeautifulSoup # 注意：使用前需安装 pip install beautifulsoup4

# =====================================================================
# 工具说明书 (Function Schema)
# =====================================================================
WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "执行互联网搜索引擎查询。当用户询问你不懂的最新知识、实时新闻、或者要求你'上网查一下'时调用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，例如：'2026年世界杯举办地' 或 '今天A股大盘走势'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回的最大结果数量，默认3条",
                    "default": 3
                }
            },
            "required": ["query"]
        }
    }
}

# =====================================================================
# 执行逻辑 (Execute Function)
# =====================================================================
def _sync_bing_search(query: str, max_results: int):
    """
    基于国内版 Bing 的轻量级网页抓取搜索
    完全免费、国内直连无墙、不需要任何 API Key
    """
    url = f"https://cn.bing.com/search?q={query}"
    # 必须伪装成正常的浏览器，否则会被拦截
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # 使用 httpx 发送同步请求
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 提取 Bing 搜索结果列表 (b_algo 是 Bing 默认的搜索结果 class)
            for li in soup.find_all('li', class_='b_algo')[:max_results]:
                title_tag = li.find('h2')
                p_tag = li.find('p')
                
                title = title_tag.text if title_tag else ""
                snippet = p_tag.text if p_tag else ""
                
                if title and snippet:
                    results.append({
                        "title": title,
                        "snippet": snippet
                    })
                    
            return results
    except Exception as e:
        return {"error": str(e)}

async def execute_web_search(query: str, max_results: int = 3) -> str:
    """异步执行网页搜索"""
    try:
        # 将同步的爬虫逻辑放入线程池运行，防止阻塞 FastAPI 异步主线程
        results = await asyncio.to_thread(_sync_bing_search, query, max_results)
        
        if isinstance(results, dict) and "error" in results:
             return json.dumps({"error": f"必应搜索失败: {results['error']}"}, ensure_ascii=False)
        
        if not results:
            return json.dumps({"message": f"未找到关于 '{query}' 的相关结果。"}, ensure_ascii=False)
            
        return json.dumps({"search_results": results}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"搜索服务异常: {str(e)}"})

# 本地测试
if __name__ == "__main__":
    print("测试国内 Bing 联网搜索中...")
    result = asyncio.run(execute_web_search("DeepSeek v4 模型有什么新特性"))
    print(result)