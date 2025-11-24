# modeling_agent.py
import os

import prompts
import json
import re
from llm_api_client import call_llm
import config


class ReActAgent:
    """
    实现论文 IV.B 节 [1] 中的 ReAct 代理。
    """
    '''
    def __init__(self, behavior_description: str):
        self.behavior_description = behavior_description

        # === 这是已修正的部分 (Line 17) ===
        self.history = [] # <-- 必须初始化为空列表
        # ================================

        self.initial_prompt = prompts.GET_REACT_MODELING_PROMPT().format(
            behavior_input=self.behavior_description
        )
        self.max_turns = 3  # 防止在ReAct内部无限循环
        '''

    # modeling_agent.py

    def __init__(self, behavior_description: str):
        self.behavior_description = behavior_description
        self.history = []
        self.max_turns = 10

        # === 修改前 (会导致 KeyError) ===
        # self.initial_prompt = prompts.GET_REACT_MODELING_PROMPT().format(
        #     behavior_input=self.behavior_description
        # )

        # === 修改后 (安全可靠) ===
        # 使用 replace 直接替换占位符，不会受到 JSON 大括号的干扰
        self.initial_prompt = prompts.GET_REACT_MODELING_PROMPT().replace(
            "{behavior_input}", self.behavior_description
        )

    def _call_llm(self) -> str:
        """ 构造完整提示词并调用 LLM """
        full_prompt = self.initial_prompt + "\n" + "\n".join(self.history)
        return call_llm(full_prompt, model=config.LLM_MODEL_NAME)

    def _parse_action(self, response: str) -> (str, str):
        """
        强力解析器 V2：
        1. 强制只看第一个 "Action:"，切断 LLM 的抢答。
        2. 兼容各种奇怪的格式噪音（如反引号 `、Markdown 加粗 ** 等）。
        3. 对 finish 动作的 JSON 进行专门提取，防止因嵌套括号导致的正则匹配中断。
        """
        try:
            # --- 步骤 1: 切断抢答 ---
            # 找到第一个 "Action:" 的位置，只保留它及其之后的内容
            # 使用不区分大小写的查找
            match_start = re.search(r"Action:", response, re.IGNORECASE)
            if not match_start:
                return "error", "No 'Action:' keyword found in response."

            # 截取 "Action:" 之后的所有文本作为待分析片段
            content_after_action = response[match_start.end():].strip()

            # --- 步骤 2: 提取动作名 ---
            # 匹配动作名：允许周围有 ` * " ' 等噪音字符
            # 例如能匹配: `search`[...], **lookup**[...], finish[...]
            name_match = re.match(r"[\s`*\"']*(search|lookup|finish)[\s`*\"']*(?=\[)", content_after_action,
                                  re.IGNORECASE)
            if not name_match:
                return "error", "Found 'Action:', but followed by unrecognized command name."

            action_name = name_match.group(1).lower()

            # --- 步骤 3: 提取参数 ---
            # 找到第一个 '[' 的位置
            start_bracket = content_after_action.find('[')
            if start_bracket == -1:
                return "error", "Missing '[' after action name."

            if action_name == "finish":
                # === 特殊处理 finish (因为 JSON 可能包含嵌套的 ']') ===
                # 我们寻找从第一个 '{' 开始，到最后一个 '}' 结束的内容
                json_start = content_after_action.find('{', start_bracket)
                json_end = content_after_action.rfind('}')  # 从后往前找最后一个 '}'

                if json_start != -1 and json_end != -1 and json_end > json_start:
                    json_str = content_after_action[json_start:json_end + 1]
                    try:
                        # 简单的清理，去掉可能包裹 JSON 的 markdown 代码块标记
                        clean_json = json_str.replace("```json", "").replace("```", "").strip()
                        json.loads(clean_json)  # 尝试校验 JSON 合法性
                        return "finish", clean_json
                    except json.JSONDecodeError as e:
                        return "error", f"Found finish action, but JSON is invalid: {e}"
                else:
                    return "error", "Action is 'finish', but could not find valid {...} JSON block."

            else:
                # === 处理普通动作 (search/lookup) ===
                # 只需要匹配到最近的一个 ']' 即可 (非贪婪)
                # 使用正则提取 [ ] 里的内容
                arg_match = re.search(r"\[(.*?)\]", content_after_action, re.DOTALL)
                if arg_match:
                    # .strip() 去掉参数前后可能多余的空格或换行
                    return action_name, arg_match.group(1).strip()
                else:
                    return "error", f"Could not extract argument for action '{action_name}'."

        except Exception as e:
            return "error", f"Unexpected error during action parsing: {e}"

    """
    def _parse_action(self, response: str) -> (str, str):
        
        #从LLM的响应中解析出 Action: [ActionName][Argument]
        #(使用更健壮的正则表达式)
        
        try:
            # 优先寻找 finish，因为它包含复杂的 JSON [1]
            # 格式: Action: finish[{...}] 或 Action: finish [...]
            finish_match = re.search(
                r"Action:\s*finish\s*\[\s*(\{.*?\})\s*\]",
                response,
                re.DOTALL  # re.DOTALL 使 '.' 匹配包括换行符在内的任何字符
            )
            if finish_match:
                json_str = finish_match.group(1)
                try:
                    # 验证它是否是有效的 JSON
                    json.loads(json_str)
                    return "finish", json_str
                except json.JSONDecodeError as e:
                    return "error", f"Found 'finish' action but JSON was invalid: {e}"

            # 寻找 search [1]
            search_match = re.search(r"Action:\s*search\[(.*?)\]", response)
            if search_match:
                return "search", search_match.group(1).strip()

            # 寻找 lookup [1]
            lookup_match = re.search(r"Action:\s*lookup\[(.*?)\]", response)
            if lookup_match:
                return "lookup", lookup_match.group(1).strip()

        except Exception as e:
            return "error", f"Error during action parsing: {e}"

        return "error", "No valid 'Action:' (search, lookup, or finish with JSON) found in response."
    
    """
    def _execute_action(self, action_name: str, argument: str) -> str:
        """
        执行 ReAct 论文 [1] 中定义的动作
        """
        print(f"  Executing Action: {action_name}")
        if action_name == "search":
            # 模拟在行为描述中搜索
            if argument.lower() in self.behavior_description.lower():
                return f"Found text related to '{argument}'."
            else:
                return f"'{argument}' not found in the device description."

        elif action_name == "lookup":
            # 模拟 "Ctrl+F" 功能 [1]
            sentences = self.behavior_description.split('.')
            found_sentence = "No specific sentence found."
            for s in sentences:
                if argument.lower() in s.lower():
                    found_sentence = s.strip()
                    break
            return f"Lookup result for '{argument}': {found_sentence}"

        elif action_name == "finish":
            return argument  # 直接返回 JSON

        else:
            return f"Unknown action: {action_name}"

    def run(self, feedback: str = None) -> (str, str):
        """
        运行 ReAct 循环直到 'finish' 动作被调用。
        """
        if feedback:
            # 如果存在来自质量检查器的反馈 (论文 IV.D 节) [1]
            # 将其作为 "Observation" 添加到历史记录中，以启动新一轮纠错
            self.history.append(f"Observation: {feedback}")

        for _ in range(self.max_turns):
            response = self._call_llm()
            self.history.append(response)  # 添加 LLM 的 Thought 和 Action

            action_name, argument = self._parse_action(response)

            if action_name == "error":
                observation = f"Error: {argument}. Please correct your action format."
                self.history.append(f"Observation: {observation}")
                continue  # 让 LLM 重试

            if action_name == "finish":
                print("  'finish' action called.")
                # JSON 有效性已在 _parse_action 中检查
                return ("SUCCESS", argument)  # 返回模型 JSON

            else:
                # 执行 search 或 lookup
                observation = self._execute_action(action_name, argument)
                self.history.append(f"Observation: {observation}")

        return ("ERROR", "Max turns reached without 'finish' action.")

'''
if __name__ == "__main__":

    # 步骤 1: 定义输入和输出文件
    input_filename = 'output_1s.txt'
    output_filename = 'draft_model_1s.json'  # 这是您想要的“初步模型草稿”

    # --- [已修正] ---
    # 移除了上一版本中的错误 print 语句
    print(f"=== 正在运行建模代理 (Module 2) ===")
    # --- [修正结束] ---

    # 检查输入文件是否存在
    if not os.path.exists(input_filename):
        print(f"Error: 找不到输入文件 '{input_filename}'。")
        print("请先运行 'python extraction_agent.py' 来生成此文件。")
    else:
        try:
            # 步骤 2: 读取上一步的输出 [1]
            print(f"正在读取行为描述: {input_filename}")
            with open(input_filename, 'r', encoding='utf-8') as f:
                behavior_description = f.read()

            if not behavior_description.strip():
                print("Warning: 输入文件为空！")
            else:
                print("=== 开始执行 ReAct 建模 (这可能需要几分钟...) ===")

                # 步骤 3: 初始化并运行代理
                agent = ReActAgent(behavior_description)

                # 运行代理 (不带反馈，这是第一轮)
                (status, model_json_or_error) = agent.run(feedback=None)

                if status == "SUCCESS":
                    print("\n=== 建模成功！(Module 2) ===")
                    print("已生成初步的模型草稿。")

                    # 步骤 4: 保存模型草稿
                    try:
                        print(f"正在保存模型草稿到 {output_filename}")
                        # 解析 JSON 字符串以便格式化 (pretty-print)
                        model_data = json.loads(model_json_or_error)
                        with open(output_filename, 'w', encoding='utf-8') as f_out:
                            # 格式化输出，使其易于阅读
                            json.dump(model_data, f_out, indent=4, ensure_ascii=False)
                        print(f"成功保存到 {output_filename}")
                        print(f"\n下一步: 运行 'controller.py' 来对 '{output_filename}' 执行完整的质量检查和迭代。")

                    except json.JSONDecodeError as e:
                        print(f"Error: LLM 返回了 'SUCCESS'，但其输出不是有效的 JSON: {e}")
                        print(f"Raw output: {model_json_or_error}")

                else:  # status == "ERROR"
                    print(f"\n=== 建模失败 (Module 2) ===")
                    print(f"错误: {model_json_or_error}")

        except Exception as e:
            print(f"\n!!! 运行出错!!!\n{e}")
'''
# ... (ReActAgent 类的所有代码保持不变) ...

if __name__ == "__main__":

    # 步骤 1: 定义输入和输出文件
    input_filename = 'output_1s.txt'
    output_filename = 'draft_model_1s.json' # 这是您想要的“初步模型草稿”

    print(f"=== 正在运行建模代理 (Module 2) ===")

    # 检查输入文件是否存在
    if not os.path.exists(input_filename):
        print(f"Error: 找不到输入文件 '{input_filename}'。")
        print("请先运行 'python extraction_agent.py' 来生成此文件。")
    else:
        try:
            # 步骤 2: 读取上一步的输出 [1]
            print(f"正在读取行为描述: {input_filename}")
            with open(input_filename, 'r', encoding='utf-8') as f:
                behavior_description = f.read()

            if not behavior_description.strip():
                print("Warning: 输入文件为空！")
            else:
                print("=== 开始执行 ReAct 建模 (这可能需要几分钟...) ===")

                # 步骤 3: 初始化并运行代理
                agent = ReActAgent(behavior_description)

                # 运行代理 (不带反馈，这是第一轮)
                (status, model_json_or_error) = agent.run(feedback=None)

                # === [新增功能] 打印 ReAct 交互历史 (可视化思考过程) ===
                print("\n" + "="*20 + " ReAct 交互历史 (Trace) " + "="*20)
                if not agent.history:
                    print("Agent 历史为空 (可能在第一步就出错了).")
                else:
                    for i, turn_content in enumerate(agent.history):
                        print(f"\n[--- Turn {i + 1} ---]")
                        if turn_content.startswith("Observation:"):
                            # 观察 (来自环境/工具)
                            print(f"🔍 {turn_content}")
                        else:
                            # 思考/行动 (来自 LLM)
                            print(f"🤖 {turn_content}")
                print("\n" + "="*60 + "\n")
                # === [功能结束] ===


                if status == "SUCCESS":
                    print("\n=== 建模成功！(Module 2) ===")
                    print("已生成初步的模型草稿。")

                    # 步骤 4: 保存模型草稿
                    try:
                        print(f"正在保存模型草稿到 {output_filename}")
                        # 解析 JSON 字符串以便格式化 (pretty-print)
                        model_data = json.loads(model_json_or_error)
                        with open(output_filename, 'w', encoding='utf-8') as f_out:
                            # 格式化输出，使其易于阅读
                            json.dump(model_data, f_out, indent=4, ensure_ascii=False)
                        print(f"成功保存到 {output_filename}")
                        print(f"\n下一步: 运行 'controller.py' 来对 '{output_filename}' 执行完整的质量检查和迭代。")

                    except json.JSONDecodeError as e:
                        print(f"Error: LLM 返回了 'SUCCESS'，但其输出不是有效的 JSON: {e}")
                        print(f"Raw output: {model_json_or_error}")

                else: # status == "ERROR"
                    print(f"\n=== 建模失败 (Module 2) ===")
                    print(f"错误: {model_json_or_error}")

        except Exception as e:
            print(f"\n!!! 运行出错!!!\n{e}")