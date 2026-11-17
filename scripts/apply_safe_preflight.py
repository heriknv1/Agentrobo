#!/usr/bin/env python3
"""Fail closed, but do not mark trusted computer-use validation errors as uncertain.

Only local pre-dispatch branches of the built-in computer_functions_act handler
may attest no input was sent. The durable journal requires this in-process
attestation, never a tool-output field supplied by the model.
"""
from pathlib import Path
import argparse

EXECUTION_ANCHOR = '''    def settle(self, output: str | None = None, *, cancelled: bool = False) -> None:
        """Close read-only work; preserve uncertainty for unverified effects."""
'''

EXECUTION_INSERT = '''    def confirm_native_preflight_no_effect(self) -> None:
        """Attest a trusted computer action rejected before input or window focusing.

        This is called only from the built-in handler's pre-dispatch path.
        Tool output alone cannot establish no-effect evidence.
        """
        with self._lock:
            if (
                current_operation_execution() is not self
                or not self.trusted_builtin
                or self.tool_name != "computer_functions_act"
                or not self._effect_started
                or self._status != "executing"
                or self.effect_class != "opaque_effect"
            ):
                raise OperationDispatchBlocked(
                    "external_effect_unknown",
                    "Cannot attest no-effect outside trusted pre-dispatch computer use.",
                )
            self._transition(
                "failed",
                reason_code="operation_failed",
                evidence={"verification_result": "unchanged"},
            )

''' + EXECUTION_ANCHOR

HELPER_ANCHOR = '''    if not isinstance(actions, list) or not actions:
        return json.dumps({"status": "error", "error": "actions must be a non-empty array."})
'''

HELPER_REPLACEMENT = '''    def _pre_dispatch_failure(output: str) -> str:
        # Called exclusively before any window focus, click, keyboard or launch.
        # The attestation is in-process, never inferred from a model/tool JSON field.
        from app.agent.durable.operation_execution import current_operation_execution
        execution = current_operation_execution()
        if execution is not None:
            execution.confirm_native_preflight_no_effect()
        return output

    if not isinstance(actions, list) or not actions:
        return _pre_dispatch_failure(json.dumps({"status": "error", "error": "actions must be a non-empty array."}))
'''

EARLY_REPLACEMENTS = [
    (
        '''    if budget_error is not None:
        return json.dumps(budget_error, ensure_ascii=False)
''',
        '''    if budget_error is not None:
        return _pre_dispatch_failure(json.dumps(budget_error, ensure_ascii=False))
''',
    ),
    (
        '''                return finish("error", reason_code="stale_state", error="state_id is expired, used, or belongs to another chat/control session.")
''',
        '''                return _pre_dispatch_failure(finish("error", reason_code="stale_state", error="state_id is expired, used, or belongs to another chat/control session."))
''',
    ),
    (
        '''                return finish("error", reason_code="window_mismatch", error="The requested window differs from the captured state.")
''',
        '''                return _pre_dispatch_failure(finish("error", reason_code="window_mismatch", error="The requested window differs from the captured state."))
''',
    ),
    (
        '''                return finish("error", reason_code="window_mismatch", error="The requested target differs from the captured state.")
''',
        '''                return _pre_dispatch_failure(finish("error", reason_code="window_mismatch", error="The requested target differs from the captured state."))
''',
    ),
    (
        '''            if target.get("status") != "ok":
                return json.dumps(target, ensure_ascii=False)
''',
        '''            if target.get("status") != "ok":
                return _pre_dispatch_failure(json.dumps(target, ensure_ascii=False))
''',
    ),
    (
        '''            if window and window_changed(window, selected):
                return finish("error", reason_code="stale_state", error="The supplied window changed. Capture a fresh state.")
''',
        '''            if window and window_changed(window, selected):
                return _pre_dispatch_failure(finish("error", reason_code="stale_state", error="The supplied window changed. Capture a fresh state."))
''',
    ),
    (
        '''                if params.get("status") in {"error", "blocked"}:
                    return json.dumps(params, ensure_ascii=False)
''',
        '''                if params.get("status") in {"error", "blocked"}:
                    return _pre_dispatch_failure(json.dumps(params, ensure_ascii=False))
''',
    ),
    (
        '''        if not state_id and any(action["type"] in {"click", "scroll", "drag"} for action in actions):
            return finish("error", reason_code="state_required", error="Capture a fresh window state before coordinate input and pass its state_id.")
''',
        '''        if not state_id and any(action["type"] in {"click", "scroll", "drag"} for action in actions):
            return _pre_dispatch_failure(finish("error", reason_code="state_required", error="Capture a fresh window state before coordinate input and pass its state_id."))
''',
    ),
]

TEST_ANCHOR = '''@pytest.fixture(autouse=True)
def clean_states():
'''

TEST_INSERT = '''def test_agentrobo_validation_error_is_attested_before_desktop_input(monkeypatch):
    from app.agent.durable import operation_execution

    class FakeExecution:
        calls = 0
        def confirm_native_preflight_no_effect(self):
            self.calls += 1

    fake = FakeExecution()
    monkeypatch.setattr(operation_execution, "current_operation_execution", lambda: fake)
    outcome = json.loads(tools._computer_functions_act(actions=[]))
    assert outcome["status"] == "error"
    assert fake.calls == 1


def test_agentrobo_input_failure_is_not_marked_no_effect(desktop, monkeypatch):
    from app.agent.durable import operation_execution

    class FakeExecution:
        calls = 0
        def confirm_native_preflight_no_effect(self):
            self.calls += 1

    fake = FakeExecution()
    monkeypatch.setattr(operation_execution, "current_operation_execution", lambda: fake)
    _, _, state_id, events = desktop
    monkeypatch.setattr(tools, "_dispatch_batch_action", lambda *a, **k: {"status": "error", "reason_code": "cannot_type"})
    outcome = json.loads(tools._computer_functions_act(actions=[{"type": "press_key", "key": "tab"}], state_id=state_id))
    assert outcome["status"] == "error"
    assert events == ["focus"]
    assert fake.calls == 0


''' + TEST_ANCHOR

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"Unexpected pinned Monaw source for {label}: {count} matching anchors")
    return text.replace(old, new, 1)

def run(root: Path) -> None:
    backend = root / "backend"
    op = backend / "app" / "agent" / "durable" / "operation_execution.py"
    tools = backend / "app" / "skills" / "computer_use" / "tools.py"
    tests = backend / "app" / "agent" / "tests" / "test_computer_state.py"

    content = op.read_text(encoding="utf-8")
    content = replace_once(content, EXECUTION_ANCHOR, EXECUTION_INSERT, str(op))
    op.write_text(content, encoding="utf-8", newline="\n")

    content = tools.read_text(encoding="utf-8")
    begin = content.index("def _computer_functions_act(")
    end = content.index("\ndef _computer_functions_clipboard(", begin)
    prefix, block, suffix = content[:begin], content[begin:end], content[end:]
    block = replace_once(block, HELPER_ANCHOR, HELPER_REPLACEMENT, "desktop preflight helper")
    for index, (old, new) in enumerate(EARLY_REPLACEMENTS):
        if index == 6:
            # Two independent pre-input UIA/index validation branches.
            if block.count(old) != 2:
                raise ValueError(f"Unexpected UIA validation branches: {block.count(old)}")
            block = block.replace(old, new, 2)
        else:
            block = replace_once(block, old, new, f"desktop preflight branch {index}")
    tools.write_text(prefix + block + suffix, encoding="utf-8", newline="\n")

    content = tests.read_text(encoding="utf-8")
    content = replace_once(content, TEST_ANCHOR, TEST_INSERT, str(tests))
    tests.write_text(content, encoding="utf-8", newline="\n")
    print("Patched locally provable pre-dispatch failures only. No behavior changes to uncertain sent input.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("monaw_root", type=Path)
    run(parser.parse_args().monaw_root.resolve())
