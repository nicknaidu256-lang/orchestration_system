"""
Top-level orchestration — wraps executor with error handling.

ONLY changes from previous version:
- Removed retry_step() function (retry now inline in executor)
- No longer passes retry logic to error handler
"""

import sys
from pathlib import Path
from typing import Any, Dict

from ai_workflows.errors import (
    ApprovalDeniedError,
    CorruptStateError,
    MissingStateError,
    StateConflictError,
    StepFailure,
    UnknownCapabilityError,
)
from ai_workflows.executor import run_executor
from ai_workflows.state import StateManager


def halt(message: str, exit_code: int = 1):
    print(f"\n[FATAL] {message}")
    sys.exit(exit_code)


def log_error(error):
    print(f"\n[ERROR] {type(error).__name__}: {error}")


def run_workflow(
    plan: dict,
    run_dir: Path,
    registry: dict = None,
    agent_kwargs: dict = None
):
    """
    Top-level entry point.

    Wraps run_executor with error handling.
    Retries are handled inline by the executor — error handler just halts on final failure.
    """
    run_id = run_dir.name
    state = StateManager(run_dir)

    if registry is None:
        from ai_workflows.registry import load_registry
        registry_path = Path(__file__).parent.parent / "registry" / "registry.json"
        registry = load_registry(registry_path)

    try:
        run_executor(plan, state, registry, run_id, agent_kwargs)
        print(f"\n[SUCCESS] Workflow '{plan['workflow_id']}' completed.")
        print(f"  Run directory: {run_dir}")

    except CorruptStateError as e:
        log_error(e)
        halt(
            f"CORRUPT STATE: run={e.run_id}, step={e.step_id}, "
            f"missing={e.missing_keys}, plan_hash={e.plan_hash}. "
            f"Inspect snapshot at {e.snapshot_path}. Halting."
        )

    except StepFailure as e:
        log_error(e)
        halt(f"STEP FAILURE: step={e.step['id']}, missing_output={e.missing_output}")

    except MissingStateError as e:
        log_error(e)
        halt(f"MISSING STATE REF: {e}")

    except UnknownCapabilityError as e:
        log_error(e)
        halt(f"UNKNOWN CAPABILITY: {e}")

    except StateConflictError as e:
        log_error(e)
        halt(f"STATE CONFLICT: {e}")

    except ApprovalDeniedError as e:
        log_error(e)
        halt(f"APPROVAL DENIED: step={e.step_id}")

    except Exception as e:
        log_error(e)
        halt(f"UNEXPECTED ERROR: {type(e).__name__}: {e}")

