"""
Quick sanity test — exercises generate_and_write workflow end-to-end.

This is NOT an acceptance test. It's a basic smoke test.
Run with: python test_smoke.py
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from ai_workflows.executor import compute_plan_hash, run_executor
from ai_workflows.state import StateManager
from ai_workflows.registry import load_registry
from ai_workflows.agents.local_fs import LocalFSAgent
from ai_workflows.agents.kilocode import KiloCodeAgent

# Monkey-patch KiloCode to return deterministic text (avoid real LLM calls)
original_kc_execute = KiloCodeAgent.execute

def fake_kc_execute(self, inputs):
    prompt = inputs.get("prompt", "")
    return {
        "text": f"GENERATED: {prompt[:50]}",
        "model": "fake-model",
        "tokens_used": 10
    }

def test_smoke():
    print("Smoke test: generate_and_write workflow (with mocked KiloCode)")

    # Load real plan
    plan_path = Path(__file__).parent.parent / "plans" / "generate_and_write.json"
    if not plan_path.exists():
        print(f"ERROR: Plan not found: {plan_path}")
        sys.exit(1)

    plan = json.loads(plan_path.read_text())

    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp) / "runs" / "smoke_test"
        run_dir.mkdir(parents=True)
        state = StateManager(run_dir)

        # Registry: map text_generation → kilocode (even though we mock it)
        registry = {
            "text_generation": "kilocode",
            "file_write": "local_fs",
        }

        with patch.object(KiloCodeAgent, 'execute', side_effect=fake_kc_execute):
            run_executor(plan, state, registry, run_id="smoke")

        # Verify outputs
        assert state.has("generated_text"), "generated_text should exist in state"
        assert state.has("file_path"), "file_path should exist in state"

        output_file = Path(state.get("file_path"))
        assert output_file.exists(), f"Output file should exist: {output_file}"
        content = output_file.read_text()
        assert "GENERATED:" in content, f"File should contain generated text. Got: {content}"

        print("✓ Smoke test passed.")
        print(f"  Generated text: {state.get('generated_text')}")
        print(f"  Written to: {output_file}")
        print(f"  File content: {content.strip()}")

if __name__ == "__main__":
    test_smoke()

