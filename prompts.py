# prompts.py

def GET_BEHAVIOR_EXTRACTION_PROMPT() -> str:
    """
    [模块 1] 行为提取提示词 (深度优化版)
    目标：清洗 OCR 文本，并建立严格的‘状态字典’和‘状态转换表’，
    为后续的形式化建模扫清障碍。
    """
    return """
**角色定义**：
你是一位资深的嵌入式系统需求分析师。你的任务是读取一份智能家居设备的中文说明书（OCR 识别文本），将其转化为一份用于形式化验证（Model Checking）的**系统行为规范**。

**输入 (OCR 原始文本)**:
{ocr_input}

**核心指令**：

1.  **文本清洗**：
    * 修复 打字错误、遗漏单词、多余的单词或符号等（如把 '0' 修复为 'O'，'坐盒' 修复为 '尘盒'）。
    * 忽略无用的营销话术（如“科技改变生活”），只保留功能逻辑。

2.  **建立状态字典 (State Dictionary) 【至关重要】**：
    * 根据常识并且通读全文，提取设备所有可能的**可感知状态**。
    * 为每个状态指定一个**唯一的、全小写、下划线连接的英文 ID (snake_case)**。


3.  **提取转换逻辑 (Transition Logic)**：
    * 识别所有的 `[当前状态] + [触发条件/输入信号] -> [目标状态]` 逻辑。
    * **特别关注自动行为**：如“10分钟无操作 -> 休眠”、“电量低 -> 回充”。这些是验证死锁的关键。

---

**输出格式要求 (请严格按照以下 Markdown 格式输出)**：

### 1. 设备基本信息
* **设备名称**: [名称]
* **核心功能**: [简短列表]

### 2. 状态定义表 (State Dictionary)
| 中文状态名 | 英文 ID (用于代码) | 状态描述 | 是否初始状态 |
| :--- | :--- | :--- | :--- |
| 关机 | off | 电源完全切断 | 是 |
| 待命 | standby | 开机静止，等待指令 | 否 |
| ... | ... | ... | ... |
*(请确保列出所有状态)*

### 3. 详细行为逻辑 (Transitions)

#### A. 用户按键操作 (User Actions)
* **[off]** + 长按电源键 -> **[standby]**
* **[standby]** + 短按清扫键 -> **[cleaning]**
* ...

#### B. 系统自动事件 (System Events & Timeouts)
* **[standby]** + 无操作10分钟 (timeout_10min) -> **[sleep]**
* **[cleaning]** + 电量低 (low_battery) -> **[returning]**
* **[charging]** + 充满电 (battery_full) -> **[standby]**
* ...

#### C. 故障与异常 (Errors)
* **[any_state]** + 轮子悬空/传感器异常 -> **[error]**
* ...

### 4. 补充说明 (Notes)
* [列出任何特殊的逻辑约束，例如：充电座上无法关机、故障排除后需重置等]
"""



def GET_REACT_MODELING_PROMPT() -> str:
    """
    [模块 2] ReAct 建模提示词 (动作定义增强版)
    优化点：
    1. 明确定义 search/lookup/finish 三个动作。
    2. 在 'finish' 动作中强行植入 JSON 格式约束。
    3. 结合 ReAct 思维链，确保先思考后行动。
    """
    return """
**角色定义**：
你是一个精通 NuSMV 的形式化验证专家 Agent。你的任务是利用 ReAct (思考-行动) 范式，将结构化的设备描述转换为可执行的 Mealy 状态机 JSON。

**输入数据**：
{behavior_input}

---

** ReAct 核心协议 (Core Protocol)**：
你必须严格遵循 **Thought (思考)** -> **Action (行动)** -> **Observation (观察)** 的循环。

1. **Thought**：
   * 在执行任何动作前，必须先用中文进行逻辑推演。
   * **状态审计**：列出【状态定义表】中所有的 `英文 ID`，并告诉自己：“只允许使用这些状态名”。
   * **逻辑解析**：分析【详细行为逻辑】中的每一条转换。

2. **Action**：
   * 输出且仅输出一个指令。指令必须属于下方的【可用动作列表】。

3. **Observation**：
   * 等待系统反馈（通常情况下，如果是 finish 动作，任务即结束）。

---

** 可用动作 (Available Actions)**：

1. **`search[keyword]`**
   * **描述**：在输入文档中搜索关键词。
   * **适用场景**：当你觉得某个状态的定义模糊，或者转换条件不清楚时使用。

2. **`lookup[keyword]`**
   * **描述**：查找包含关键词的具体句子或段落上下文。
   * **适用场景**：当你需要确认某个逻辑的原文描述时使用。

3. **`finish[json_model]`**
   * **描述**：提交最终的 JSON 模型并结束任务。
   * **参数要求 (CRITICAL)**：参数 `json_model` 必须是一个合法的 JSON 对象，且满足以下格式：
     * `states`: [字符串列表] (必须与表格中的英文 ID 完全一致，严禁创造新词)。
     * `init_state`: "状态名" (必须在 states 列表中)。
     * `transitions`: [
         {{"from": "状态A", "to": "状态B", "input": "事件名", "output": "响应动作"}}
       ]
     * **变量规范**：`input` 和 `output` 必须是 **snake_case** (如 `press_power`, `wifi_connected`)，严禁中文。
     * **通配符**：如果原文写 `[any_state]`，JSON 中 `from` 写 `"*"`。

---

**交互示例 (Example Interaction)**：

<USER>:
输入文档：
### 状态表
| 中文 | 英文 ID |
| :--- | :--- |
| 关机 | off |
| 运行 | run |

### 逻辑
* [off] + 按键 -> [run]

<YOU>:
Thought:
1. **状态审计**：表格里只有 `off` 和 `run`。所以我绝对不能用 `running` 或 `closed`。
2. **逻辑分析**：
   - 转换 1: off -> run (input: press_button)。
3. **决策**：信息完整，不需要 search，直接生成模型。

Action: finish[{
    "states": ["off", "run"],
    "init_state": "off",
    "transitions": [
        {"from": "off", "to": "run", "input": "press_button", "output": "start"}
    ]
}]

---

**当前任务**：
请利用 ReAct 范式，对上面的 {behavior_input} 进行建模。
**请开始你的推理 (Thought)...**
"""


def GET_FEEDBACK_PROMPT_TEMPLATE() -> str:
    """
    [模块 4] 反馈提示词 (中文版)
    将 NuSMV 的数学反例翻译成人类可读的修复指令。
    """
    return """
###  质量检查未通过 (Quality Check FAILED)

**你上一次生成的模型**:
{last_model_draft}

**违反的属性 (Violated Property)**:
{violated_property}

**反例路径 (Counterexample Trace)** (这是证明模型出错的证据):
{counterexample}

---
###  专家修复指引
**{enhanced_instructions}**

**要求**:
1. 仔细阅读上面的 `反例路径`。它展示了模型是在哪一步偏离了预期，或者陷入了死锁。
2. 阅读 `专家修复指引`。
3. 思考：“是少了一个转换？还是状态跳转的目标错了？或者是陷入了死循环？”
4. 请输出一个新的 `finish[...]` 动作，包含修复后的 JSON 模型。**记住保持 Key/Value 为全英文。**

开始你的修复逻辑。
"""