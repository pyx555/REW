# visualize_model.py
import json
import os
import subprocess
import shutil


def generate_visualization(json_path: str, output_base_name: str):
    """
    读取 JSON 模型，生成 DOT 文件并渲染为 PNG。
    参考: EnviRE2024/transfer.py
    """
    if not os.path.exists(json_path):
        print(f"Error: Model file '{json_path}' not found.")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_fsm = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return

    # 1. 获取所有状态
    # 优先使用 metadata 中的 'states'，如果没有则从 transitions 提取
    if "states" in json_fsm:
        all_states = set(json_fsm["states"])
    else:
        all_states = set([t['from'] for t in json_fsm.get("transitions", []) if t['from'] != '*'] +
                         [t['to'] for t in json_fsm.get("transitions", []) if t['to'] != '*'])

    # 2. 生成 DOT 内容 (基于 transfer.py 逻辑)
    header = """digraph finite_state_machine {
    rankdir = LR;
    node [shape = circle];
    """

    trans_lines = []

    # 标记初始状态
    init_state = json_fsm.get("init_state")
    if init_state:
        # 添加一个隐形的起始点指向初始状态
        trans_lines.append(f'    "" [shape=none, width=0];')
        trans_lines.append(f'    "" -> "{init_state}";')

    transitions = json_fsm.get("transitions", [])

    for t in transitions:
        src = t.get('from')
        dst = t.get('to')
        # 清理标签中的特殊字符
        inp = t.get('input', '').replace('"', "'")
        out = t.get('output', '').replace('"', "'")
        label = f'{inp} / {out}'

        if src != '*' and dst != '*':
            trans_lines.append(f'    "{src}" -> "{dst}" [ label = "{label}" ];')

        elif src != '*' and dst == '*':
            # from specific to ALL
            for state in all_states:
                trans_lines.append(f'    "{src}" -> "{state}" [ label = "{label}" ];')

        elif dst != '*' and src == '*':
            # from ALL to specific
            for state in all_states:
                trans_lines.append(f'    "{state}" -> "{dst}" [ label = "{label}" ];')

    body = "\n".join(trans_lines)
    footer = "\n}"

    dot_content = header + body + footer

    # 3. 写入 .dot 文件
    dot_filename = f"{output_base_name}.dot"
    with open(dot_filename, 'w', encoding='utf-8') as f:
        f.write(dot_content)
    print(f"DOT file generated: {dot_filename}")

    # 4. 调用 Graphviz 转换为 PNG
    png_filename = f"{output_base_name}.png"

    # 检查是否安装了 graphviz (dot 命令)
    if not shutil.which("dot"):
        print("WARNING: 'dot' command not found. Cannot convert to PNG.")
        print("Please install Graphviz: sudo apt-get install graphviz")
        return

    try:
        subprocess.run(["dot", "-Tpng", dot_filename, "-o", png_filename], check=True)
        print(f"Successfully generated image: {png_filename}")
    except subprocess.CalledProcessError as e:
        print(f"Error running Graphviz: {e}")


if __name__ == "__main__":
    # 默认转换当前目录下的 verified_model_from_draft.json
    model_file = "verified_model_from_draft.json"
    generate_visualization(model_file, "final_model_graph")