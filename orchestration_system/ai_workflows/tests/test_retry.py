#!/usr/bin/env python3
"""
Unit tests for AI Workflows retry logic.
Verifies that retryable steps correctly retry once on StepFailure.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_workflows.executor import compute_plan_hash, run_executor
from ai_workflows.state import StateManager
from ai_workflows.agents.kilocode import KiloCodeAgent
from ai_workflows.errors import StepFailure


def test_retryable_step_success_on_retry():
    """
    Test: Step is retryable. First attempt fails (StepFailure), second succeeds.
    Expected:
    - Agent.execute() called exactly twice.
    - State.write() called exactly once (after the second attempt).
    - Workflow completes successfully.
    """
    print("\n" + "="*60)
    print("TEST: Retryable step success on second attempt")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        run_dir = tmp_path / "runs" / "test_retry"
        run_dir.mkdir(parents=True)

        state = StateManager(run_dir)
        registry = {"text_generation": "kilocode"}

        steps = [{
            "id": "step_a",
            "capability": "text_generation",
            "inputs": {"prompt": "Try me"},
            "outputs": ["out"],
            "retryable": True,
            "idempotent": False
        }]
        plan = {
            "workflow_id": "test_retry_workflow",
            "version": "1.0",
            "plan_hash": compute_plan_hash(steps),
            "steps": steps
        }

        # Tracks calls
        execution_context = {
            "attempts": 0,
            "state_writes": 0
        }

        def mock_execute(*args, **kwargs):
            execution_context["attempts"] += 1
            if execution_context["attempts"] == 1:
                print("  Attempt 1: Failing as planned...")
                # Raise StepFailure to trigger retry
                raise StepFailure(
                    step=steps[0],
                    resolved_inputs={"prompt": "Try me"},
                    missing_output="out",
                    message="Simulated first-attempt failure"
                )
            else:
                print("  Attempt 2: Succeeding as planned...")
                return {"outputs": {"out": "Success!"}}

        # We also need to monitor state.write to ensure it's only called after success
        original_write = state.write
        def tracked_write(*args, **kwargs):
            execution_context["state_writes"] += 1
            return original_write(*args, **kwargs)

        with patch.object(KiloCodeAgent, 'execute', side_effect=mock_execute):
            with patch.object(state, 'write', side_effect=tracked_write):
                # We also need to mock KiloCodeAgent.__init__ to avoid CLI check
                with patch.object(KiloCodeAgent, '_verify_available', return_value=None):
                    run_executor(plan, state, registry, run_id="test_retry")

        print(f"  Attempts: {execution_context['attempts']}")
        print(f"  State Writes: {execution_context['state_writes']}")

        assert execution_context["attempts"] == 2, f"Expected 2 attempts, got {execution_context['attempts']}"
        assert execution_context["state_writes"] == 1, f"Expected 1 state write, got {execution_context['state_writes']}"
        assert state.get("out") == "Success!", "Final state should contain successful result"
        print("  [OK] Retry logic verified.")

if __name__ == "__main__":
    try:
        test_retryable_step_success_on_retry()
        print("\nALL RETRY TESTS PASSED [OK]")
    except Exception as e:
        print(f"\n[FAIL] Retry test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
