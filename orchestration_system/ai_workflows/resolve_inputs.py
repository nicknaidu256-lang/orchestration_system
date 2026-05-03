"""
Input resolution — converts $ref strings into actual state values.

Rules:
- Pure $ref values (entire value is "$key"): replaced with raw state value (any type)
- Template strings containing embedded $key tokens: each token is interpolated as a string
  (lists/dicts are JSON-serialised so they embed cleanly into LLM prompts)
- Non-string values or strings with no $ at all: passed through unchanged
- If any referenced key is missing or None in state: raise MissingStateError immediately
- Never passes None silently to an agent — fail fast

This is a pure function with no side effects.
"""

import json
import re
from typing import Any, Dict

from ai_workflows.errors import MissingStateError

# Matches $word_with_underscores_and_digits — valid state key references
_REF_PATTERN = re.compile(r'\$([A-Za-z_][A-Za-z0-9_]*)')


def _to_string(value: Any) -> str:
    """Serialize a state value to a string for embedding in a prompt template."""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=None)


def resolve_inputs(inputs: dict, state) -> dict:
    """
    Resolve all inputs for a step.

    Args:
        inputs: Step's input dict from the plan
        state: StateManager instance

    Returns:
        Dict with all $ref values replaced by actual state values

    Raises:
        MissingStateError: If any $ref key is not found in state (or is None)
    """
    resolved = {}
    for k, v in inputs.items():

        if not isinstance(v, str) or "$" not in v:
            # Non-string or no $ at all — pass through as-is
            resolved[k] = v
            continue

        refs = _REF_PATTERN.findall(v)

        if not refs:
            # Has a $ but no valid $key pattern — pass through
            resolved[k] = v
            continue

        # Check: is the entire value a single bare $key reference (e.g. "$results")?
        # If so, return the raw state value (preserves list/dict types for downstream agents).
        stripped = v.strip()
        if stripped.startswith("$") and stripped[1:] in refs and stripped == f"${stripped[1:]}":
            key = stripped[1:]
            value = state.get(key)
            if value is None:
                raise MissingStateError(
                    f"Step requires state key '{key}' (referenced as '${key}') "
                    f"but it is not present in state. "
                    f"This means a prior step did not produce this output, "
                    f"or the plan references a key that was never written."
                )
            resolved[k] = value
            continue

        # Otherwise: string template with one or more embedded $key tokens.
        # Interpolate each token as a string (serialise lists/dicts to JSON).
        def replacer(match):
            key = match.group(1)
            value = state.get(key)
            if value is None:
                raise MissingStateError(
                    f"Step requires state key '{key}' (referenced as '${key}') "
                    f"but it is not present in state. "
                    f"This means a prior step did not produce this output, "
                    f"or the plan references a key that was never written."
                )
            return _to_string(value)

        resolved[k] = _REF_PATTERN.sub(replacer, v)

    return resolved
