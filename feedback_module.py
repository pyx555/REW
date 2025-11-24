# feedback_module.py
import prompts


def construct_feedback_prompt(model_draft_json: str, failure_reason: str) -> str:
    """
    当质量检查失败时，构建*增强的*反馈提示词。
    (基于论文 IV.D 节 和 表IV )
    """
    print("[Module 4] Constructing enhanced feedback prompt...")

    # 从 prompts.py 加载表IV的提示词模板
    prompt_template = prompts.GET_FEEDBACK_PROMPT_TEMPLATE()

    # --- [新逻辑：根据失败类型生成详细指令] ---

    violated_property = "Unknown"
    counterexample = "No counterexample generated."
    # 这是新增的指导性文本
    enhanced_instructions = "No specific instructions for this error. Please re-analyze the problem and the model structure."

    if "Clarity check failed" in failure_reason:
        # 这是您当前遇到的错误 。
        violated_property = failure_reason.strip()
        counterexample = "N/A (This is a structural property, not a path-based one)."

        # 为 LLM 提供如何修复“清晰性”错误的明确指令
        enhanced_instructions = (
            "To fix 'Clarity': The error message shows a state is 'incomplete'.\n"
            "You MUST add new transitions for *every single missing input* listed in the error.\n"
            "If an input should not change the state (e.g., pressing 'home' while 'off'), "
            "create a *self-loop transition* (e.g., \"from\": \"off\", \"to\": \"off\", \"input\": \"short_press_home\", \"output\": \"none\").\n"
            "The final model *must* be complete for all states and all inputs."
        )

    elif "Determinism check failed" in failure_reason:
        # 这是另一种可能的结构错误
        violated_property = failure_reason.strip()
        counterexample = "N/A (This is a structural property)."
        enhanced_instructions = (
            "To fix 'Determinism': The error message indicates a state has *conflicting* transitions.\n"
            "You have defined two or more different transitions for the *exact same (from, input) pair*.\n"
            "You MUST remove the duplicates or merge them into one single, deterministic transition."
        )

    elif "Counterexample:" in failure_reason:
        # 这是 nuXmv/NuSMV 返回的属性错误 (Connectivity, Resettable)
        parts = failure_reason.split("Counterexample:", 1)
        violated_property = parts[0].strip()
        counterexample = parts[1].strip()
        enhanced_instructions = (
            "To fix this property violation:\n"
            "You MUST analyze the 'Counterexample' trace. This trace shows an illegal path (e.g., an unreachable state or a state that cannot return to the initial state).\n"
            "You MUST *add new transitions* (e.g., add a path to the unreachable state) "
            "or *delete the problematic states/transitions* to ensure the logic is correct."
        )

    else:
        # 其他未知错误
        violated_property = failure_reason.strip()

    # --- [逻辑结束] ---

    # === [已修改] ===
    # 使用.replace() 来安全地注入所有内容，包括新的“增强指令”
    feedback_prompt = prompt_template.replace(
        "{last_model_draft}", model_draft_json
    ).replace(
        "{violated_property}", violated_property
    ).replace(
        "{counterexample}", counterexample
    ).replace(
        "{enhanced_instructions}", enhanced_instructions  # <-- 注入新指令
    )

    return feedback_prompt


