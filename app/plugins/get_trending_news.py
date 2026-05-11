import httpx
import json
import xml.etree.ElementTree as ET

# =====================================================================
# 工具说明书 (Function Schema)
# =====================================================================
NEWS_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_trending_news",
        "description": "获取不同分类的最新热点新闻。当用户让你'播报一下新闻'、'有什么大瓜'、'最近军事有什么动向'时调用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "新闻类别。可选值：'society'(社会日常), 'finance'(财经金融), 'world'(国际大事), 'military'(军事动态), 'entertainment'(娱乐八卦/明星), 'sports'(体育赛事)。如果用户没明确要求，默认传 'society'。",
                    "enum": ["society", "finance", "world", "military", "entertainment", "sports"],
                    "default": "society"
                }
            }
        }
    }
}

# =====================================================================
# 执行逻辑 (Execute Function)
# =====================================================================
async def execute_get_trending_news(category: str = "society") -> str:
    """通过免费的 RSS 源获取实时新闻（扩展多分类版）"""
    
    # 将用户的类别映射到具体的 RSS 源订阅地址
    rss_map = {
        "society": "https://www.chinanews.com.cn/rss/society.xml",
        "finance": "https://www.chinanews.com.cn/rss/finance.xml",
        "world": "https://www.chinanews.com.cn/rss/world.xml",
        "military": "https://www.chinanews.com.cn/rss/mil.xml",
        "entertainment": "https://www.chinanews.com.cn/rss/ent.xml",
        "sports": "https://www.chinanews.com.cn/rss/sports.xml"
    }
    
    url = rss_map.get(category, rss_map["society"])
    category_zh = {"society":"社会", "finance":"财经", "world":"国际", "military":"军事", "entertainment":"娱乐", "sports":"体育"}[category]
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            # 解析 XML
            root = ET.fromstring(response.content)
            channel = root.find("channel")
            
            news_list = []
            # 提取前 5 条最新新闻
            for item in channel.findall("item")[:5]:
                title = item.find("title").text if item.find("title") is not None else ""
                description = item.find("description").text if item.find("description") is not None else ""
                # 清理长摘要，保留核心信息防止 token 爆炸
                clean_desc = description[:80] + "..." if len(description) > 80 else description
                
                news_list.append({
                    "title": title,
                    "summary": clean_desc
                })
                
            return json.dumps({
                "category_zh": category_zh,
                "top_news": news_list
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({"error": f"获取{category_zh}新闻失败: {str(e)}"})

# 本地测试
if __name__ == "__main__":
    import asyncio
    
    print("获取最新娱乐新闻...")
    ent_result = asyncio.run(execute_get_trending_news("entertainment"))
    print("娱乐新闻：", ent_result)
    
    print("\n获取最新军事新闻...")
    mil_result = asyncio.run(execute_get_trending_news("military"))
    print("军事新闻：", mil_result)