# extraction_agent.py
import prompts
from llm_api_client import call_llm
import config


def extract_device_behavior(ocr_text: str) -> str:
    """
    调用LLM执行OCR纠错和设备行为提取。
    对应论文 IV.A 节 [1]。

    参数:
        ocr_text (str): 从设备手册OCR得到的原始文本。

    返回:
        str: 经过LLM纠错和提炼的行为描述。
    """
    print("[Module 1] Starting behavior extraction...")

    # 从 prompts.py 加载表I的提示词模板
    prompt_template = prompts.GET_BEHAVIOR_EXTRACTION_PROMPT()

    # 将OCR文本注入到提示词的"Input"部分
    full_prompt = prompt_template.format(ocr_input=ocr_text)

    # 调用LLM API
    behavior_description = call_llm(full_prompt, model=config.LLM_MODEL_NAME)

    print("[Module 1] Behavior extraction complete.")
    return behavior_description


if __name__ == "__main__":
    import os

    # 指定输入和输出文件名
    input_filename = 'input_1s.txt'
    output_filename = 'output_1s.txt' # <--- 这是您希望的输出文件

    # 检查文件是否存在
    if not os.path.exists(input_filename):
        print(f"Error: 找不到文件 '{input_filename}'。请确保它和当前脚本在同一目录下。")
    else:
        try:
            print(f"=== 正在读取 {input_filename} ===")
            # 使用 utf-8 编码读取
            with open(input_filename, 'r', encoding='utf-8') as f:
                file_ocr_content = f.read()

            if not file_ocr_content.strip():
                print("Warning: 文件内容为空！")
            else:
                print(f"成功读取 {len(file_ocr_content)} 个字符。")
                print("=== 开始执行行为提取 (这可能需要几十秒) ===")

                # 调用核心函数
                result = extract_device_behavior(file_ocr_content)

                print("\n=== 最终提取结果 (预览) ===")
                print(result[:1000] + "...") # 打印结果的前1000个字符作为预览

                # --- [已修改] ---
                # 将结果保存到 'output_1s.txt'
                print(f"\n=== 正在保存结果到 {output_filename} ===")
                with open(output_filename, 'w', encoding='utf-8') as f_out:
                    f_out.write(result)
                print(f"结果已成功保存到 {output_filename}")
                # --------------

        except Exception as e:
            print(f"\n!!! 运行出错!!!\n{e}")