# test_controller.py
import os
import re
import json
import argparse
import config
from pathlib import Path

# === 导入各个模块 ===
from extraction_agent import extract_device_behavior
# 引入 generate_draft_model 用于在循环中创建新的修复 Agent
from modeling_agent import ReActAgent, generate_draft_model
from quality_checker import QualityChecker
from feedback_module import construct_feedback_prompt
from visualize_model import generate_visualization


def get_file_paths(input_file_path):
    """
    根据输入文件路径，自动清洗文件名，生成所有路径
    """
    path_obj = Path(input_file_path)
    base_name = path_obj.stem

    # 使用正则强制去除开头的 input_ 或 output_
    identifier = re.sub(r'^(input|output)_?', '', base_name, flags=re.IGNORECASE)

    return {
        "raw_input": str(path_obj),
        "behavior_txt": f"output_{identifier}.txt",
        "draft_json": f"draft_model_{identifier}.json",
        "verified_json": f"verified_model_{identifier}.json",
        "smv_file": f"final_model_{identifier}.smv",
        "graph_base": f"final_model_graph_{identifier}"
    }


def run_correction_pipeline(behavior_text, checker, initial_draft_json, paths):
    """
    运行 Check -> Feedback -> Refine 循环
    :param behavior_text: 原始行为描述文本 (用于初始化修复 Agent)
    :param checker: 质量检查器实例
    :param initial_draft_json: 初始模型 JSON
    :param paths: 文件路径字典
    """
    current_model_json = initial_draft_json
    feedback_to_agent = None

    for attempt in range(config.MAX_ITERATIONS):
        print(f"\n--- 修正尝试 {attempt + 1}/{config.MAX_ITERATIONS} ---")

        # 1. 如果有反馈，运行 Agent 进行修复
        if feedback_to_agent:
            print("[模块 2] 运行 ReAct 代理 (修正)...")
            # === 关键修改 ===
            # 我们不复用旧 agent，而是创建一个新的修复 Agent
            (status, model_json_or_error) = generate_draft_model(
                behavior_text,
                feedback_prompt=feedback_to_agent
            )

            if status == "ERROR":
                return ("FAILURE", model_json_or_error)
            current_model_json = model_json_or_error

        # 2. 保存中间调试用的 SMV 代码
        iter_smv_filename = f"debug_iter_{attempt + 1}_{paths['smv_file']}"
        checker.save_debug_smv(current_model_json, iter_smv_filename)
        print(f"  [调试] 本次迭代的 SMV 代码已保存至: {iter_smv_filename}")

        # 3. 运行质量检查
        print("[模块 3] 运行质量检查...")
        (passed, failure_reason) = checker.check(current_model_json)

        if passed:
            print("\n--- [SUCCESS] 模型验证通过 ---")
            return ("SUCCESS", current_model_json)

        print(f"--- 质量检查失败: {failure_reason} ---")
        if attempt == config.MAX_ITERATIONS - 1: break

        # 4. 构建反馈
        print("[模块 4] 构建反馈...")
        feedback_to_agent = construct_feedback_prompt(current_model_json, failure_reason)

    return ("FAILURE", "达到最大尝试次数")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", nargs='?', default="input_2.txt", help="原始 OCR 文件")
    args = parser.parse_args()
    paths = get_file_paths(args.input_file)

    print(f"=== 启动全流程自动化: {paths['raw_input']} ===")

    # 1. [模块 1] 行为提取
    behavior_text = ""
    if os.path.exists(paths['behavior_txt']):
        print(f"[系统] 检测到已有行为描述 '{paths['behavior_txt']}'，直接加载。")
        with open(paths['behavior_txt'], "r", encoding="utf-8") as f:
            behavior_text = f.read()
    else:
        print(f"[模块 1] 正在从 '{paths['raw_input']}' 提取设备行为...")
        if not os.path.exists(paths['raw_input']):
            print(f"FATAL: 文件 '{paths['raw_input']}' 未找到。")
            exit(1)

        with open(paths['raw_input'], "r", encoding="utf-8") as f:
            raw_ocr = f.read()

        behavior_text = extract_device_behavior(raw_ocr)

        with open(paths['behavior_txt'], "w", encoding="utf-8") as f:
            f.write(behavior_text)
        print(f"[模块 1] 提取完成，已保存至 '{paths['behavior_txt']}'")

    # 2. [模块 2] 初始化相关对象
    print("[模块 2] 初始化 ReAct Agent...")
    checker = QualityChecker()

    # 3. 生成/加载初始草稿
    draft_json = ""
    if os.path.exists(paths['draft_json']):
        print(f"[系统] 加载已有草稿 '{paths['draft_json']}'...")
        with open(paths['draft_json'], "r", encoding="utf-8") as f:
            draft_json = f.read()
    else:
        print("[模块 2] 生成初始模型草稿...")
        # 初始生成不需要 feedback
        status, result = generate_draft_model(behavior_text, feedback_prompt=None)
        if status == "ERROR":
            print(f"FATAL: 初始建模失败: {result}")
            exit(1)
        draft_json = result
        with open(paths['draft_json'], "w", encoding="utf-8") as f:
            f.write(draft_json)

    # 4. [模块 3 & 4] 运行修正循环
    # === 关键修改：传入 behavior_text 而不是 agent 对象 ===
    status, result = run_correction_pipeline(behavior_text, checker, draft_json, paths)

    if status == "SUCCESS":
        # 5. 保存最终结果
        try:
            parsed = json.loads(result)
            with open(paths['verified_json'], "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=4, ensure_ascii=False)

            print(f"[导出] 生成 NuSMV 代码 -> {paths['smv_file']}")
            checker.save_smv_file(json.dumps(parsed), paths['smv_file'])

            print(f"[可视化] 生成图片 -> {paths['graph_base']}.png")
            generate_visualization(paths['verified_json'], paths['graph_base'])

            print("\n=== ✅ 全流程执行完毕 ===")
        except Exception as e:
            print(f"保存结果时出错: {e}")
    else:
        print(f"\n=== ❌ 流程失败: {result} ===")