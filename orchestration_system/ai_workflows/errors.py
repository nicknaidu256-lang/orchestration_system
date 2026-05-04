"""
Error classes for AI Workflows system.
These define the explicit error taxonomy — each error has a single cause and action.
"""


class CorruptStateError(Exception):
    """
    Raised when a step is marked completed in status
    but its declared outputs are missing or None in state.
    This is a state integrity failure — not a retryable execution failure.
    Operator must inspect manually.
    """
    def __init__(self, run_id, step_id, missing_keys, plan_hash, snapshot_path):
        self.run_id = run_id
        self.step_id = step_id
        self.missing_keys = missing_keys
        self.plan_hash = plan_hash
        self.snapshot_path = snapshot_path
        super().__init__(
            f"CorruptState: run={run_id}, step={step_id}, "
            f"missing_keys={missing_keys}, plan_hash={plan_hash}, "
            f"snapshot={snapshot_path}"
        )


class StepFailure(Exception):
    """
    Raised when a step's agent executes but the result
    is missing a declared output key.
    May be retryable depending on step schema.
    Carries resolved_inputs so retry has full context.
    """
    def __init__(self, step, resolved_inputs, missing_output, message=""):
        self.step = step
        self.resolved_inputs = resolved_inputs
        self.missing_output = missing_output
        super().__init__(message or f"StepFailure: step={step['id']}, missing_output={missing_output}")


class MissingStateError(Exception):
    """
    Raised when input resolution finds a $ref key
    that is not present in state (or is None).
    Indicates a planning error or a failed upstream step.
    Always halts — never retries.
    """
    pass


class UnknownCapabilityError(Exception):
    """
    Raised when the registry does not contain
    the capability required by a step.
    Always halts — configuration error.
    """
    pass


class StateConflictError(Exception):
    """
    Raised when a step attempts to write an output key
    that already exists in state.
    State is append-only. This is a planning error.
    Always halts.
    """
    pass


class ApprovalDeniedError(Exception):
    """
    Raised when the user explicitly rejects a step at the approval gate.
    Always halts — user decision is final.
    """
    def __init__(self, step_id, message=""):
        self.step_id = step_id
        super().__init__(message or f"ApprovalDenied: step={step_id}")

