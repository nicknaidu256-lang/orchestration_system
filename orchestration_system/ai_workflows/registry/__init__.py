"""
Registry loader — flat JSON mapping, no scoring, no fallback logic.
If capability not in mapping: raise UnknownCapabilityError immediately.
"""

import json
from pathlib import Path

from ai_workflows.errors import UnknownCapabilityError


def load_registry(registry_path: Path) -> dict:
    """
    Load the capability → agent registry from JSON.

    Args:
        registry_path: Path to registry.json

    Returns:
        Dict mapping capability names to agent identifiers

    Raises:
        FileNotFoundError: If registry file doesn't exist
        json.JSONDecodeError: If registry is invalid JSON
    """
    with open(registry_path, 'r') as f:
        data = json.load(f)
    return data.get("mapping", {})


def get_agent(registry: dict, capability: str):
    """
    Look up agent by capability.

    This function does NOT load the agent — it only returns the agent identifier
    string. The caller is responsible for loading the actual agent implementation.

    Args:
        registry: The loaded registry dict
        capability: The capability name from the step

    Returns:
        Agent identifier string (e.g. "opencode", "local_fs")

    Raises:
        UnknownCapabilityError: If capability not in registry
    """
    if capability not in registry:
        raise UnknownCapabilityError(
            f"Capability '{capability}' not found in registry. "
            f"Available capabilities: {list(registry.keys())}"
        )
    return registry[capability]

