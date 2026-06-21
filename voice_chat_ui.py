"""
NeuVox 智能语音管家 - Gradio UI 界面
"""
import os
# 禁用系统代理
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("ALL_PROXY", None)
os.environ.pop("all_proxy", None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

import gradio as gr
import httpx
import tempfile
import yaml
import json

API_URL = "http://127.0.0.1:8000/api/v1/ask"
SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "configs", "ui_settings.json")

DEFAULT_SETTINGS = {
    "theme": "深蓝色",
    "reply_mode": "语音+文字",
    "volume": 70,
    "voice": "zh-CN-XiaoxiaoNeural",
    "ws_address": "ws://127.0.0.1:8001",
    "ota_address": "http://127.0.0.1:8003",
    "reply_style": "友好专业",
    "temperature": 0.7,
    "context_rounds": 3,
    "max_tokens": 2048,
    "plugins": ["天气", "新闻", "搜索", "知识库"],
}

VOICE_CHOICES = {
    "晓晓 (女)": "zh-CN-XiaoxiaoNeural",
    "晓依 (女)": "zh-CN-XiaoyiNeural",
    "云希 (男)": "zh-CN-YunxiNeural",
    "云扬 (男)": "zh-CN-YunyangNeural",
    "云健 (男)": "zh-CN-YunjianNeural",
    "晓辰 (女)": "zh-CN-XiaochenNeural",
    "晓涵 (女)": "zh-CN-XiaohanNeural",
    "晓梦 (女)": "zh-CN-XiaomengNeural",
    "晓墨 (女)": "zh-CN-XiaomoNeural",
}

STYLE_PROMPTS = {
    "友好专业": "你是一个友好、专业的智能语音助手。请用简洁自然的中文回答用户的问题。回复要口语化，适合语音播报。",
    "简洁直接": "请用简短直接的方式回答，避免废话和客套。重点突出，一针见血。",
    "幽默风趣": "你是一个幽默风趣的助手，适当加入轻松的表达，让对话更有趣。",
    "严谨专业": "你是一个严谨的专业助手，回答要准确、有条理、逻辑清晰。",
}

OVERLAY_CSS = """
#settings-overlay {
    position: fixed !important;
    top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
    background: rgba(0,0,0,0.35) !important;
    z-index: 9998 !important;
}
#settings-drawer {
    position: fixed !important;
    top: 0 !important; right: 0 !important;
    width: 400px !important;
    height: 100vh !important;
    max-height: 100vh !important;
    background: #fff !important;
    box-shadow: -4px 0 24px rgba(0,0,0,0.18) !important;
    z-index: 9999 !important;
    overflow-y: auto !important;
    padding: 20px !important;
    border-radius: 0 !important;
    animation: slideInDrawer 0.25s ease !important;
}
@keyframes slideInDrawer {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
}
#settings-drawer .gradio-group {
    border: none !important;
    box-shadow: none !important;
}
"""


def load_settings():
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存设置失败: {e}")


def toggle_drawer(visible):
    return gr.update(visible=not visible), gr.update(visible=not visible), not visible


def apply_settings(settings_state, theme, reply_mode, volume, voice,
                   ws_address, ota_address, reply_style, temperature,
                   context_rounds, max_tokens, plugins):
    settings = {
        "theme": theme,
        "reply_mode": reply_mode,
        "volume": volume,
        "voice": voice,
        "ws_address": ws_address,
        "ota_address": ota_address,
        "reply_style": reply_style,
        "temperature": temperature,
        "context_rounds": context_rounds,
        "max_tokens": max_tokens,
        "plugins": plugins or [],
    }
    save_settings(settings)
    return settings, "✅ 已保存"


def process_voice_input(audio_path, chat_history, settings_state):
    if audio_path is None:
        return chat_history, None
    session_id = "gradio_session_001"
    settings = settings_state or DEFAULT_SETTINGS
    reply_mode = settings.get("reply_mode", "语音+文字")
    need_tts = reply_mode in ("语音+文字", "仅语音")
    try:
        with open(audio_path, "rb") as f:
            files = {"audio_file": (os.path.basename(audio_path), f, "audio/wav")}
            data = {"session_id": session_id, "need_tts": str(need_tts).lower()}
            with httpx.Client(timeout=60.0) as client:
                response = client.post(API_URL, data=data, files=files)
                response.raise_for_status()
        res_json = response.json()
        if res_json.get("code") == 200:
            res_data = res_json.get("data", {})
            recognized_text = res_data.get("recognized_text", "未识别到语音")
            reply_text = res_data.get("reply_text", "无回复内容")
            audio_url = res_data.get("audio_url")
            chat_history.append({"role": "user", "content": f"语音: {recognized_text}"})
            chat_history.append({"role": "assistant", "content": f"AI: {reply_text}"})
            output_audio_path = None
            if audio_url and need_tts:
                with httpx.Client() as client:
                    audio_res = client.get(f"http://127.0.0.1:8000{audio_url}")
                    if audio_res.status_code == 200:
                        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        temp_audio.write(audio_res.content)
                        temp_audio.close()
                        output_audio_path = temp_audio.name
            return chat_history, output_audio_path
        else:
            chat_history.append({"role": "user", "content": "语音输入"})
            chat_history.append({"role": "assistant", "content": f"错误: {res_json.get('msg')}"})
            return chat_history, None
    except Exception as e:
        chat_history.append({"role": "user", "content": "语音输入"})
        chat_history.append({"role": "assistant", "content": f"错误: {str(e)}"})
        return chat_history, None


def process_text_input(text, chat_history, settings_state):
    if not text or not text.strip():
        return chat_history, "", None
    session_id = "gradio_session_001"
    settings = settings_state or DEFAULT_SETTINGS
    reply_mode = settings.get("reply_mode", "语音+文字")
    need_tts = reply_mode in ("语音+文字", "仅语音")
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                API_URL,
                data={"session_id": session_id, "text": text, "need_tts": str(need_tts).lower()}
            )
            response.raise_for_status()
        res_json = response.json()
        if res_json.get("code") == 200:
            res_data = res_json.get("data", {})
            reply_text = res_data.get("reply_text", "无回复内容")
            audio_url = res_data.get("audio_url")
            chat_history.append({"role": "user", "content": text})
            chat_history.append({"role": "assistant", "content": f"AI: {reply_text}"})
            output_audio_path = None
            if audio_url and need_tts:
                with httpx.Client() as client:
                    audio_res = client.get(f"http://127.0.0.1:8000{audio_url}")
                    if audio_res.status_code == 200:
                        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        temp_audio.write(audio_res.content)
                        temp_audio.close()
                        output_audio_path = temp_audio.name
            return chat_history, "", output_audio_path
        else:
            chat_history.append({"role": "user", "content": text})
            chat_history.append({"role": "assistant", "content": f"错误: {res_json.get('msg')}"})
            return chat_history, "", None
    except Exception as e:
        chat_history.append({"role": "user", "content": text})
        chat_history.append({"role": "assistant", "content": f"错误: {str(e)}"})
        return chat_history, "", None


def change_theme(theme_name):
    themes = {
        "深蓝色": gr.themes.Soft(primary_hue="blue"),
        "橙色": gr.themes.Soft(primary_hue="orange"),
        "绿色": gr.themes.Soft(primary_hue="green"),
        "紫色": gr.themes.Soft(primary_hue="indigo"),
        "红色": gr.themes.Soft(primary_hue="red"),
        "青色": gr.themes.Soft(primary_hue="cyan"),
    }
    return themes.get(theme_name, themes["深蓝色"])


init_settings = load_settings()
init_voice_name = [k for k, v in VOICE_CHOICES.items() if v == init_settings.get("voice", "zh-CN-XiaoxiaoNeural")]
init_voice_name = init_voice_name[0] if init_voice_name else "晓晓 (女)"


# =====================================================================
# 构建 Gradio 界面
# =====================================================================
with gr.Blocks(title="NeuVox 智能语音管家", theme=gr.themes.Soft(primary_hue="blue"), css=OVERLAY_CSS) as demo:

    settings_state = gr.State(value=init_settings)
    drawer_visible = gr.State(value=False)

    # ---- 遮罩层（默认隐藏） ----
    overlay = gr.Column(visible=False, elem_id="settings-overlay")

    # ---- 右浮窗（默认隐藏） ----
    drawer = gr.Column(visible=False, elem_id="settings-drawer")

    with drawer:
        with gr.Row():
            gr.Markdown("## ⚙️ 设置")
            close_btn = gr.Button("✕", size="sm", min_width=40, scale=0)

        with gr.Tabs():
            # ---- 个性化 ----
            with gr.TabItem("🎨 个性化"):
                theme_select = gr.Dropdown(
                    label="主题颜色",
                    choices=["深蓝色", "橙色", "绿色", "紫色", "红色", "青色"],
                    value=init_settings.get("theme", "深蓝色"),
                )
                reply_mode = gr.Radio(
                    label="回复模式",
                    choices=["仅语音", "仅文字", "语音+文字"],
                    value=init_settings.get("reply_mode", "语音+文字"),
                )
                volume = gr.Slider(
                    label="音量",
                    minimum=0, maximum=100, step=5,
                    value=init_settings.get("volume", 70),
                )
                voice_select = gr.Dropdown(
                    label="音色",
                    choices=list(VOICE_CHOICES.keys()),
                    value=init_voice_name,
                )

            # ---- 网络 ----
            with gr.TabItem("🌐 网络"):
                ws_address = gr.Textbox(
                    label="WebSocket 地址",
                    value=init_settings.get("ws_address", "ws://127.0.0.1:8001"),
                )
                ota_address = gr.Textbox(
                    label="OTA 地址",
                    value=init_settings.get("ota_address", "http://127.0.0.1:8003"),
                )

            # ---- 风格 ----
            with gr.TabItem("💬 风格"):
                reply_style = gr.Dropdown(
                    label="回复风格",
                    choices=list(STYLE_PROMPTS.keys()),
                    value=init_settings.get("reply_style", "友好专业"),
                )
                gr.Markdown(
                    "<span style='color: gray; font-size: 12px;'>"
                    "友好专业（默认）· 简洁直接（省废话）· 幽默风趣（轻松）· 严谨专业（准确）"
                    "</span>"
                )

            # ---- 参数 ----
            with gr.TabItem("⚙️ 参数"):
                temperature = gr.Slider(
                    label="Temperature（创造性）",
                    minimum=0.0, maximum=2.0, step=0.1,
                    value=init_settings.get("temperature", 0.7),
                )
                context_rounds = gr.Slider(
                    label="上下文轮数",
                    minimum=0, maximum=10, step=1,
                    value=init_settings.get("context_rounds", 3),
                )
                max_tokens = gr.Slider(
                    label="最大 Token",
                    minimum=256, maximum=4096, step=256,
                    value=init_settings.get("max_tokens", 2048),
                )
                plugins = gr.CheckboxGroup(
                    label="启用插件",
                    choices=["天气", "新闻", "搜索", "知识库"],
                    value=init_settings.get("plugins", ["天气", "新闻", "搜索", "知识库"]),
                )

        with gr.Row():
            apply_btn = gr.Button("💾 保存设置", variant="primary", scale=1)
            settings_status = gr.Markdown("")

    # ---- 顶部标题栏 ----
    with gr.Row():
        gr.Markdown("# NeuVox 智能语音管家")
        settings_btn = gr.Button("⚙️ 设置", scale=0, min_width=80, size="sm")

    gr.Markdown("<span style='color: gray; font-size: 14px;'>支持语音和文字输入，基于 DeepSeek + MiMo TTS</span>")

    # ---- 主对话区域 ----
    with gr.Row():
        with gr.Column(scale=7):
            chatbot = gr.Chatbot(
                label="对话历史",
                height=400,
                type="messages",
                allow_tags=False
            )
        with gr.Column(scale=3):
            audio_input = gr.Audio(
                label="发送语音",
                sources=["microphone"],
                type="filepath",
                interactive=True
            )
            audio_output = gr.Audio(
                label="AI 回复",
                interactive=False,
                autoplay=True
            )

    # 文本输入区域
    with gr.Row():
        text_input = gr.Textbox(
            label="文字输入",
            placeholder="输入消息...",
            scale=5
        )
        text_submit = gr.Button("发送", variant="primary", scale=1)
        clear_btn = gr.Button("清空", scale=1)

    # ---- 事件绑定 ----

    # 打开浮窗
    settings_btn.click(
        fn=toggle_drawer,
        inputs=[drawer_visible],
        outputs=[overlay, drawer, drawer_visible]
    )

    # 关闭浮窗（点击 X）
    close_btn.click(
        fn=toggle_drawer,
        inputs=[drawer_visible],
        outputs=[overlay, drawer, drawer_visible]
    )

    # 保存设置
    apply_btn.click(
        fn=apply_settings,
        inputs=[settings_state, theme_select, reply_mode, volume, voice_select,
                ws_address, ota_address, reply_style, temperature,
                context_rounds, max_tokens, plugins],
        outputs=[settings_state, settings_status]
    )

    # 主题切换
    theme_select.change(
        fn=change_theme,
        inputs=[theme_select],
        outputs=[demo]
    )

    # 语音输入
    audio_input.change(
        fn=process_voice_input,
        inputs=[audio_input, chatbot, settings_state],
        outputs=[chatbot, audio_output]
    )

    # 文本输入
    text_submit.click(
        fn=process_text_input,
        inputs=[text_input, chatbot, settings_state],
        outputs=[chatbot, text_input, audio_output]
    )
    text_input.submit(
        fn=process_text_input,
        inputs=[text_input, chatbot, settings_state],
        outputs=[chatbot, text_input, audio_output]
    )

    # 清空
    clear_btn.click(
        fn=lambda: ([], None),
        inputs=None,
        outputs=[chatbot, audio_output]
    )


if __name__ == "__main__":
    print("正在启动 NeuVox Web UI...")
    config_path = os.path.join(os.path.dirname(__file__), "configs", ".config.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        web_ui_config = config.get("web_ui", {})
        server_host = web_ui_config.get("host", "127.0.0.1")
        server_port = web_ui_config.get("port", 7860)
    except Exception as e:
        print(f"读取配置文件失败，使用默认值: {e}")
        server_host = "127.0.0.1"
        server_port = 7860
    print(f"监听地址: http://{server_host}:{server_port}")
    demo.launch(server_name=server_host, server_port=server_port)
