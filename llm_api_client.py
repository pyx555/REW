# llm_api_client.py
import requests
import json
import config
import time # <-- 确保添加此导入

# ... (旧版的 OpenAI SDK 或旧版的 requests 实现请保留在文件中，仅修改第三部分)

def call_llm(prompt_text: str, model: str = config.LLM_MODEL_NAME) -> str:
    """
    使用 requests 库直接调用 LLM API (兼容所有 Python 版本)。
    (已修复：添加了对 429 错误的代码重试机制，并将超时增加到 300 秒)
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

    MAX_RETRIES = 5  # 我们最多重试 5 次

    for attempt in range(MAX_RETRIES):
        try:
            # 修正: 增加超时时间到 300 秒（5 分钟）
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=300)

            # 检查 HTTP 响应状态码
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print("--- [LLM Call] Response received ---")
                return content

            elif response.status_code == 429:
                # 处理限速错误 (429)
                print(f"API Warning: Status Code 429 - Rate limited. Retrying in {2**attempt} seconds...")
                if attempt < MAX_RETRIES - 1:
                    # 指数退避：第一次等待 1s, 第二次 2s, 第三次 4s, 以此类推
                    time.sleep(2**attempt)
                    continue # 继续下一次循环重试
                else:
                    # 最后一次尝试失败，直接退出
                    print("API Error: Status Code 429. Max retries reached.")
                    return f"Error: API returned status code 429 after {MAX_RETRIES} retries."

            else:
                # 处理其他非 200/429 的错误
                print(f"API Error: Status Code {response.status_code}")
                print(f"Response Body: {response.text}")
                return f"Error: API returned status code {response.status_code}"

        except requests.exceptions.ReadTimeout:
            # 处理 Read timed out 错误 (之前遇到的问题)
            print("API Warning: Read timed out. Retrying in 5 seconds...")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
                continue
            else:
                print("API Error: Read timed out. Max retries reached.")
                return "Error: LLM API call failed due to persistent read timeout."

        except Exception as e:
            # 处理其他网络/连接错误
            print(f"Error calling LLM API: {e}")
            return f"Error: LLM API call failed. {e}"

    # 如果循环正常退出（不应该发生，但作为安全措施）
    return "Error: LLM API call failed unexpectedly."