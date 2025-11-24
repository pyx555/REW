import os
import json
import config  # 确保你有 config.py 并且定义了 MAX_ITERATIONS

# 导入所有需要的模块
from modeling_agent import ReActAgent
from quality_checker import QualityChecker
from feedback_module import construct_feedback_prompt
# 我们仍然需要 extraction_agent 来获取原始文本，
# 以便 ReAct 代理在修正时有上下文（用于 search/lookup）
from extraction_agent import extract_device_behavior


def run_correction_pipeline(ocr_text: str, initial_draft_json: str):
    """
    运行一个修正循环。

    1. 使用 ocr_text 初始化 Agent (用于上下文)。
    2. 使用 initial_draft_json 作为第一次检查的输入。
    3. 循环：Check -> Feedback -> Refine (by Agent)
    """

    print("=== [START] 修正流水线启动 ===")

    # === 步骤 1: 初始化 ===
    print("[模块 2] 初始化 ReAct 代理 (需要 OCR 文本作为上下文)...")
    # Agent 必须用原始行为描述来初始化，
    # 否则它无法使用 'search' 或 'lookup' 动作来修复模型。
    agent = ReActAgent(ocr_text)

    print("[模块 3] 初始化质量检查器...")
    checker = QualityChecker()

    current_model_json = initial_draft_json
    feedback_to_agent = None

    # === 核心迭代循环 (IV.D) ===
    for attempt in range(config.MAX_ITERATIONS):
        print(f"\n--- 修正尝试 {attempt + 1}/{config.MAX_ITERATIONS} ---")

        if feedback_to_agent:
            # === [尝试 2, 3, ...] ===
            # 这不是第一次尝试，我们现在要求 Agent 根据反馈进行修正
            print("[模块 2] 运行 ReAct 代理 (执行修正)...")
            (status, model_json_or_error) = agent.run(feedback=feedback_to_agent)

            if status == "ERROR":
                print(f"--- 建模失败 ---")
                return ("FAILURE", f"Agent 未能生成修正模型: {model_json_or_error}")

            current_model_json = model_json_or_error
            print(f"\n--- [中间输出] 修正尝试 {attempt + 1} 生成的模型 ---")
            try:
                parsed_temp_model = json.loads(current_model_json)
                print(json.dumps(parsed_temp_model, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                print(current_model_json)
            print("-" * 50)

        else:
            # === [尝试 1] ===
            # 这是第一次尝试，我们不运行 agent.run()，
            # 我们直接使用用户提供的 'initial_draft_json'
            print(f"--- [输入] 正在检查初始模型草稿 'draft_model_1s.json' ---")
            # (current_model_json 已经在循环外被设置为 initial_draft_json)

        # === 步骤 3 (执行): 质量检查 ===
        print("[模块 3] 运行质量检查...")
        (passed, failure_reason) = checker.check(current_model_json)

        if passed:
            # 成功！
            print("\n--- 模型验证成功 ---")
            return ("SUCCESS", current_model_json)

        # === 步骤 4: 准备反馈 (IV.D) ===
        print(f"--- 质量检查失败 ---")
        print(f"原因: {failure_reason}")

        # 检查是否这是最后一次尝试
        if attempt == config.MAX_ITERATIONS - 1:
            break  # 达到最大次数，退出循环

        print("[模块 4] 正在构建反馈提示词...")
        feedback_to_agent = construct_feedback_prompt(current_model_json, failure_reason)
        # 循环将继续，feedback_to_agent 将在下一次 agent.run() 中被使用

    print(f"\n--- 建模失败 (达到最大尝试次数 {config.MAX_ITERATIONS}) ---")
    return ("FAILURE", "Max attempts reached. Model could not be verified.")


# --- 主执行 ---
if __name__ == "__main__":

    print("==================================================")
    print("      启动 LLM 模型修正循环测试脚本      ")
    print("==================================================")

    input_ocr_file = "input_1s.txt"
    input_draft_file = "draft_model_1s.json"

    # 1. 加载 OCR 文本 (为 Agent 提供上下文)
    try:
        with open(input_ocr_file, "r", encoding="utf-8") as f:
            # 我们不需要运行 extract_device_behavior，
            # 因为 ReAct Agent 的 prompt 应该使用 *全部* 原始文本
            ocr_manual_text = f.read()
        print(f"成功加载 OCR 文本 '{input_ocr_file}' (用于 Agent 上下文).")
    except FileNotFoundError:
        print(f"FATAL ERROR: '{input_ocr_file}' 未找到。")
        print("Agent 需要此文件来进行 'search' 和 'lookup' 以修复模型。")
        exit(1)

    # 2. 加载初始模型草稿 (作为循环的起点)
    try:
        with open(input_draft_file, "r", encoding="utf-8") as f:
            draft_model_json = f.read()
        print(f"成功加载初始模型草稿 '{input_draft_file}'.")
    except FileNotFoundError:
        print(f"FATAL ERROR: '{input_draft_file}' 未找到。")
        print("请创建此文件，并填入你希望测试的初步模型 JSON。")
        exit(1)
    except json.JSONDecodeError:
        print(f"FATAL ERROR: '{input_draft_file}' 中的内容不是有效的 JSON。")
        exit(1)

    # 3. 运行修正流水线
    (final_status, final_result) = run_correction_pipeline(ocr_manual_text, draft_model_json)

    if final_status == "SUCCESS":
        print("\n=== 最终验证通过的模型 (JSON) ===")
        print(final_result)

        output_filename = "verified_model_from_draft.json"
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(json.loads(final_result), f, indent=4, ensure_ascii=False)
            print(f"\n最终模型已保存到 '{output_filename}'")
        except Exception as e:
            print(f"\n保存文件时出错: {e}")
    else:
        print(f"\n=== 修正失败 ===")
        print(final_result)