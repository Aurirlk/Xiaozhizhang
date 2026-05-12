/**
 * NeuVox WebSocket SDK
 * 标准化前端对接 SDK
 * 
 * 使用方法：
 * 
 * import { NeuVoxClient } from './neuvox-sdk.js';
 * 
 * const client = new NeuVoxClient('ws://localhost:8000/ws/v1/chat/stream');
 * 
 * // 连接
 * await client.connect();
 * 
 * // 发送文本消息
 * await client.sendText('你好');
 * 
 * // 发送音频数据
 * await client.sendAudio(audioBuffer);
 * 
 * // 监听事件
 * client.on('message', (data) => console.log(data));
 * client.on('token', (token) => console.log(token));
 * client.on('audio', (audioData) => playAudio(audioData));
 */

class NeuVoxClient {
    /**
     * 创建 NeuVox 客户端
     * 
     * @param {string} url - WebSocket 服务器地址
     * @param {Object} options - 配置选项
     */
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            reconnect: true,
            reconnectInterval: 3000,
            maxReconnectAttempts: 10,
            heartbeatInterval: 30000,
            ...options
        };
        
        this.ws = null;
        this.sessionId = options.sessionId || `session_${Date.now()}`;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.heartbeatTimer = null;
        
        // 事件监听器
        this.listeners = {
            'connect': [],
            'disconnect': [],
            'message': [],
            'token': [],
            'audio': [],
            'error': [],
            'status': []
        };
    }
    
    /**
     * 连接到服务器
     */
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(this.url);
                
                this.ws.onopen = () => {
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    this._startHeartbeat();
                    this._emit('connect', { sessionId: this.sessionId });
                    resolve();
                };
                
                this.ws.onmessage = (event) => {
                    this._handleMessage(event.data);
                };
                
                this.ws.onerror = (error) => {
                    this._emit('error', { error });
                    reject(error);
                };
                
                this.ws.onclose = (event) => {
                    this.isConnected = false;
                    this._stopHeartbeat();
                    this._emit('disconnect', { code: event.code, reason: event.reason });
                    
                    if (this.options.reconnect && event.code !== 1000) {
                        this._attemptReconnect();
                    }
                };
            } catch (error) {
                reject(error);
            }
        });
    }
    
    /**
     * 断开连接
     */
    disconnect() {
        this.options.reconnect = false;
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
        }
    }
    
    /**
     * 发送文本消息
     * 
     * @param {string} text - 文本内容
     */
    async sendText(text) {
        if (!this.isConnected) {
            throw new Error('Not connected');
        }
        
        const message = {
            type: 'text',
            content: text,
            session_id: this.sessionId
        };
        
        this.ws.send(JSON.stringify(message));
    }
    
    /**
     * 发送音频数据
     * 
     * @param {ArrayBuffer} audioData - 音频数据
     */
    async sendAudio(audioData) {
        if (!this.isConnected) {
            throw new Error('Not connected');
        }
        
        this.ws.send(audioData);
    }
    
    /**
     * 开始录音
     */
    async startRecording() {
        if (!this.isConnected) {
            throw new Error('Not connected');
        }
        
        this.ws.send(JSON.stringify({
            type: 'audio_start',
            session_id: this.sessionId
        }));
    }
    
    /**
     * 停止录音
     */
    async stopRecording() {
        if (!this.isConnected) {
            throw new Error('Not connected');
        }
        
        this.ws.send(JSON.stringify({
            type: 'audio_end',
            session_id: this.sessionId
        }));
    }
    
    /**
     * 监听事件
     * 
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    on(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event].push(callback);
        }
        return this;
    }
    
    /**
     * 移除事件监听
     * 
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    off(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
        }
        return this;
    }
    
    /**
     * 触发事件
     * @private
     */
    _emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (e) {
                    console.error(`Event listener error: ${e}`);
                }
            });
        }
    }
    
    /**
     * 处理收到的消息
     * @private
     */
    _handleMessage(data) {
        try {
            // 检查是否是二进制数据（音频）
            if (data instanceof ArrayBuffer || data instanceof Blob) {
                this._emit('audio', data);
                return;
            }
            
            // 解析 JSON 消息
            const message = JSON.parse(data);
            this._emit('message', message);
            
            // 根据消息类型分发
            switch (message.type) {
                case 'connected':
                    this._emit('connect', message);
                    break;
                case 'token':
                    this._emit('token', message.content);
                    break;
                case 'llm_done':
                    this._emit('llm_done', message);
                    break;
                case 'tts_done':
                    this._emit('tts_done', message);
                    break;
                case 'status':
                    this._emit('status', message);
                    break;
                case 'error':
                    this._emit('error', message);
                    break;
                case 'pong':
                    break;
                default:
                    this._emit('message', message);
            }
        } catch (e) {
            console.error('Message parse error:', e);
        }
    }
    
    /**
     * 启动心跳
     * @private
     */
    _startHeartbeat() {
        this._stopHeartbeat();
        this.heartbeatTimer = setInterval(() => {
            if (this.isConnected) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, this.options.heartbeatInterval);
    }
    
    /**
     * 停止心跳
     * @private
     */
    _stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    /**
     * 尝试重连
     * @private
     */
    async _attemptReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            this._emit('error', { message: 'Max reconnect attempts reached' });
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.options.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1);
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`);
        
        setTimeout(async () => {
            try {
                await this.connect();
            } catch (e) {
                console.error('Reconnect failed:', e);
            }
        }, delay);
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { NeuVoxClient };
} else if (typeof window !== 'undefined') {
    window.NeuVoxClient = NeuVoxClient;
}
