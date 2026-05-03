"""
StateManager — per-run isolated state with atomic writes and append-only enforcement.

Design decisions (non-negotiable):
- Flat key-value store (no namespacing)
- Atomic writes via .tmp + rename()
- Append-only: write raises StateConflictError if key already exists
- Status and outputs committed together in single atomic operation
- Snapshots are best-effort forensic logs, written AFTER state commit
- Each run gets its own directory: ~/.ai-workflows/runs/{run_id}/
"""

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from ai_workflows.errors import StateConflictError


class StateManager:
    """
    Manages per-run state with atomic writes and append-only guarantees.
    State file: ~/.ai-workflows/runs/{run_id}/state.json
    Snapshots:  ~/.ai-workflows/runs/{run_id}/steps/{step_id}.json
    """

    def __init__(self, run_dir: Path):
        self.state_path = run_dir / "state.json"
        self.steps_dir = run_dir / "steps"
        self.steps_dir.mkdir(parents=True, exist_ok=True)
        self._state = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load existing state or return fresh {'status': {}}."""
        if self.state_path.exists():
            return json.loads(self.state_path.read_text())
        return {"status": {}}

    def get(self, key: str) -> Any:
        """
        Return the value for key, or None if not present.
        Used by resolve_inputs for $ref resolution.
        """
        return self._state.get(key)

    def read_all(self) -> Dict[str, Any]:
        """Return the current in-memory state."""
        return deepcopy(self._state)

    def has(self, key: str) -> bool:
        """
        A key is considered present only if it exists AND is not None.
        This is used for idempotency checks and output validation.
        """
        return key in self._state and self._state[key] is not None

    def all_outputs_present(self, outputs: list) -> bool:
        """
        Returns True only if every declared output key is present and non-None.
        Used in the idempotency check before skipping a step.
        """
        return all(self.has(k) for k in outputs)

    def is_completed(self, step_id: str) -> bool:
        """
        Returns True if the step's status is 'completed'.
        Used in the idempotency check.
        """
        return self._state.get("status", {}).get(step_id) == "completed"

    def mark_waiting_approval(self, step_id: str):
        """
        Used if non-blocking approval is ever added in v2.
        Not used in v1 — v1 uses blocking approval via pause_for_approval().
        This is a placeholder to satisfy the spec.
        """
        pass  # v1 uses blocking approval — this is a placeholder only

    def write(self, outputs: list, result: dict, step_id: str):
        """
        Write step outputs and mark step completed — atomically.

        Process:
        1. Deep-copy current state to temp dict
        2. For each output key:
           - If key already exists in temp (and is not 'status'): raise StateConflictError
           - Otherwise: set temp[key] = result[key]
        3. Set temp["status"][step_id] = "completed"
        4. Atomic write: serialize to .tmp file, then rename() to state.json
        5. Update in-memory _state to match

        Raises:
            StateConflictError: If any output key already exists in state.
        """
        temp = deepcopy(self._state)

        for key in outputs:
            if key in temp and key != "status":
                raise StateConflictError(
                    f"Key '{key}' already exists in state. "
                    f"Step '{step_id}' attempted to overwrite it. "
                    f"State is append-only. This is a planning error."
                )
            temp[key] = result[key]

        temp["status"][step_id] = "completed"
        self._atomic_write(temp)

    def _atomic_write(self, new_state: dict):
        """
        Write state atomically using temp file + rename().
        This is crash-safe: either the old state or the new state exists,
        never a partially-written file.
        """
        temp_path = self.state_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(new_state, indent=2))
        temp_path.replace(self.state_path)
        self._state = new_state  # keep in-memory state in sync

    def snapshot(self, step_id: str, resolved_inputs: dict, result: dict, plan_hash: str):
        """
        Write a forensic snapshot of this step's execution.
        Best-effort only — not part of atomic guarantee.
        Written AFTER state commit. State is the source of truth.

        Format:
        {
          "step_id": "...",
          "resolved_inputs": {...},
          "result": {...},
          "timestamp": "2024-01-01T00:00:00Z",
          "status": "completed",
          "plan_hash": "<same hash as in the plan>"
        }
        """
        snapshot_data = {
            "step_id": step_id,
            "resolved_inputs": resolved_inputs,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed",
            "plan_hash": plan_hash
        }
        path = self.steps_dir / f"{step_id}.json"
        path.write_text(json.dumps(snapshot_data, indent=2))

