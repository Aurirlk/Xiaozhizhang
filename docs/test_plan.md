# NeuVox 黑盒测试方案

## 一、测试环境

| 项目        | 值                               |
| --------- | ------------------------------- |
| 后端地址      | http://127.0.0.1:8000           |
| Web UI 地址 | http://127.0.0.1:7860           |
| 测试工具      | curl / Python httpx / 浏览器       |
| 默认 LLM    | DeepSeekLLM (deepseek-v4-flash) |
| 默认 ASR    | FunASR (paraformer-zh)          |
| 默认 TTS    | EdgeTTS (zh-CN-XiaoxiaoNeural)  |

---

## 二、Prompt 测试用例（覆盖全部 6 种意图）

### 2.1 天气意图 (weather)

| 编号   | 输入 Prompt | 预期意图    | 预期行为                             |
| ---- | --------- | ------- | -------------------------------- |
| W-01 | 北京今天天气怎么样 | weather | 提取 city=北京，调用 get_weather，返回天气数据 |
| W-02 | 江西南昌的今天天气 | weather | 提取 city=江西南昌，调用 get_weather      |
| W-03 | 明天会下雨吗    | weather | 触发天气意图，询问是否下雨                    |
| W-04 | 上海多少度     | weather | 提取 city=上海，返回温度                  |
| W-05 | 广州会不会下雨   | weather | 提取 city=广州，返回降雨概率                |
| W-06 | 天气        | weather | 无城市参数，应提示用户指定城市或用 LLM 提取         |
| W-07 | 空气质量怎么样   | weather | 关键词匹配 weather                    |

### 2.2 新闻意图 (news)

| 编号   | 输入 Prompt | 预期意图 | 预期行为                        |
| ---- | --------- | ---- | --------------------------- |
| N-01 | 今天有什么新闻   | news | 调用 get_trending_news，返回社会新闻 |
| N-02 | 最新热点      | news | 关键词"热点"触发                   |
| N-03 | 给我看财经新闻   | news | category=finance            |
| N-04 | 国际上发生了什么  | news | 关键词"发生了什么"触发                |
| N-05 | 体育新闻      | news | category=sports             |
| N-06 | 最近有什么大瓜   | news | 关键词"大瓜"触发                   |

### 2.3 搜索意图 (search)

| 编号   | 输入 Prompt        | 预期意图   | 预期行为                  |
| ---- | ---------------- | ------ | --------------------- |
| S-01 | 帮我查一下 Python 怎么学 | search | 调用 web_search，返回搜索结果  |
| S-02 | 搜索一下人工智能最新进展     | search | 关键词"搜索"触发             |
| S-03 | 什么是量子计算          | search | 关键词"什么是"触发            |
| S-04 | OpenAI 的 CEO 是谁  | search | LLM 分类为 search 或 chat |
| S-05 | 怎么做红烧肉           | search | 关键词"怎么"触发             |
| S-06 | 帮我查              | search | 关键词"帮我查"触发            |

### 2.4 知识库意图 (knowledge)

| 编号   | 输入 Prompt    | 预期意图      | 预期行为             |
| ---- | ------------ | --------- | ---------------- |
| K-01 | 劳动法规定加班费怎么算  | knowledge | 关键词"劳动法"触发，查询知识库 |
| K-02 | 合同纠纷怎么处理     | knowledge | 关键词"合同"触发        |
| K-03 | 民法典里关于隐私权的规定 | knowledge | 关键词"民法典"触发       |
| K-04 | 知识产权保护有哪些法律  | knowledge | 关键词"知识产权"触发      |
| K-05 | 刑法中诈骗罪的量刑标准  | knowledge | 关键词"刑法"触发        |

### 2.5 时间意图 (time)

| 编号   | 输入 Prompt | 预期意图 | 预期行为             |
| ---- | --------- | ---- | ---------------- |
| T-01 | 现在几点了     | time | 关键词"几点"触发，返回当前时间 |
| T-02 | 今天星期几     | time | 关键词"星期"触发        |
| T-03 | 今天几号      | time | 关键词"几号"触发        |
| T-04 | 今天日期是什么   | time | 关键词"今天"触发        |
| T-05 | 当前时间      | time | 关键词"当前"触发        |

### 2.6 闲聊意图 (chat)

| 编号   | 输入 Prompt     | 预期意图 | 预期行为       |
| ---- | ------------- | ---- | ---------- |
| C-01 | 你好，介绍一下你自己    | chat | LLM 直接回复   |
| C-02 | 给我讲个笑话        | chat | LLM 生成笑话   |
| C-03 | 你觉得人工智能会取代人类吗 | chat | LLM 讨论话题   |
| C-04 | 帮我写一首诗        | chat | LLM 创作诗歌   |
| C-05 | 1+1等于几        | chat | LLM 回答简单问题 |
| C-06 | 你能做什么         | chat | LLM 介绍自身能力 |
| C-07 | 谢谢你           | chat | LLM 礼貌回复   |
| C-08 | 你叫什么名字        | chat | LLM 回复名称   |

### 2.7 意图识别边界测试

| 编号   | 输入 Prompt               | 预期意图         | 测试点    |
| ---- | ----------------------- | ------------ | ------ |
| B-01 | 我想看看北京天气和最新新闻           | weather/news | 多意图混合  |
| B-02 | asdfghjkl               | chat         | 无意义输入  |
| B-03 | （空字符串）                  | 无            | 参数校验   |
| B-04 | a                       | chat         | 单字符输入  |
| B-05 | 今天天气不错，帮我查一下明天北京天气会不会下雨 | weather      | 复杂天气句式 |
| B-06 | 你好天气好                   | weather      | 关键词边界  |

---

## 三、API 接口黑盒测试

### 3.1 POST /api/v1/ask（统一问答）

```bash
# TC-API-01: 纯文本输入
curl -X POST http://127.0.0.1:8000/api/v1/ask \
  -F "session_id=test_001" \
  -F "text=你好" \
  -F "need_tts=true"
# 预期: 200, code=200, reply_text 非空, audio_url 非空

# TC-API-02: 纯文本输入，不需要 TTS
curl -X POST http://127.0.0.1:8000/api/v1/ask \
  -F "session_id=test_002" \
  -F "text=你好" \
  -F "need_tts=false"
# 预期: 200, code=200, reply_text 非空, audio_url=null

# TC-API-03: 缺少必要参数
curl -X POST http://127.0.0.1:8000/api/v1/ask \
  -F "session_id=test_003"
# 预期: 400, detail="必须提供 text 或 audio_file 其中之一"

# TC-API-04: 语音文件输入
curl -X POST http://127.0.0.1:8000/api/v1/ask \
  -F "session_id=test_004" \
  -F "audio_file=@test.wav" \
  -F "need_tts=true"
# 预期: 200, recognized_text 非空, reply_text 非空, audio_url 非空

# TC-API-05: 会话上下文保持
curl -X POST http://127.0.0.1:8000/api/v1/ask \
  -F "session_id=test_005" \
  -F "text=我叫张三"
# 然后
curl -X POST http://127.0.0.1:8000/api/v1/ask \
  -F "session_id=test_005" \
  -F "text=我叫什么名字"
# 预期: 回复中包含"张三"
```

### 3.2 GET /api/v1/health（健康检查）

```bash
curl http://127.0.0.1:8000/api/v1/health
# 预期: 200, status="healthy", 各服务状态正常
```

### 3.3 GET /api/v1/providers（服务提供商列表）

```bash
curl http://127.0.0.1:8000/api/v1/providers
# 预期: 200, 包含 asr/llm/tts 各提供商列表
```

### 3.4 GET /api/v1/voices（音色列表）

```bash
curl http://127.0.0.1:8000/api/v1/voices
# 预期: 200, 返回中文音色列表
```

### 3.5 GET /api/v1/assets/audio/{filename}（音频文件）

```bash
# TC-AUDIO-01: 存在的文件
curl -I http://127.0.0.1:8000/api/v1/assets/audio/xxx.mp3
# 预期: 200, Content-Type: audio/mpeg

# TC-AUDIO-02: 不存在的文件
curl -I http://127.0.0.1:8000/api/v1/assets/audio/not_exist.mp3
# 预期: 404
```

### 3.6 DELETE /api/v1/sessions/{session_id}（清空会话）

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/sessions/test_001
# 预期: 200, message="会话已清空"
```

### 3.7 POST /api/v1/chat/text（文本对话）

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat/text \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "history": []}' \
  -G --data-urlencode "provider=auto"
# 预期: 200, success=true, message 非空
```

### 3.8 WebSocket /ws/v1/chat/stream（流式对话）

```python
import asyncio
import websockets

async def test_ws():
    async with websockets.connect("ws://127.0.0.1:8001/ws/v1/chat/stream") as ws:
        # 1. 接收 connected 消息
        msg = await ws.recv()
        assert "connected" in msg

        # 2. 发送文本消息
        await ws.send('{"type": "text", "content": "你好"}')

        # 3. 接收流式回复
        tokens = []
        while True:
            msg = await ws.recv()
            if "llm_token" in msg:
                tokens.append(msg)
            elif "llm_done" in msg:
                break
            elif "tts_done" in msg:
                break
        assert len(tokens) > 0

asyncio.run(test_ws())
```

---

## 四、语音输入/输出测试

### 4.1 ASR 语音识别测试

| 编号     | 测试文件       | 预期识别结果    | 测试点   |
| ------ | ---------- | --------- | ----- |
| ASR-01 | 清晰中文男声.wav | 准确识别中文    | 基础识别  |
| ASR-02 | 清晰中文女声.wav | 准确识别中文    | 不同音色  |
| ASR-03 | 带背景噪音.wav  | 识别率 > 80% | 噪音鲁棒性 |
| ASR-04 | 快速语速.wav   | 识别率 > 70% | 快速语音  |
| ASR-05 | 方言.wav     | 部分识别      | 方言支持  |
| ASR-06 | 静音.wav     | 空文本或提示    | 静音处理  |

### 4.2 TTS 语音合成测试

| 编号     | 输入文本                | 音色  | 预期         | 测试点   |
| ------ | ------------------- | --- | ---------- | ----- |
| TTS-01 | 你好，今天天气真不错          | 晓晓  | 生成 mp3，可播放 | 基础合成  |
| TTS-02 | 你好                  | 云希  | 男声合成       | 音色切换  |
| TTS-03 | （空字符串）              | 默认  | 返回错误       | 空文本处理 |
| TTS-04 | 这是一段很长的文本...（500字）  | 默认  | 正常合成       | 长文本   |
| TTS-05 | Hello, how are you? | 默认  | 英文合成       | 中英混合  |
| TTS-06 | 123456789           | 默认  | 数字朗读       | 数字处理  |

### 4.3 完整语音对话测试

| 编号       | 流程                        | 预期     |
| -------- | ------------------------- | ------ |
| VOICE-01 | 录音 → ASR → LLM → TTS → 播放 | 全链路通畅  |
| VOICE-02 | 录音（噪音） → ASR → LLM → TTS  | 容错处理   |
| VOICE-03 | 录音（静音） → ASR              | 返回提示信息 |

---

## 五、Gradio Web UI 测试

### 5.1 设置面板测试

| 编号    | 操作                   | 预期结果                        |
| ----- | -------------------- | --------------------------- |
| UI-01 | 点击 ⚙️ 设置按钮           | 右侧滑出设置浮窗 + 遮罩层              |
| UI-02 | 点击 ✕ 关闭按钮            | 浮窗关闭                        |
| UI-03 | 点击遮罩层                | 浮窗关闭                        |
| UI-04 | 切换到 🎨 个性化标签         | 显示主题/回复模式/音量/音色             |
| UI-05 | 切换到 🌐 网络标签          | 显示 WebSocket/OTA 地址         |
| UI-06 | 切换到 💬 风格标签          | 显示回复风格选择                    |
| UI-07 | 切换到 ⚙️ 参数标签          | 显示 Temperature/上下文/Token/插件 |
| UI-08 | 修改主题颜色为橙色            | 页面主题变为橙色                    |
| UI-09 | 修改回复模式为仅文字           | AI 只返回文字不返回语音               |
| UI-10 | 修改音色为云希(男)           | TTS 使用男声                    |
| UI-11 | 调整 Temperature 为 1.5 | 回复更有创造性                     |
| UI-12 | 调整上下文轮数为 0           | 不携带历史上下文                    |
| UI-13 | 取消勾选天气插件             | 天气查询降级为 LLM 直接回复            |
| UI-14 | 点击 💾 保存设置           | 显示"✅ 已保存"                   |
| UI-15 | 刷新页面                 | 设置保持上次保存的值                  |

### 5.2 对话功能测试

| 编号    | 操作           | 预期结果                  |
| ----- | ------------ | --------------------- |
| UI-20 | 文本输入"你好"点击发送 | chatbot 显示用户消息和 AI 回复 |
| UI-21 | 文本输入按 Enter  | 同上，Enter 触发发送         |
| UI-22 | 点击麦克风录音并发送   | 识别语音 → AI 回复 → 播放音频   |
| UI-23 | 点击清空按钮       | 对话历史和音频清空             |
| UI-24 | 连续发送 5 条消息   | 对话历史累积显示              |
| UI-25 | 输入空文本点击发送    | 无响应或提示                |
| UI-26 | 设置回复模式为仅文字   | 发送后只有文字无音频            |
| UI-27 | 设置回复模式为仅语音   | 发送后只有音频无文字            |

---

## 六、边界与异常测试

### 6.1 网络异常

| 编号     | 场景                  | 预期                  |
| ------ | ------------------- | ------------------- |
| EXC-01 | 后端未启动，发送请求          | 返回连接错误              |
| EXC-02 | DeepSeek API Key 无效 | 返回 500，错误信息包含"认证失败" |
| EXC-03 | 请求超时（60s）           | 返回超时错误              |
| EXC-04 | 并发发送 10 个请求         | 全部正常响应或排队           |

### 6.2 输入边界

| 编号     | 场景                               | 预期        |
| ------ | -------------------------------- | --------- |
| EXC-10 | 发送 10000 字超长文本                   | 正常处理或返回截断 |
| EXC-11 | 发送纯 emoji                        | 正常处理      |
| EXC-12 | 发送特殊字符 <script>alert(1)</script> | 安全处理，不执行  |
| EXC-13 | 发送 SQL 注入 ' OR 1=1 --            | 安全处理      |
| EXC-14 | 上传非音频文件（.txt）                    | 返回格式错误    |
| EXC-15 | 上传超大文件（>10MB）                    | 返回文件过大错误  |

### 6.3 成本控制

| 编号      | 场景           | 预期                     |
| ------- | ------------ | ---------------------- |
| COST-01 | 日用量接近限额（80%） | 触发预警日志                 |
| COST-02 | 日用量超过限额      | 返回 429 budget_exceeded |
| COST-03 | 月用量超过限额      | 返回 429 budget_exceeded |

### 6.4 会话管理

| 编号         | 场景                 | 预期          |
| ---------- | ------------------ | ----------- |
| SESSION-01 | 同一 session_id 连续对话 | 上下文保持       |
| SESSION-02 | 不同 session_id 对话   | 上下文隔离       |
| SESSION-03 | 删除会话后再对话           | 重新开始        |
| SESSION-04 | 超过 5 轮对话           | 滑动窗口，丢弃最早轮次 |

---

## 七、测试执行检查清单

### 启动前检查

- [ ] `.env` 中 API Key 已配置（DeepSeek）
- [ ] `configs/.config.yaml` 中 ASR=FunASR, TTS=EdgeTTS
- [ ] `configs/ui_settings.json` 可选存在

### 启动后检查

- [ ] `python main.py` 启动成功，无报错
- [ ] `python voice_chat_ui.py` 启动成功，无报错
- [ ] 浏览器打开 http://127.0.0.1:7860 正常显示
- [ ] http://127.0.0.1:8000/docs Swagger 文档可访问

### 核心功能验证

- [ ] 文本对话正常返回
- [ ] 语音输入正常识别
- [ ] TTS 语音正常播放
- [ ] 意图识别覆盖 6 种意图
- [ ] 工具调用正常（天气除外）
- [ ] 设置面板正常展开/收起
- [ ] 设置持久化正常

---

## 八、测试报告模板

| 编号   | 测试项  | 输入        | 预期     | 实际  | 结果  | 备注  |
| ---- | ---- | --------- | ------ | --- | --- | --- |
| W-01 | 天气查询 | 北京今天天气怎么样 | 返回天气数据 |     |     |     |
| ...  | ...  | ...       | ...    |     |     |     |

**结果统计：**

- 总用例数：XX
- 通过：XX
- 失败：XX
- 阻塞：XX
- 通过率：XX%
