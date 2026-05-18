"""
NeuVox 管理后端 API
提供系统配置、插件管理、用户管理等功能
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import os

# 创建 FastAPI 应用
app = FastAPI(
    title="NeuVox Manager API",
    description="NeuVox 系统管理后端",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 数据模型 ====================

class ConfigUpdate(BaseModel):
    """配置更新请求"""
    module: str
    key: str
    value: Any


class PluginAction(BaseModel):
    """插件操作请求"""
    plugin_name: str


class SystemStatus(BaseModel):
    """系统状态"""
    version: str
    services: Dict[str, str]
    plugins: Dict[str, Dict[str, Any]]


# ==================== 配置管理接口 ====================

@app.get("/api/v1/config", tags=["config"])
async def get_config():
    """获取系统配置"""
    from app.utils.config_loader import config
    
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "selected_module": config.get("selected_module", {}),
            "server": config.get("server", {}),
            "embedding": config.get("Embedding", {}),
        }
    }


@app.get("/api/v1/config/{module}", tags=["config"])
async def get_module_config(module: str):
    """获取指定模块配置"""
    from app.utils.config_loader import config
    
    module_config = config.get(module, default=None)
    if module_config is None:
        raise HTTPException(status_code=404, detail=f"模块 {module} 不存在")
    
    return {
        "code": 200,
        "msg": "success",
        "data": module_config
    }


@app.put("/api/v1/config", tags=["config"])
async def update_config(update: ConfigUpdate):
    """更新配置（热更新）"""
    from app.utils.config_loader import config
    
    # 获取当前配置
    current = config.get(update.module, default={})
    if current is None:
        raise HTTPException(status_code=404, detail=f"模块 {update.module} 不存在")
    
    # 更新配置
    current[update.key] = update.value
    config._config[update.module] = current
    
    logger.info(f"[Config] 更新配置: {update.module}.{update.key} = {update.value}")
    
    return {
        "code": 200,
        "msg": "success",
        "data": {"message": "配置已更新"}
    }


# ==================== 插件管理接口 ====================

@app.get("/api/v1/plugins", tags=["plugins"])
async def list_plugins():
    """列出所有插件"""
    from app.services.plugin_manager import plugin_manager
    
    plugins = plugin_manager.get_plugin_status()
    
    return {
        "code": 200,
        "msg": "success",
        "data": plugins
    }


@app.post("/api/v1/plugins/load", tags=["plugins"])
async def load_plugin(action: PluginAction):
    """加载插件"""
    from app.services.plugin_manager import plugin_manager
    
    success = plugin_manager.load_plugin(action.plugin_name)
    
    if success:
        return {"code": 200, "msg": "success", "data": {"message": f"插件 {action.plugin_name} 加载成功"}}
    else:
        raise HTTPException(status_code=500, detail=f"插件 {action.plugin_name} 加载失败")


@app.post("/api/v1/plugins/unload", tags=["plugins"])
async def unload_plugin(action: PluginAction):
    """卸载插件"""
    from app.services.plugin_manager import plugin_manager
    
    success = plugin_manager.unload_plugin(action.plugin_name)
    
    if success:
        return {"code": 200, "msg": "success", "data": {"message": f"插件 {action.plugin_name} 卸载成功"}}
    else:
        raise HTTPException(status_code=500, detail=f"插件 {action.plugin_name} 卸载失败")


@app.post("/api/v1/plugins/reload", tags=["plugins"])
async def reload_plugin(action: PluginAction):
    """重载插件"""
    from app.services.plugin_manager import plugin_manager
    
    success = plugin_manager.reload_plugin(action.plugin_name)
    
    if success:
        return {"code": 200, "msg": "success", "data": {"message": f"插件 {action.plugin_name} 重载成功"}}
    else:
        raise HTTPException(status_code=500, detail=f"插件 {action.plugin_name} 重载失败")


@app.post("/api/v1/plugins/reload-all", tags=["plugins"])
async def reload_all_plugins():
    """重载所有插件"""
    from app.services.plugin_manager import plugin_manager
    
    success_count = plugin_manager.reload_all()
    
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "success_count": success_count,
            "total_count": len(plugin_manager.list_plugins())
        }
    }


# ==================== 系统状态接口 ====================

@app.get("/api/v1/status", tags=["system"])
async def get_system_status():
    """获取系统状态"""
    from app.services.plugin_manager import plugin_manager
    from app.config import settings
    
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "version": settings.APP_VERSION,
            "services": {
                "asr": "ready",
                "llm": "ready",
                "tts": "ready",
                "crm": "ready",
                "knowledge": "ready"
            },
            "plugins": plugin_manager.get_plugin_status()
        }
    }


@app.get("/api/v1/health", tags=["system"])
async def health_check():
    """健康检查"""
    return {"code": 200, "msg": "success", "data": {"status": "ok"}}


# 启动入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("manager-api:app", host="0.0.0.0", port=8002, reload=True)
