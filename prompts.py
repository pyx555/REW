# prompts.py

def GET_BEHAVIOR_EXTRACTION_PROMPT() -> str:
    """
    返回论文表I  中的提示词：设备行为提取。
    """
    return """
Task Description(OCR Error Correction):
Solve the given task. The following is the OCR recognition result of a smart home device, which may have typos, missing words, extra words or symbols, etc. You need to correct the key information of this device based on it.

Task Description(Device Behavior Extraction):
After correction, you need to further summarize the key information of this device based on it, specifically all states, operations, and behaviors of this device, based on it and common sense, for end users to further understand its behavior.

Input(User manual of the device):
The OCR recognition result of the manual is as follows:
{ocr_input}

Output Form Description:
You should answer the result directly.
"""
# prompts.py

def GET_REACT_MODELING_PROMPT():
    return """You are a formal verification expert. Your job is to extract a Mealy machine model from the device description.

Use the following ReAct format strictly:

Thought: <your reasoning about what to do next>
Action: <one of the available actions>
[STOP HERE and wait for Observation]
Observation: <the result of your action will be pasted here by the system>

Available Actions:
- search[keyword]: Searches specifically for 'keyword' in the text.
- lookup[keyword]: Finds the exact sentence containing 'keyword'.
- finish[json_model]: Returns the final JSON model when you are confident.

Examples:
Thought: I need [Module 3] Starting quality check...
[Module 3] Check FAILED: Clarity
[Module 3] Starting quality check...
[Module 3] Check FAILED: Clarity
--- Quality Check FAILED ---
Reason: Clarity check failed for state 'cleaning'. Missing transitions for inputs: {'long_press_power', 'short_press_home', 'long_press_home', 'short_press_power', 'error_resolved', 'battery_charged', 'error_occurred', 'resume'}
[Module 4] Constructing feedback prompt...

--- Modeling FAILED after 5 attempts ---

=== MODELING FAILED ===
Max attempts reached. Model could not be verified.to find how to turn it on.
Action: search[电源]
Observation: Found: "长按电源键3秒可以开机..."

Thought: I have all info.
Action: finish[{"states": ["off", "on"], ...}]

IMPORTANT RULES:
1. ONLY generate ONE Thought and ONE Action per turn.
2. DO NOT generate "Observation:" yourself. The system will provide it.
3. If you already have enough information from the initial description, you can directly use the 'finish' action.
4. The model MUST be COMPLETELY SPECIFIED. For EVERY state, you MUST define a transition for EVERY possible input.
   - If an input is ignored, you MUST add a "self-loop" transition: {"from": "state_A", "to": "state_A", "input": "ignored_input", "output": "none"}

Device Description to Model:
{behavior_input}
"""



'''
def GET_REACT_MODELING_PROMPT() -> str:
    """
    返回论文表II  中的提示词：基于ReAct的自动建模。
    """
    return """
ReAct Prompting:
Solve the given task by following Thought, Action, and Observation for every step.
Thought: Reason about the current situation and the next steps to follow.
Action: Choose one of the available actions:
1.  `search[query]`: Search the device behavior description for information about a state, transition, or keyword.
2.  `lookup[keyword]`: Look up a specific keyword in the provided text to find related sentences.
3.  `finish[json_model]`: Finish the task and return the complete Mealy machine model in the specified JSON format.
Observation: Observe the result of the action.

Task Description:
Your task is to create a formal Mealy machine model based on the provided device behavior description.

Input(Device Behavior Description):
{behavior_input}

Output Form Description:
The final result must be returned using the `finish` action.
The argument for `finish` MUST be a valid JSON format.
The JSON must contain:
1.  `states`: A list of all state names (strings).
2.  `init_state`: The name of the initial state (e.g., "power_off").
3.  `transitions`: A list of transition objects.

Each transition object MUST include four keys:
1.  `"from"`: The source state name.
2.  `"to"`: The target state name.
3.  `"input"`: The input signal that triggers the transition.
4.  `"output"`: The output signal generated during the transition.

In the names of the states, inputs, and outputs you generate, only lowercase letters and underscores are allowed (e.g., "power_off", "long_press_power", "charging_started").

Begin your reasoning.
"""
'''

'''
def GET_FEEDBACK_PROMPT_TEMPLATE() -> str:
    """
    返回论文表IV  中的提示词：质量检查失败的反馈。
    """
    return """
Device Model (In last output):
The model you generated in the last turn was:
{last_model_draft}

Violated property:
This model failed the quality check. It violated the following property:
{violated_property}

Counterexample:
Here is the counterexample trace demonstrating the violation:
{counterexample}

Please analyze this error, generate a new 'Thought', and provide a corrected JSON model using the 'finish' action.
"""
'''

def GET_FEEDBACK_PROMPT_TEMPLATE() -> str:
    """
    返回论文表IV  中的提示词：质量检查失败的反馈。
    (已修改：添加了 {enhanced_instructions} 占位符以提供修复指南)
    """
    return """
Device Model (In last output):
The model you generated in the last turn was:
{last_model_draft}

Violated property:
This model failed the quality check. It violated the following property:
{violated_property}

Counterexample:
Here is the counterexample trace demonstrating the violation:
{counterexample}

---
**Actionable Instructions (How to fix this specific error):**
{enhanced_instructions}
---

Please analyze this error AND the instructions above, generate a new 'Thought', and provide a corrected JSON model using the 'finish' action.
"""