# extraction_agent.py
import argparse
import os
import re

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
    # === 命令行模式 (单独运行时执行) ===
    parser = argparse.ArgumentParser(description="模块 1: 设备行为提取")
    parser.add_argument("input_file", nargs='?', default="input_2.txt", help="OCR 源文件路径")
    parser.add_argument("output_file", nargs='?', default=None, help="输出文件路径 (可选)")
    args = parser.parse_args()

    # 1. 确定文件名
    input_path = args.input_file
    if args.output_file:
        output_path = args.output_file
    else:
        # === 修改处 ===
        base = os.path.splitext(os.path.basename(input_path))[0]
        identifier = re.sub(r'^(input|output)_?', '', base, flags=re.IGNORECASE)
        output_path = f"output_{identifier}.txt"

    # 2. 运行提取
    if not os.path.exists(input_path):
        print(f"Error: 文件 '{input_path}' 不存在.")
        exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    behavior_desc = extract_device_behavior(raw_text)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(behavior_desc)

    print(f"结果已保存至: {output_path}")