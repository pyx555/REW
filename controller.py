# controller.py
import config
from extraction_agent import extract_device_behavior
from modeling_agent import ReActAgent
from quality_checker import QualityChecker
from feedback_module import construct_feedback_prompt
# controller.py 顶部
import json  # <--- 确保这一行存在
import config
from extraction_agent import extract_device_behavior
# ... 其他导入


def run_full_pipeline(ocr_text: str) -> (str, str):
    # === 步骤 1: 行为提取 (IV.A)  ===
    behavior_description = extract_device_behavior(ocr_text)

    # === 步骤 2: 初始化建模代理 (IV.B)  ===
    agent = ReActAgent(behavior_description)

    # === 步骤 3: 初始化质量检查器 (IV.C)  ===
    checker = QualityChecker()

    feedback_to_agent = None

    # === 核心迭代循环 (IV.D)  ===
    for attempt in range(config.MAX_ITERATIONS):
        print(f"\n--- Modeling Attempt {attempt + 1}/{config.MAX_ITERATIONS} ---")

        # === 步骤 2 (执行): 自动建模 ===
        print("[Module 2] Running ReAct modeling agent...")
        (status, model_json_or_error) = agent.run(feedback=feedback_to_agent)

        if status == "ERROR":
            print(f"--- Modeling FAILED ---")
            return ("FAILURE", f"Agent failed to produce model: {model_json_or_error}")

        #model_json = model_json_or_error
        model_json = model_json_or_error

        # === [新增功能] 中间输出：打印当前轮次生成的初步模型 ===
        print(f"\n--- [Intermediate Output] Attempt {attempt + 1} Generated Model ---")
        try:
            # 尝试解析并美化打印 JSON，方便阅读
            parsed_temp_model = json.loads(model_json)
            print(json.dumps(parsed_temp_model, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            # 如果生成的不是标准 JSON（虽然不太可能，但防万一），直接打印原始字符串
            print(model_json)
        print("-" * 50)
        # ========================================================

        # === 步骤 3 (执行): 质量检查 ===
        (passed, failure_reason) = checker.check(model_json)

        # === 步骤 3 (执行): 质量检查 ===
        (passed, failure_reason) = checker.check(model_json)

        if passed:
            # 成功！
            print("\n--- Model Verification SUCCESSFUL ---")
            return ("SUCCESS", model_json)

        # === 步骤 4: 准备反馈 (IV.D)  ===
        print(f"--- Quality Check FAILED ---")
        print(f"Reason: {failure_reason}")
        feedback_to_agent = construct_feedback_prompt(model_json, failure_reason)
        # 循环将继续，feedback_to_agent 将在下一次 agent.run() 中被使用

    print(f"\n--- Modeling FAILED after {config.MAX_ITERATIONS} attempts ---")
    return ("FAILURE", "Max attempts reached. Model could not be verified.")


# --- 主执行 ---
if __name__ == "__main__":

    print("==================================================")
    print(" Starting LLM-based Device Modeling Pipeline ")
    print("==================================================")

    # 加载  中提到的输入文件
    try:
        with open("input_1s.txt", "r", encoding="utf-8") as f:
            ocr_manual_text = f.read()
    except FileNotFoundError:
        print("FATAL ERROR: 'input_1s.txt' not found.")
        print("Please create the file with the OCR content from the manual.")
        exit(1)

    (final_status, final_result) = run_full_pipeline(ocr_manual_text)

    if final_status == "SUCCESS":
        print("\n=== FINAL VERIFIED MODEL (JSON) ===")
        print(final_result)
        # 保存到文件
        try:
            with open("verified_model_1s.json", "w", encoding="utf-8") as f:
                json.dump(json.loads(final_result), f, indent=4, ensure_ascii=False)
            print("\nFinal model saved to 'verified_model_1s.json'")
        except Exception as e:
            print(f"\nError saving model to file: {e}")
    else:
        print(f"\n=== MODELING FAILED ===")
        print(final_result)