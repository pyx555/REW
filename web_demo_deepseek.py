# web_demo_deepseek.py
import gradio as gr
import requests
import json
import config  # 复用你的配置文件


def format_history(history, current_message):
    """
    将 Gradio 的历史记录 [[q1, a1], [q2, a2]] 转换为 DeepSeek API 的 messages 格式
    """
    messages = []
    # 添加系统提示词，保证模型行为符合预期
    messages.append({
        "role": "system",
        "content": "You are a helpful formal verification assistant using DeepSeek-V3."
    })

    for user_msg, bot_msg in history:
        if user_msg:
            messages.append({"role": "user", "content": user_msg})
        if bot_msg:
            messages.append({"role": "assistant", "content": bot_msg})

    # 添加当前用户输入
    messages.append({"role": "user", "content": current_message})
    return messages


def chat_with_deepseek(message, history):
    """
    调用 API 并返回回复
    """
    if not message:
        return "", history

    # 1. 准备消息上下文
    messages = format_history(history, message)

    # 2. 准备请求头和数据
    headers = {
        "Authorization": f"Bearer {config.API_KEY}",
        "Content-Type": "application/json"
    }

    # 优先使用 config 中的 URL，如果没有则使用默认
    api_url = getattr(config, "API_URL", "https://api.deepseek.com/chat/completions")

    payload = {
        "model": getattr(config, "LLM_MODEL_NAME", "deepseek-chat"),
        "messages": messages,
        "temperature": 0.1,  # 保持低温以获得准确回答
        "stream": True,  # 开启流式输出，体验更好
        "max_tokens": 4096
    }

    try:
        # 3. 发起流式请求
        response = requests.post(api_url, headers=headers, json=payload, stream=True, timeout=60)

        if response.status_code != 200:
            error_msg = f"Error: API returned {response.status_code} - {response.text}"
            yield "", history + [[message, error_msg]]
            return

        # 4.逐步解析流式响应
        partial_response = ""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    json_str = decoded_line[6:]  # 去掉 'data: ' 前缀
                    if json_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(json_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                partial_response += content
                                # 实时 yield 更新界面
                                yield "", history + [[message, partial_response]]
                    except json.JSONDecodeError:
                        pass

    except Exception as e:
        error_msg = f"Network Error: {str(e)}"
        yield "", history + [[message, error_msg]]


# --- 构建 Gradio 界面 ---
with gr.Blocks(title="DeepSeek Chat Demo", theme=gr.themes.Soft()) as demo:
    gr.HTML("""<h1 align="center">🤖 DeepSeek-V3 Formal Verification Chatbot</h1>""")
    gr.Markdown("这是一个基于你本地配置 (config.py) 的 DeepSeek 在线交互界面。")

    chatbot = gr.Chatbot(height=600, show_copy_button=True)

    with gr.Row():
        with gr.Column(scale=8):
            msg = gr.Textbox(
                show_label=False,
                placeholder="输入你的问题，或者粘贴一段设备描述...",
                lines=2,
                container=False
            )
        with gr.Column(scale=1, min_width=50):
            submit_btn = gr.Button("🚀 发送", variant="primary")

    with gr.Row():
        clear_btn = gr.Button("🗑️ 清空对话")

    # 绑定事件
    # 回车提交
    msg.submit(chat_with_deepseek, [msg, chatbot], [msg, chatbot])
    # 按钮提交
    submit_btn.click(chat_with_deepseek, [msg, chatbot], [msg, chatbot])
    # 清空按钮
    clear_btn.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    # 在本地 7860 端口启动
    print("启动 Web 界面中... 请在浏览器访问 http://127.0.0.1:7860")
    demo.queue().launch(server_name="127.0.0.1", server_port=7860, share=False)