import json
from modeling_agent import ReActAgent

# 1. 模拟一段设备行为描述 (通常来自 extraction_agent 的输出)
# 这里我们用一个简单的例子：米家扫地机器人的部分行为
MOCK_BEHAVIOR_DESCRIPTION = """
设备名称：米家扫地机器人。
主要功能：
1. 开机/关机：长按电源键3秒可以开机或关机。
2. 清扫：短按电源键开始全屋清扫。
3. 回充：短按回充键，机器人返回充电座。如果在清扫过程中电量低于20%，机器人会自动返回充电。
4. 暂停：在清扫或回充过程中，按任意键暂停。
状态指示灯：
- 白色常亮：工作正常或充电完成。
- 黄色呼吸：正在充电。
- 红色闪烁：故障状态。
"""

def print_separator(title=""):
    print(f"\n{'='*20} {title} {'='*20}")

def test_react_agent():
    print_separator("开始 ReAct Agent 测试")
    print("输入行为描述:")
    print(MOCK_BEHAVIOR_DESCRIPTION.strip())
    print_separator()

    # 2. 实例化 Agent
    agent = ReActAgent(MOCK_BEHAVIOR_DESCRIPTION)

    # 为了能在控制台看到实时的交互过程，我们需要稍微 "魔改" 一下 agent 的 _call_llm 方法，
    # 或者更简单地，我们信任 llm_api_client.py 里的 print 语句能让我们看到进度。
    # 更好的可视化是打印出 agent 的历史记录。

    print("正在启动 ReAct 循环，请耐心等待 LLM 思考和行动...\n")

    # 3. 运行 Agent
    status, result = agent.run()

    # 4. 可视化输出交互历史 (ReAct 的思考过程)
    print_separator("ReAct 交互历史 (Trace)")
    for i, turn in enumerate(agent.history):
        # 给不同类型的消息加一点简单的格式区分
        if turn.startswith("Observation:"):
             print(f"[Step {i+1}] 🔍 {turn}")
        elif "Thought:" in turn or "Action:" in turn:
             print(f"[Step {i+1}] 🤖 LLM:\n{turn}")
        else:
             print(f"[Step {i+1}] {turn}")
        print("-" * 40)

    # 5. 输出最终结果
    print_separator("最终运行结果")
    if status == "SUCCESS":
        print("✅ 建模成功！生成的 JSON 如下：\n")
        try:
            # 尝试格式化打印 JSON
            parsed_json = json.loads(result)
            print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
        except:
            print(result) # 如果解析失败直接打印原始字符串
    else:
        print(f"❌ 建模失败: {result}")

if __name__ == "__main__":
    # 确保依赖文件存在
    try:
        import prompts
        import llm_api_client
        import config
    except ImportError as e:
        print(f"❌ 环境检查失败: 缺少必要的文件。错误: {e}")
        print("请确保 prompts.py, llm_api_client.py, config.py 都在当前目录下。")
        exit(1)

    test_react_agent()