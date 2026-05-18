"""
插件管理器
支持运行时加载/卸载/重载插件
"""
import os
import importlib
import sys
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

from app.utils.logger import logger


class PluginInfo:
    """插件信息"""
    
    def __init__(self, name: str, module_path: str, instance: Any = None):
        self.name = name
        self.module_path = module_path
        self.instance = instance
        self.loaded = False
        self.error = None


class PluginManager:
    """
    插件管理器
    
    支持：
    - 运行时加载插件
    - 运行时卸载插件
    - 插件热重载
    - 插件状态监控
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins: Dict[str, PluginInfo] = {}
            cls._instance._plugin_dir = "app/plugins"
        return cls._instance
    
    def __init__(self):
        self._scan_plugins()
    
    def _scan_plugins(self):
        """扫描插件目录"""
        plugin_dir = Path(self._plugin_dir)
        
        if not plugin_dir.exists():
            logger.warning(f"[PluginManager] 插件目录不存在: {self._plugin_dir}")
            return
        
        for file_path in plugin_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            
            plugin_name = file_path.stem
            module_path = f"app.plugins.{plugin_name}"
            
            if plugin_name not in self._plugins:
                self._plugins[plugin_name] = PluginInfo(
                    name=plugin_name,
                    module_path=module_path
                )
                logger.info(f"[PluginManager] 发现插件: {plugin_name}")
    
    def load_plugin(self, plugin_name: str) -> bool:
        """
        加载插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否加载成功
        """
        if plugin_name not in self._plugins:
            logger.error(f"[PluginManager] 插件不存在: {plugin_name}")
            return False
        
        plugin_info = self._plugins[plugin_name]
        
        try:
            # 动态导入模块
            if plugin_info.module_path in sys.modules:
                module = sys.modules[plugin_info.module_path]
            else:
                module = importlib.import_module(plugin_info.module_path)
            
            plugin_info.instance = module
            plugin_info.loaded = True
            plugin_info.error = None
            
            logger.info(f"[PluginManager] 插件加载成功: {plugin_name}")
            return True
            
        except Exception as e:
            plugin_info.loaded = False
            plugin_info.error = str(e)
            logger.error(f"[PluginManager] 插件加载失败: {plugin_name}, 错误: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否卸载成功
        """
        if plugin_name not in self._plugins:
            logger.error(f"[PluginManager] 插件不存在: {plugin_name}")
            return False
        
        plugin_info = self._plugins[plugin_name]
        
        try:
            # 从 sys.modules 中移除
            if plugin_info.module_path in sys.modules:
                del sys.modules[plugin_info.module_path]
            
            plugin_info.instance = None
            plugin_info.loaded = False
            plugin_info.error = None
            
            logger.info(f"[PluginManager] 插件卸载成功: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"[PluginManager] 插件卸载失败: {plugin_name}, 错误: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """
        重载插件（热重载）
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否重载成功
        """
        logger.info(f"[PluginManager] 重载插件: {plugin_name}")
        
        # 先卸载
        self.unload_plugin(plugin_name)
        
        # 再加载
        return self.load_plugin(plugin_name)
    
    def reload_all(self) -> int:
        """
        重载所有插件
        
        Returns:
            成功重载的插件数量
        """
        success_count = 0
        
        for plugin_name in list(self._plugins.keys()):
            if self.reload_plugin(plugin_name):
                success_count += 1
        
        logger.info(f"[PluginManager] 重载完成，成功: {success_count}/{len(self._plugins)}")
        return success_count
    
    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """获取插件实例"""
        plugin_info = self._plugins.get(plugin_name)
        if plugin_info and plugin_info.loaded:
            return plugin_info.instance
        return None
    
    def get_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件状态"""
        status = {}
        for name, info in self._plugins.items():
            status[name] = {
                "loaded": info.loaded,
                "error": info.error,
                "module_path": info.module_path
            }
        return status
    
    def list_plugins(self) -> List[str]:
        """列出所有插件"""
        return list(self._plugins.keys())
    
    def list_loaded_plugins(self) -> List[str]:
        """列出已加载的插件"""
        return [name for name, info in self._plugins.items() if info.loaded]


# 全局插件管理器实例
plugin_manager = PluginManager()
