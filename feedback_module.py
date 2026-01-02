# feedback_module.py
import prompts


def construct_feedback_prompt(model_draft_json: str, failure_reason: str) -> str:
    """
    当质量检查失败时，构建增强的中文反馈提示词。
    适配论文定义的 Determinism 和 Clarity 检查。
    """
    print("[Module 4] 正在构建增强反馈提示词 (Constructing Feedback)...")

    prompt_template = prompts.GET_FEEDBACK_PROMPT_TEMPLATE()

    violated_property = "未知错误 (Unknown Error)"
    counterexample = "请参考下方的详细错误日志。"
    enhanced_instructions = "请分析错误日志并修正模型逻辑。"

    # === 场景 A: NuSMV 验证失败 (CTL 属性违规) ===
    if "违反属性" in failure_reason or "Violated Property" in failure_reason:
        try:
            lines = failure_reason.split('\n')
            violated_property = lines[0].replace("违反属性 (Violated Property):", "").strip()
            # 提取 Trace
            for line in lines:
                if "反例路径" in line or "Trace" in line:
                    counterexample = line.replace("反例路径 (Trace):", "").replace("Trace:", "").strip()

            if "Resettability" in violated_property:
                enhanced_instructions = (
                    "【修复‘可重置性’ (Resettability)】\n"
                    "反例显示了一条无法回到初始状态的路径。\n"
                    "**修复方案**：请检查路径末端的状态，确保存在一条能（直接或间接）跳转回初始状态的转换规则。"
                )
            elif "Valid_Transition" in violated_property:
                enhanced_instructions = (
                    "【修复‘幻觉跳转’ (Invalid Transition)】\n"
                    "NuSMV 发现模型生成了 JSON 中未定义的非法跳转（通常是隐式自环导致的）。\n"
                    "**修复方案**：请显式定义该状态在特定输入下的行为。如果不应发生任何动作，请显式添加自环（to: 自身）。"
                )
            elif "Reachability" in violated_property:
                enhanced_instructions = (
                    "【修复‘连通性’ (Connectivity)】\n"
                    "检测到不可达状态。\n"
                    "**修复方案**：请检查该状态的前置条件，确保从初始状态有路可走。"
                )
        except Exception as e:
            print(f"[Feedback] 解析 NuSMV 错误异常: {e}")

    # === 场景 B: 清晰性错误 (Clarity / Input Completeness) [新增] ===
    elif "清晰性错误" in failure_reason or "Clarity" in failure_reason:
        violated_property = "输入不完备 (Incomplete Input Handling)"
        counterexample = failure_reason
        enhanced_instructions = (
            "【修复‘清晰性’ (Clarity)】\n"
            "根据 Mealy 机定义，每个状态必须对**所有**可能的输入信号都有定义。\n"
            "错误日志指出了哪些状态漏掉了哪些输入。\n"
            "**修复方案 (强烈建议)**：\n"
            "1. 不要为每个状态单独补写逻辑，这会很繁琐。\n"
            "2. **使用通配符 `*`**：如果某个输入（如 `reset` 或 `timeout`）在大多数状态下行为一致，请添加一条全局规则。\n"
            "   例如: `{\"from\": \"*\", \"to\": \"off\", \"input\": \"reset\"}`\n"
            "3. 如果某个输入在该状态下应该被忽略，请添加**自环**：\n"
            "   例如: `{\"from\": \"state_A\", \"to\": \"state_A\", \"input\": \"irrelevant_input\", \"output\": \"none\"}`"
        )

    # === 场景 C: 确定性错误 (Determinism) ===
    elif "确定性错误" in failure_reason or "Determinism" in failure_reason:
        violated_property = "非确定性冲突 (Non-Determinism)"
        counterexample = failure_reason
        enhanced_instructions = (
            "【修复冲突 (Ambiguity)】\n"
            "同一个状态在同一个输入下，定义了多条不同的跳转路径。\n"
            "**修复方案**：删除冲突的条目，只保留一条正确的逻辑。"
        )

    # === 场景 D: 结构错误 (死锁/孤立) ===
    elif "结构错误" in failure_reason:
        violated_property = "图结构缺陷 (Structural Defect)"
        counterexample = failure_reason
        if "没有入边" in failure_reason:
            enhanced_instructions = "【修复孤立状态】：该状态无法到达。请添加指向它的转换。"
        else:
            enhanced_instructions = "【修复死锁】：该状态没有出边。请添加跳转规则或自环。"

    # === 场景 E: 语法错误 ===
    elif "JSON" in failure_reason or "Syntax" in failure_reason or "语法错误" in failure_reason:
        violated_property = "语法/格式错误 (Syntax Error)"
        counterexample = failure_reason
        enhanced_instructions = (
            "【修复格式】\n"
            "生成的模型无法被解析。请检查 JSON 闭合性，并确保变量名不含空字符串或特殊字符。"
        )

    # 替换模板变量
    feedback_prompt = prompt_template.replace(
        "{last_model_draft}", model_draft_json
    ).replace(
        "{violated_property}", violated_property
    ).replace(
        "{counterexample}", counterexample
    ).replace(
        "{enhanced_instructions}", enhanced_instructions
    )

    return feedback_prompt