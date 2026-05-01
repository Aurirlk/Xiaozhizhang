"""
启动入口
核心逻辑在 fastAPI.py 中
"""
import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "fastAPI:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
