"""
# llm_api_client.py
import openai
import config
from openai import OpenAI

# 设置 API 密钥
# (如果您在使用 DeepSeek, 请确保 base_url 也已设置)
client = OpenAI(
    api_key=config.API_KEY,
    # 必须改为硅基流动的地址
    base_url="https://api.siliconflow.cn/v1"
)


def call_llm(prompt_text: str, model: str = config.LLM_MODEL_NAME) -> str:

    print(f"\n--- [LLM Call] Sending prompt to {model} ---")
    # print(prompt_text) # (取消注释以调试完整的提示词)
    print("--- [LLM Call] Waiting for response... ---")

    try:
        response = client.chat.completions.create(
            model=model,
            # === 这是已修复的部分 ===
            messages=[
                {"role": "user", "content": prompt_text}
            ],
            # ========================
            temperature=0.2  # 降低随机性以获取可复现的模型
        )
        content = response.choices[0].message.content
        print("--- [LLM Call] Response received ---")
        return content
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return f"Error: LLM API call failed. {e}"
"""


"""
# llm_api_client.py
import openai
import config

# === 设置 API 密钥和地址 (旧版写法) ===
openai.api_key = config.API_KEY
# 重要：旧版本 SDK 使用 'api_base' 而不是 'base_url'
openai.api_base = "https://api.siliconflow.cn/v1"


def call_llm(prompt_text: str, model: str = config.LLM_MODEL_NAME) -> str:

    print(f"\n--- [LLM Call] Sending prompt to {model} ---")
    # print(prompt_text) # (取消注释以调试完整的提示词)
    print("--- [LLM Call] Waiting for response... ---")

    try:
        # === 旧版调用方式 ===
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.2  # 降低随机性以获取可复现的模型
        )

        # 获取内容。如果运行报错，可以尝试注释掉下面一行，改用字典访问方式：
        # content = response['choices'][0]['message']['content']
        content = response.choices[0].message.content

        print("--- [LLM Call] Response received ---")
        return content
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return f"Error: LLM API call failed. {e}"
    
"""
# llm_api_client.py
import requests
import json
import config


def call_llm(prompt_text: str, model: str = config.LLM_MODEL_NAME) -> str:
    """
    使用 requests 库直接调用 LLM API (兼容所有 Python 版本)。
    """
    print(f"\n--- [LLM Call] Sending prompt to {model} ---")
    print("--- [LLM Call] Waiting for response... ---")

    # 硅基流动 API 地址
    url = "https://api.siliconflow.cn/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {config.API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.2,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)

        # 检查 HTTP 响应状态码
        if response.status_code == 200:
            result = response.json()
            # 解析返回的 JSON 结构
            content = result['choices'][0]['message']['content']
            print("--- [LLM Call] Response received ---")
            return content
        else:
            print(f"API Error: Status Code {response.status_code}")
            print(f"Response Body: {response.text}")
            return f"Error: API returned status code {response.status_code}"

    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return f"Error: LLM API call failed. {e}"