# quality_checker.py
import json
import os
import subprocess
from typing import Tuple, Dict, Any

# 导入 pynusmv 库
# 确保 NuSMV 已安装并在系统 PATH 中
try:
    import pynusmv
    import pynusmv.glob
    import pynusmv.init
    import pynusmv.mc
    import pynusmv.prop
except ImportError:
    print("FATAL ERROR: pynusmv library not found.")
    print("Please install NuSMV and the pynusmv library.")
    print("See README.md for installation instructions.")
    exit(1)

Model = Dict[str, Any]


class QualityChecker:
    """
    实现论文 IV.C 节  的质量检查。
    """

    def __init__(self):
        self.output_map = {}
        pass

    def check(self, model_json: str) -> Tuple[bool, str]:
        """
        运行完整的两阶段质量检查。
        """
        print("[Module 3] Starting quality check...")
        try:
            model = json.loads(model_json)
        except json.JSONDecodeError as e:
            return (False, f"Model is not valid JSON: {e}")

        # === 阶段 1: 有效性检查 (IV.C.1)  ===

        (clarity_passed, clarity_reason) = self._check_clarity(model)
        if not clarity_passed:
            print("[Module 3] Check FAILED: Clarity")
            return (False, clarity_reason)

        (determinism_passed, det_reason) = self._check_determinism(model)
        if not determinism_passed:
            print("[Module 3] Check FAILED: Determinism")
            return (False, det_reason)

        print("[Module 3] Validity checks (Clarity, Determinism) PASSED.")

        # === 阶段 2: 设备特定检查 (IV.C.2)  ===
        (device_check_passed, device_reason) = self._check_device_properties(model)
        if not device_check_passed:
            print("[Module 3] Check FAILED: Device Properties (NuSMV)")
            return (False, device_reason)

        print("[Module 3] Device property checks (NuSMV) PASSED.")
        return (True, "Passed all quality checks.")

    ### 子模块 A: 有效性检查 (IV.C.1) - 纯 Python ###

    def _check_clarity(self, model: Model) -> Tuple[bool, str]:
        """
        检查“清晰性”(Clarity):
        确保每个状态都为所有可能的输入信号定义了转换。

        """
        try:
            all_inputs = set(t['input'] for t in model['transitions'])
            if not all_inputs:
                return (False, "Clarity check failed: No inputs found in transitions.")

            for state in model['states']:
                inputs_from_state = set(
                    t['input'] for t in model['transitions'] if t['from'] == state
                )

                if inputs_from_state != all_inputs:
                    missing_inputs = all_inputs - inputs_from_state
                    return (False, f"Clarity check failed for state '{state}'. "
                                   f"Missing transitions for inputs: {missing_inputs}")
            return (True, "Clarity check passed.")
        except KeyError as e:
            return (False, f"Model structure error (KeyError) during clarity check: {e}")

    def _check_determinism(self, model: Model) -> Tuple[bool, str]:
        """
        检查“确定性”(Determinism):
        确保没有非确定性转换 (即, (state, input) 对是唯一的)。

        """
        try:
            seen_transitions = set()
            for t in model['transitions']:
                transition_key = (t['from'], t['input'])
                if transition_key in seen_transitions:
                    return (False, f"Determinism check failed. "
                                   f"State '{t['from']}' has multiple transitions "
                                   f"for input '{t['input']}'.")
                seen_transitions.add(transition_key)
            return (True, "Determinism check passed.")
        except KeyError as e:
            return (False, f"Model structure error (KeyError) during determinism check: {e}")

    ### 子模块 B: 设备特定检查 (IV.C.2) - NuSMV 集成 ###

    def _convert_json_to_smv(self, model: Model) -> str:
        """
        将模块2的 JSON 转换为 NuSMV (.smv) 文件格式。
        (基于论文图2  的模板)
        """
        # 1. VAR state (状态变量)
        states_enum = "{" + ", ".join(model['states']) + "}"
        smv_vars = [f"    state: {states_enum};"]

        # 2. VAR (输入变量) - 论文  提到这是布尔值
        all_inputs = sorted(list(set(t['input'] for t in model['transitions'])))
        for inp in all_inputs:
            smv_vars.append(f"    {inp}: boolean;")

        # 3. VAR (输出变量) - 论文  提到编码为整数
        all_outputs = sorted(list(set(t['output'] for t in model['transitions'])))
        self.output_map = {out: i for i, out in enumerate(all_outputs)}
        output_range = f"0..{len(self.output_map) - 1}" if self.output_map else "0..0"
        smv_vars.append(f"    output: {output_range};")

        # 4. ASSIGN init(state) (初始状态)
        init_state = model.get('init_state', model['states'])
        smv_assign = [f"init(state) := {init_state};"]

        # 5. ASSIGN next(state) (状态转移逻辑)
        smv_assign.append("next(state) :=")
        smv_assign.append("    case")

        # 6. ASSIGN output (输出逻辑)
        smv_assign_output = ["output :=", "    case"]

        # 构建 case 语句
        for t in model['transitions']:
            # 关键步骤: 将 'input' 转换为布尔表达式
            bool_conditions = []
            for inp in all_inputs:
                if inp == t['input']:
                    bool_conditions.append(f"{inp}")  # NuSMV 中布尔变量为TRUE
                else:
                    bool_conditions.append(f"!{inp}")  # 其他所有为FALSE

            case_condition = f"state = {t['from']} & {' & '.join(bool_conditions)}"

            smv_assign.append(f"        {case_condition}: {t['to']};")
            output_int = self.output_map.get(t['output'], 0)
            smv_assign_output.append(f"        {case_condition}: {output_int};")

        # 添加默认 case (保持不变)
        smv_assign.append("        TRUE: state;")
        smv_assign.append("    esac;")

        smv_assign_output.append("        TRUE: output;")  # 默认输出
        smv_assign_output.append("    esac;")

        smv_model_str = (
                "MODULE main\n"
                "VAR\n" + "\n".join(smv_vars) + "\n"
                                                "ASSIGN\n" + "\n".join(smv_assign) + "\n" + "\n".join(
            smv_assign_output) + "\n"
        )
        print(f"\n--- Generated SMV Model ---\n{smv_model_str}\n---------------------------")
        return smv_model_str

    def _check_device_properties(self, model: Model) -> Tuple[bool, str]:
        """
        使用 pynusmv 检查设备特定属性 (Connectivity, Resettable)。
        (基于论文表III )
        """
        smv_model_str = self._convert_json_to_smv(model)

        try:
            pynusmv.init.init_nusmv()
            pynusmv.glob.load_from_string(smv_model_str)
            pynusmv.glob.compute_model()
            fsm = pynusmv.glob.prop_database().master.bddFsm

            # 属性 1: Resettable (可重置性)
            # "For every state, there is a path to the initial state."
            # CTL: AG (AF state = init_state)
            init_state = model.get('init_state', model['states'])
            resettable_ctl = f"AG (AF state = {init_state})"

            print(f"  Checking Resettable: {resettable_ctl}")
            spec = pynusmv.prop.parse_ctl_spec(resettable_ctl)

            if not pynusmv.mc.check_ctl_spec(fsm, spec):
                counterexample = self._get_counterexample_trace(fsm, spec)
                pynusmv.init.deinit_nusmv()
                return (False, f"Resettable check failed (CTL: {resettable_ctl}). "
                               f"Counterexample: {counterexample}")

            # 属性 2: Connectivity (连通性)
            # "There is no state that cannot be reached from the initial state."
            # CTL: AF (state = <state_name>) (从初始状态必须能达到所有状态)
            print("  Checking Connectivity for all states...")
            for state_name in model['states']:
                conn_ctl = f"AF (state = {state_name})"
                spec = pynusmv.prop.parse_ctl_spec(conn_ctl)

                if not pynusmv.mc.check_ctl_spec(fsm, spec):
                    counterexample = self._get_counterexample_trace(fsm, spec)
                    pynusmv.init.deinit_nusmv()
                    return (False, f"Connectivity check failed for state '{state_name}' "
                                   f"(CTL: {conn_ctl}). State is unreachable. "
                                   f"Counterexample: {counterexample}")

            pynusmv.init.deinit_nusmv()
            return (True, "Device properties passed.")

        except Exception as e:
            pynusmv.init.deinit_nusmv()
            return (False, f"Error during NuSMV check: {e}\nGenerated SMV Model:\n{smv_model_str}")

    def _get_counterexample_trace(self, fsm, spec) -> str:
        """
        使用 pynusmv.mc.explain 获取反例的字符串表示。
        [2]
        """
        try:
            violating_states = fsm.init & ~pynusmv.mc.eval_ctl_spec(fsm, spec)
            explanation = pynusmv.mc.explain(fsm, violating_states, spec)

            trace_parts = []
            # [2] 展示了解释的格式
            for state, inputs in zip(explanation[::2], explanation[1::2]):
                trace_parts.append(f"State: {state.get_str_values()}, "
                                   f"Input: {inputs.get_str_values()}")
            # 添加最后一个状态
            if explanation and len(explanation) % 2 == 1:
                trace_parts.append(f"State: {explanation[-1].get_str_values()}")

            return " -> ".join(trace_parts)
        except Exception as e:
            return f"Could not generate counterexample: {e}"


if __name__ == "__main__":

    input_draft_model = 'draft_model_1s.json'  # 上一步的输出

    print(f"=== 正在运行质量检查 (Module 3) ===")
    print(f"输入文件: {input_draft_model}")
    print("========================================")

    # 1. 检查文件是否存在
    if not os.path.exists(input_draft_model):
        print(f"FATAL ERROR: 找不到输入文件 '{input_draft_model}'。")
        print("请先运行 'python modeling_agent.py' 来生成此文件。")
        exit(1)

    # 2. 读取模型 JSON 字符串
    try:
        with open(input_draft_model, 'r', encoding='utf-8') as f:
            model_json_string = f.read()
    except Exception as e:
        print(f"FATAL ERROR: 读取文件 '{input_draft_model}' 时出错: {e}")
        exit(1)

    # 3. 初始化并运行检查器
    checker = QualityChecker()
    (passed, reason) = checker.check(model_json_string)

    # 4. 打印最终结果
    if passed:
        print("\n=== [Module 3] 最终结果: PASSED ===")
        print("模型草稿通过了所有质量检查。")
    else:
        print("\n=== [Module 3] 最终结果: FAILED ===")
        print("模型草稿未通过质量检查:")
        print(f"失败原因: {reason}")

    print("========================================")

