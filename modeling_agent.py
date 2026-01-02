# modeling_agent.py
import os
import argparse
import json
import re
import prompts
import config
from llm_api_client import call_llm


class ReActAgent:
    """
    实现论文 IV.B 节 [1] 中的 ReAct 代理。
    支持两种模式：
    1. 初始建模 (Initial Modeling): 从头生成模型。
    2. 迭代修复 (Iterative Repair): 根据反馈修正模型。
    """

    def __init__(self, behavior_description: str, prompt_override: str = None):
        """
        :param behavior_description: 设备行为描述文本
        :param prompt_override: (可选) 如果传入此参数，将忽略默认 Prompt，直接使用此内容。
                                这用于传入 Module 4 构建好的“修复指令”。
        """
        self.behavior_description = behavior_description
        self.history = []
        self.max_turns = 8  # 限制最大轮数，防止无限消耗 Token

        if prompt_override:
            # === 修复模式 ===
            # 直接使用 Feedback Module 生成的完整 Prompt
            self.initial_prompt = prompt_override
            self.mode = "REPAIR"
        else:
            # === 初始模式 ===
            # 加载默认的建模 Prompt
            self.initial_prompt = prompts.GET_REACT_MODELING_PROMPT().replace(
                "{behavior_input}", self.behavior_description
            )
            self.mode = "INIT"

    def _call_llm(self) -> str:
        """ 构造完整提示词并调用 LLM """
        # 将历史记录拼接，形成上下文
        full_prompt = self.initial_prompt + "\n" + "\n".join(self.history)
        return call_llm(full_prompt, model=config.LLM_MODEL_NAME)

    def _parse_action(self, response: str) -> (str, str):
        """
        强力解析器 V5 (防逗号丢失版)：
        1. 自动挽救 Action 缺失。
        2. 自动修复 JSON 中常见的语法错误（缺失逗号、尾部逗号）。
        """
        try:
            content_after_action = ""

            # --- 步骤 1: 寻找 Action 或 JSON ---
            match_start = re.search(r"Action:", response, re.IGNORECASE)
            if match_start:
                content_after_action = response[match_start.end():].strip()
            else:
                # Auto-Fix: 直接找 JSON 块
                json_match = re.search(r"(\{.*\"states\".*\"transitions\".*\})", response, re.DOTALL)
                if json_match:
                    print("  [Auto-Fix] 检测到 JSON 但缺失 'Action:' 前缀。自动修复为 finish 动作...")
                    content_after_action = f"finish[{json_match.group(1)}]"
                else:
                    return "error", "No 'Action:' keyword found."

            # --- 步骤 2: 提取动作名 ---
            name_match = re.match(r"[\s`*\"']*(search|lookup|finish)[\s`*\"']*(?=\[)", content_after_action,
                                  re.IGNORECASE)
            if not name_match:
                return "error", "Found 'Action:', but unrecognized command."

            action_name = name_match.group(1).lower()
            start_bracket = content_after_action.find('[')

            if action_name == "finish":
                # --- 步骤 3: 提取并清洗 JSON ---
                json_start = content_after_action.find('{', start_bracket)
                json_end = content_after_action.rfind('}')

                if json_start != -1 and json_end != -1:
                    raw_json = content_after_action[json_start:json_end + 1]

                    # 1. 去掉 Markdown
                    clean_json = re.sub(r"^```[a-zA-Z]*", "", raw_json).replace("```", "").strip()

                    # === 核心修复：自动补全缺失的逗号 ===
                    # 将 "} {" 替换为 "}, {" (允许中间有换行和空格)
                    clean_json = re.sub(r"}\s*\{", "}, {", clean_json)

                    # === 核心修复：去除尾部多余逗号 ===
                    # 将 ", ]" 替换为 "]"
                    clean_json = re.sub(r",\s*]", "]", clean_json)

                    try:
                        json.loads(clean_json)  # 校验
                        return "finish", clean_json
                    except json.JSONDecodeError as e:
                        # 如果还报错，打印出来看看哪错了，但在生产环境中通常只能重试
                        return "error", f"JSON Syntax Error: {e}"
                else:
                    return "error", "Invalid JSON structure."

            else:
                # 处理 search/lookup
                arg_match = re.search(r"\[(.*?)\]", content_after_action, re.DOTALL)
                return (action_name, arg_match.group(1).strip()) if arg_match else ("error", "Missing args.")

        except Exception as e:
            return "error", f"Parsing exception: {e}"

    def _execute_action(self, action_name: str, argument: str) -> str:
        """ 执行动作 """
        print(f"  [Action] {action_name}: {argument[:50]}..." if len(
            argument) > 50 else f"  [Action] {action_name}: {argument}")

        if action_name == "search":
            if argument.lower() in self.behavior_description.lower():
                return f"Found text related to '{argument}'."
            else:
                return f"'{argument}' not found."

        elif action_name == "lookup":
            sentences = self.behavior_description.split('\n')
            found_lines = [s.strip() for s in sentences if argument.lower() in s.lower()]
            if found_lines:
                return f"Lookup results:\n" + "\n".join(found_lines[:3])  # 只返回前3条
            return "No specific sentence found."

        elif action_name == "finish":
            return argument

        else:
            return f"Unknown action: {action_name}"

    def run(self) -> (str, str):
        """
        运行 ReAct 循环。
        """
        # 如果是修复模式，Agent 已经带着 Feedback Prompt 初始化了，直接开始

        for turn in range(self.max_turns):
            response = self._call_llm()

            # === 可视化 Thought (方便调试) ===
            # 尝试提取 Thought 部分打印出来
            thought_match = re.search(r"Thought:(.*?)(Action:|$)", response, re.DOTALL | re.IGNORECASE)
            if thought_match:
                thought_text = thought_match.group(1).strip()
                print(f"\n[Thought] {thought_text}\n")

            # 将模型的回答加入历史
            self.history.append(response)

            action_name, argument = self._parse_action(response)

            if action_name == "error":
                observation = f"System Error: {argument}. Please strictly follow the format: Action: finish[{{...}}]"
                self.history.append(f"Observation: {observation}")
                print(f"  [Error Feedback] {observation}")
                continue

            if action_name == "finish":
                print("  'finish' action called.")
                return ("SUCCESS", argument)

            else:
                # search / lookup
                observation = self._execute_action(action_name, argument)
                self.history.append(f"Observation: {observation}")

        return ("ERROR", "Max turns reached without 'finish' action.")


# ==========================================
# 功能函数 API
# ==========================================
def generate_draft_model(behavior_text: str, feedback_prompt: str = None) -> (str, str):
    """
    生成或修复模型。
    :param behavior_text: 原始行为描述
    :param feedback_prompt: (可选) 如果提供了反馈提示词，则进入修复模式
    """
    if feedback_prompt:
        # === 修复模式 ===
        # 使用 Module 4 生成的特定 Prompt 初始化 Agent
        agent = ReActAgent(behavior_text, prompt_override=feedback_prompt)
    else:
        # === 初始模式 ===
        print("=== [Module 2] Starting Modeling Agent (Initial) ===")
        agent = ReActAgent(behavior_text)

    return agent.run()


# ==========================================
# 命令行入口
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Module 2: ReAct Agent")
    parser.add_argument("input_file", default="output_1s.txt")
    parser.add_argument("output_file", nargs='?', default=None)
    args = parser.parse_args()

    input_path = args.input_file

    # 简单的文件名推导
    if args.output_file:
        output_path = args.output_file
    else:
        base = os.path.splitext(os.path.basename(input_path))[0]
        identifier = re.sub(r'^(input|output)_?', '', base, flags=re.IGNORECASE)
        output_path = f"draft_model_{identifier}.json"

    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    status, res = generate_draft_model(text)

    if status == "SUCCESS":
        try:
            # 再次确保 JSON 格式化
            data = json.loads(res)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Saved to {output_path}")
        except:
            print("Invalid JSON result.")
            print(res)
    else:
        print("Modeling Failed.")