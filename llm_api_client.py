# llm_api_client.py
import requests
import json
import config
import time


def call_llm(prompt_text: str, model: str = config.LLM_MODEL_NAME) -> str:
    """
    使用 requests 库调用 DeepSeek/OpenAI 兼容 API。
    """
    print(f"\n--- [LLM Call] Sending prompt to {model} ---")

    # 优先使用 config 中定义的 URL，如果没有则默认 DeepSeek 官方
    url = getattr(config, "API_URL", "https://api.deepseek.com/chat/completions")

    headers = {
        "Authorization": f"Bearer {config.API_KEY}",
        "Content-Type": "application/json"
    }

    # DeepSeek 推荐的参数设置
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.1,  # 降低温度以获得更稳定的输出
        "stream": False,
        "max_tokens": 4096
    }

    MAX_RETRIES = 5

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=300)

            if response.status_code == 200:
                result = response.json()
                # 兼容不同的返回结构
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    print("--- [LLM Call] Response received ---")
                    return content
                else:
                    print(f"API Error: Unexpected JSON format: {result}")
                    return "Error: API response format invalid."

            elif response.status_code == 429:
                wait_time = 2 ** attempt
                print(f"API Warning: Rate limited (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

            else:
                print(f"API Error: Status Code {response.status_code}")
                print(f"Response Body: {response.text}")
                return f"Error: API returned status code {response.status_code}"

        except requests.exceptions.Timeout:
            print("API Warning: Request timed out. Retrying...")
            time.sleep(5)
            continue

        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return f"Error: LLM API call failed. {e}"

    return "Error: LLM API call failed after max retries."