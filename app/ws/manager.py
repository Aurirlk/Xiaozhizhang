"""
WebSocket 连接管理器
管理客户端连接、心跳检测、消息广播
"""
import asyncio
import json
import time
from typing import Dict, Set, Optional
from fastapi import WebSocket


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 活跃连接集合: {client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # 连接元数据: {client_id: {"connected_at": timestamp, "last_heartbeat": timestamp}}
        self.connection_meta: Dict[str, dict] = {}
        # 心跳超时时间（秒）
        self.heartbeat_timeout = 30
        
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """
        接受并注册新连接
        
        Args:
            websocket: WebSocket 连接对象
            client_id: 客户端唯一标识
            
        Returns:
            是否连接成功
        """
        try:
            await websocket.accept()
            
            # 如果已存在旧连接，先关闭
            if client_id in self.active_connections:
                old_ws = self.active_connections[client_id]
                try:
                    await old_ws.close(code=1000, reason="新连接取代旧连接")
                except Exception:
                    pass
            
            self.active_connections[client_id] = websocket
            self.connection_meta[client_id] = {
                "connected_at": time.time(),
                "last_heartbeat": time.time()
            }
            
            print(f"[WS] 客户端 {client_id} 已连接，当前活跃连接: {len(self.active_connections)}")
            return True
            
        except Exception as e:
            print(f"[WS] 连接失败: {e}")
            return False
    
    async def disconnect(self, client_id: str):
        """
        断开并移除连接
        
        Args:
            client_id: 客户端唯一标识
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.close(code=1000)
            except Exception:
                pass
            
            del self.active_connections[client_id]
            if client_id in self.connection_meta:
                del self.connection_meta[client_id]
            
            print(f"[WS] 客户端 {client_id} 已断开，当前活跃连接: {len(self.active_connections)}")
    
    async def send_json(self, client_id: str, data: dict) -> bool:
        """
        发送 JSON 消息给指定客户端
        
        Args:
            client_id: 客户端唯一标识
            data: 要发送的数据字典
            
        Returns:
            是否发送成功
        """
        if client_id not in self.active_connections:
            return False
            
        websocket = self.active_connections[client_id]
        try:
            await websocket.send_text(json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"[WS] 发送消息失败: {e}")
            await self.disconnect(client_id)
            return False
    
    async def send_bytes(self, client_id: str, data: bytes) -> bool:
        """
        发送二进制数据给指定客户端
        
        Args:
            client_id: 客户端唯一标识
            data: 要发送的二进制数据
            
        Returns:
            是否发送成功
        """
        if client_id not in self.active_connections:
            return False
            
        websocket = self.active_connections[client_id]
        try:
            await websocket.send_bytes(data)
            return True
        except Exception as e:
            print(f"[WS] 发送二进制数据失败: {e}")
            await self.disconnect(client_id)
            return False
    
    async def broadcast_json(self, data: dict) -> int:
        """
        广播 JSON 消息给所有连接的客户端
        
        Args:
            data: 要发送的数据字典
            
        Returns:
            成功发送的数量
        """
        success_count = 0
        disconnected = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(data, ensure_ascii=False))
                success_count += 1
            except Exception:
                disconnected.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected:
            await self.disconnect(client_id)
            
        return success_count
    
    def update_heartbeat(self, client_id: str):
        """更新客户端心跳时间"""
        if client_id in self.connection_meta:
            self.connection_meta[client_id]["last_heartbeat"] = time.time()
    
    async def check_heartbeat(self):
        """检查超时的连接并断开"""
        current_time = time.time()
        timeout_clients = []
        
        for client_id, meta in self.connection_meta.items():
            if current_time - meta["last_heartbeat"] > self.heartbeat_timeout:
                timeout_clients.append(client_id)
        
        for client_id in timeout_clients:
            print(f"[WS] 客户端 {client_id} 心跳超时，断开连接")
            await self.disconnect(client_id)
    
    def get_connection_count(self) -> int:
        """获取当前活跃连接数"""
        return len(self.active_connections)
    
    def get_client_ids(self) -> list:
        """获取所有活跃客户端 ID"""
        return list(self.active_connections.keys())


# 全局连接管理器实例
manager = ConnectionManager()


async def heartbeat_checker():
    """后台心跳检测任务"""
    while True:
        await asyncio.sleep(10)  # 每 10 秒检查一次
        await manager.check_heartbeat()
