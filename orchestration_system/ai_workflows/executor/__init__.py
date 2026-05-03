"""
Executor — deterministic, mechanical runner.
No LLM calls. No reasoning. No branching on model output.
The plan is immutable — never modified inside this function.

Protocol enforcement:
- Agent must return {"outputs": {...}}
- Every declared output key must exist in result["outputs"]
- On StepFailure with retryable: true, retry ONCE inside the loop (no external retry_step)

Replanning policy:
- Replanning is ONLY attempted for transient execution failures (StepFailure, generic Exception)
- The following errors are STRUCTURAL/INTENTIONAL HALTS and are NEVER replanned:
    MissingStateError    — planning error (bad $ref)
    StateConflictError   — planning error (duplicate output key)
    ApprovalDeniedError  — user decision is final
    UnknownCapabilityError — configuration error
    CorruptStateError    — state integrity failure, needs manual inspection
"""

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union

from ai_workflows.agents.loader import load_agent
from ai_workflows.errors import (
    ApprovalDeniedError,
    CorruptStateError,
    MissingStateError,
    StateConflictError,
    StepFailure,
    UnknownCapabilityError,
)
from ai_workflows.registry import load_registry, get_agent
from ai_workflows.resolve_inputs import resolve_inputs
from ai_workflows.state import StateManager
from ai_workflows.planner.replanner import Replanner

# Errors that indicate a structural/intentional halt — replanning cannot fix these.
_NO_REPLAN_ERRORS = (
    MissingStateError,
    StateConflictError,
    ApprovalDeniedError,
    UnknownCapabilityError,
    CorruptStateError,
)


def compute_plan_hash(steps: list) -> str:
    canonical = json.dumps(steps, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def pause_for_approval(step: dict, inputs: dict):
    print(f"\n{'='*60}")
    print(f"APPROVAL REQUIRED")
    print(f"Step ID:    {step['id']}")
    print(f"Capability: {step['capability']}")
    print(f"Inputs:     {json.dumps(inputs, indent=2)}")
    print(f"{'='*60}")
    response = input("Press Enter to approve, or type 'no' to abort: ").strip().lower()
    if response in ("no", "n"):
        raise ApprovalDeniedError(
            step_id=step["id"],
            message=f"User rejected approval for step '{step['id']}'"
        )


def run_workflow(plan: dict, run_dir: Path, agent_kwargs: dict = None):
    """
    Entry point for running a workflow.
    Initializes state and runs the executor loop.
    """
    from ai_workflows.state import StateManager
    from ai_workflows.registry import load_registry

    state = StateManager(run_dir)
    # The registry is relative to the package root
    package_root = Path(__file__).parent.parent
    registry_path = package_root / "registry" / "registry.json"
    registry = load_registry(registry_path)
    run_id = run_dir.name

    return run_executor(plan, state, registry, run_id, agent_kwargs)


def run_executor(
    plan: dict,
    state: StateManager,
    registry: dict,
    run_id: str,
    agent_kwargs: dict = None
):
    """
    Deterministic executor loop with support for parallel groups.
    """
    plan_hash = plan["plan_hash"]
    agent_kwargs = agent_kwargs or {}
    state_lock = threading.Lock()

    # ── STEP 1: PRE-PROCESS STEPS INTO EXECUTION UNITS ──────────
    execution_units: List[Union[dict, List[dict]]] = []
    current_group = []
    group_name = None

    for step in plan["steps"]:
        s_group = step.get("parallel_group")
        if s_group:
            if group_name and group_name != s_group:
                execution_units.append(current_group)
                current_group = []
            group_name = s_group
            current_group.append(step)
        else:
            if current_group:
                execution_units.append(current_group)
                current_group = []
                group_name = None
            execution_units.append(step)
    if current_group:
        execution_units.append(current_group)

    # ── STEP 2: EXECUTION LOOP ──────────────────────────────────
    replanner = Replanner()
    for unit_index, unit in enumerate(execution_units):
        if isinstance(unit, list):
            # Parallel execution
            with ThreadPoolExecutor() as executor:
                futures = []
                for step in unit:
                    futures.append(executor.submit(
                        _execute_single_step,
                        step, state, registry, plan_hash, run_id, agent_kwargs, state_lock
                    ))
                for future in futures:
                    future.result()
        else:
            # Sequential execution
            try:
                _execute_single_step(unit, state, registry, plan_hash, run_id, agent_kwargs, state_lock)
            except Exception as e:
                # Structural/intentional halts — replanning cannot fix these, re-raise immediately.
                if isinstance(e, _NO_REPLAN_ERRORS):
                    raise

                # Transient failure — attempt dynamic replan before halting.
                print(f"[Executor] Step '{unit['id']}' failed: {e}")
                print(f"[Executor] Attempting dynamic replan...")

                completed_step_ids = {s["id"] for s in plan["steps"][:unit_index]}
                remaining = [
                    s for s in plan["steps"]
                    if s["id"] not in completed_step_ids and s["id"] != unit["id"]
                ]

                package_root = Path(__file__).parent.parent
                registry_path = package_root / "registry" / "registry.json"
                registry_data = load_registry(registry_path)

                revised = replanner.replan(unit, state.read_all(), remaining, registry_data)

                if revised is None or len(revised) == 0:
                    raise StepFailure(
                        step=unit,
                        resolved_inputs={},
                        missing_output="unknown",
                        message=f"Replanning failed or returned no steps. Original error: {e}"
                    ) from e
                else:
                    execution_units[unit_index + 1:] = revised
                    print(f"[Executor] Replanned — continuing with {len(revised)} revised steps.")
                    continue


def _execute_single_step(
    step: dict,
    state: StateManager,
    registry: dict,
    plan_hash: str,
    run_id: str,
    agent_kwargs: dict,
    state_lock: threading.Lock
):
    """
    Executes a single step.
    """
    step_id = step["id"]

    # ── IDEMPOTENCY CHECK ──────────────────────────────────────
    if state.is_completed(step_id) and step.get("idempotent", False):
        if not state.all_outputs_present(step["outputs"]):
            missing = [k for k in step["outputs"] if not state.has(k)]
            raise CorruptStateError(
                run_id=run_id,
                step_id=step_id,
                missing_keys=missing,
                plan_hash=plan_hash,
                snapshot_path=f"steps/{step_id}.json"
            )
        print(f"  [SKIP] Step '{step_id}' already completed (idempotent).")
        return

    # ── INPUT RESOLUTION ───────────────────────────────────────
    inputs = resolve_inputs(step["inputs"], state)

    # ── APPROVAL GATE ──────────────────────────────────────────
    if step.get("requires_approval"):
        pause_for_approval(step, inputs)

    # ── REGISTRY LOOKUP ────────────────────────────────────────
    agent_name = get_agent(registry, step["capability"])
    agent = load_agent(agent_name, **agent_kwargs)

    # ── EXECUTION (with inline retry) ──────────────────────────
    attempt = 0
    max_attempts = 2 if step.get("retryable") else 1

    while attempt < max_attempts:
        attempt += 1
        try:
            result = agent.execute(inputs)

            # ── OUTPUT VALIDATION ───────────────────────────────
            if "outputs" not in result:
                raise StepFailure(
                    step=step,
                    resolved_inputs=inputs,
                    missing_output="<top-level outputs key missing>",
                    message=(
                        f"Agent response missing top-level 'outputs' key. "
                        f"Got keys: {list(result.keys())}"
                    )
                )

            outputs_dict = result["outputs"]
            missing = [k for k in step["outputs"] if k not in outputs_dict]
            if missing:
                raise StepFailure(
                    step=step,
                    resolved_inputs=inputs,
                    missing_output=missing[0],
                    message=(
                        f"Agent outputs missing declared key '{missing[0]}'. "
                        f"Declared: {step['outputs']}, Got: {list(outputs_dict.keys())}"
                    )
                )

            # ── STATE WRITE (Thread Safe) ────────────────────────
            with state_lock:
                state.write(step["outputs"], outputs_dict, step_id)
                state.snapshot(step_id, inputs, result, plan_hash)

            print(f"  [DONE] Step '{step_id}' completed.")
            break

        except StepFailure:
            if step.get("retryable") and attempt < max_attempts:
                print(f"  [RETRY] Step '{step_id}' failed, retrying...")
                continue
            else:
                raise
