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

# 后端 API 地址
API_URL = "http://127.0.0.1:8000/api/v1/ask"


def process_voice_input(audio_path, chat_history):
    """处理音频输入"""
    if audio_path is None:
        return chat_history, None
    
    session_id = "gradio_session_001"
    
    try:
        with open(audio_path, "rb") as f:
            files = {"audio_file": (os.path.basename(audio_path), f, "audio/wav")}
            data = {"session_id": session_id, "need_tts": "true"}
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(API_URL, data=data, files=files)
                response.raise_for_status()
        
        res_json = response.json()
        
        if res_json.get("code") == 200:
            res_data = res_json.get("data", {})
            recognized_text = res_data.get("recognized_text", "未识别到语音")
            reply_text = res_data.get("reply_text", "无回复内容")
            audio_url = res_data.get("audio_path")
            
            chat_history.append({"role": "user", "content": f"语音: {recognized_text}"})
            chat_history.append({"role": "assistant", "content": f"AI: {reply_text}"})
            
            output_audio_path = None
            if audio_url:
                with httpx.Client() as client:
                    audio_res = client.get(f"http://127.0.0.1:8000{audio_url}")
                    if audio_res.status_code == 200:
                        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
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


def process_text_input(text, chat_history):
    """处理文本输入"""
    if not text or not text.strip():
        return chat_history, "", None
    
    session_id = "gradio_session_001"
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                API_URL,
                data={"session_id": session_id, "text": text, "need_tts": "true"}
            )
            response.raise_for_status()
        
        res_json = response.json()
        
        if res_json.get("code") == 200:
            res_data = res_json.get("data", {})
            reply_text = res_data.get("reply_text", "无回复内容")
            audio_url = res_data.get("audio_path")
            
            chat_history.append({"role": "user", "content": text})
            chat_history.append({"role": "assistant", "content": f"AI: {reply_text}"})
            
            output_audio_path = None
            if audio_url:
                with httpx.Client() as client:
                    audio_res = client.get(f"http://127.0.0.1:8000{audio_url}")
                    if audio_res.status_code == 200:
                        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
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
    """切换主题"""
    themes = {
        "深蓝色": gr.themes.Soft(primary_hue="blue"),
        "橙色": gr.themes.Soft(primary_hue="orange"),
        "绿色": gr.themes.Soft(primary_hue="green"),
        "紫色": gr.themes.Soft(primary_hue="indigo"),
        "红色": gr.themes.Soft(primary_hue="red"),
        "青色": gr.themes.Soft(primary_hue="cyan"),
    }
    return themes.get(theme_name, themes["深蓝色"])


# =====================================================================
# 构建 Gradio 界面
# =====================================================================
with gr.Blocks(title="NeuVox 智能语音管家", theme=gr.themes.Soft(primary_hue="blue")) as demo:
    
    gr.Markdown("# NeuVox 智能语音管家")
    gr.Markdown("<span style='color: gray; font-size: 14px;'>支持语音和文字输入，基于 DeepSeek + MiMo TTS</span>")
    
    # 主题选择
    with gr.Row():
        theme_select = gr.Dropdown(
            label="选择主题颜色",
            choices=["深蓝色", "橙色", "绿色", "紫色", "红色", "青色"],
            value="深蓝色",
            scale=1
        )
    
    with gr.Row():
        # 左侧区域
        with gr.Column(scale=7):
            chatbot = gr.Chatbot(
                label="对话历史", 
                height=400,
                type="messages",
                allow_tags=False
            )
            
        # 右侧区域
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

    # 绑定语音事件
    audio_input.change(
        fn=process_voice_input,
        inputs=[audio_input, chatbot],
        outputs=[chatbot, audio_output]
    )
    
    # 绑定文本事件
    text_submit.click(
        fn=process_text_input,
        inputs=[text_input, chatbot],
        outputs=[chatbot, text_input, audio_output]
    )
    
    text_input.submit(
        fn=process_text_input,
        inputs=[text_input, chatbot],
        outputs=[chatbot, text_input, audio_output]
    )
    
    # 绑定清空事件
    clear_btn.click(
        fn=lambda: ([], None),
        inputs=None,
        outputs=[chatbot, audio_output]
    )
    
    # 绑定主题切换
    theme_select.change(
        fn=change_theme,
        inputs=[theme_select],
        outputs=[demo]
    )


if __name__ == "__main__":
    print("正在启动 NeuVox Web UI...")
    
    # 从配置文件读取 Web UI 服务器设置
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
