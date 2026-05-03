import json
import hashlib
from typing import Any, Dict, List

def compute_plan_hash(steps: List[Dict]) -> str:
    """
    Compute canonical SHA256 hash of steps array.
    Canonicalization: json.dumps(steps, sort_keys=True, separators=(',', ':'))
    """
    canonical = json.dumps(steps, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()

class PlanBuilder:
    """
    Fluent builder for creating workflow plans.
    Enforces schema structure and computes plan_hash automatically.
    """

    def __init__(self, workflow_id: str, version: str = "1.0"):
        self.workflow_id = workflow_id
        self.version = version
        self.steps: List[Dict] = []

    def add_step(
        self,
        id: str,
        capability: str,
        inputs: Dict[str, Any],
        outputs: List[str],
        idempotent: bool = False,
        retryable: bool = False,
        requires_approval: bool = False
    ):
        """
        Add a step to the plan.
        """
        step = {
            "id": id,
            "capability": capability,
            "inputs": inputs,
            "outputs": outputs,
            "idempotent": idempotent,
            "retryable": retryable,
            "requires_approval": requires_approval
        }
        self.steps.append(step)
        return self

    def build(self, created_by: str = "hermes") -> Dict:
        """
        Build the final plan dict with computed plan_hash.
        """
        plan_hash = compute_plan_hash(self.steps)
        plan = {
            "workflow_id": self.workflow_id,
            "version": self.version,
            "created_by": created_by,
            "plan_hash": plan_hash,
            "steps": self.steps
        }
        return plan


def validate_plan(plan: Dict) -> bool:
    """
    Basic validation of plan structure and parallel constraints.
    Raises descriptive errors if invalid.
    """
    required_top = {"workflow_id", "version", "created_by", "plan_hash", "steps"}
    missing = required_top - set(plan.keys())
    if missing:
        raise ValueError(f"Plan missing required keys: {missing}")

    if not isinstance(plan["steps"], list):
        raise ValueError("plan['steps'] must be a list")

    parallel_groups = {}  # group_name -> list of steps
    active_group = None

    for i, step in enumerate(plan["steps"]):
        required_step = {"id", "capability", "inputs", "outputs"}
        missing_step = required_step - set(step.keys())
        if missing_step:
            raise ValueError(f"Step {i} ({step.get('id', '?')}) missing keys: {missing_step}")

        # Parallel group validation
        group = step.get("parallel_group")
        if group:
            if step.get("requires_approval"):
                raise ValueError(f"Step {step['id']} cannot have requires_approval in a parallel group")

            if active_group and active_group != group:
                # Group ended, check if it was seen before
                if group in parallel_groups:
                    raise ValueError(f"Parallel group '{group}' steps are not consecutive")
            active_group = group
            parallel_groups.setdefault(group, []).append(step)
        else:
            active_group = None

        # Check dependencies within parallel groups
        if group:
            for input_key, input_val in step.get("inputs", {}).items():
                if isinstance(input_val, str) and input_val.startswith("$"):
                    ref = input_val[1:]
                    # Check if reference is produced by another step in the SAME group
                    for other_step in parallel_groups[group]:
                        if other_step["id"] != step["id"] and ref in other_step["outputs"]:
                            raise ValueError(f"Step {step['id']} references output of step {other_step['id']} within same parallel group")

    # Verify plan_hash matches computed hash
    computed = compute_plan_hash(plan["steps"])
    if plan["plan_hash"] != computed:
        raise ValueError(
            f"plan_hash mismatch. Expected computed hash: {computed}, "
            f"got: {plan['plan_hash']}. Plan was tampered with or miscomputed."
        )

    return True
