"""
Base Agent class and package entrypoint for ai_workflows agents.
All agent implementations must subclass Agent and implement execute().
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class Agent(ABC):
    """
    Abstract base class for all agents.

    Every agent must implement execute(), which receives a resolved
    inputs dict and returns a dict containing an 'outputs' key.
    """

    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's capability.

        Args:
            inputs: Resolved input dict from the executor

        Returns:
            Dict with at minimum an 'outputs' key containing
            the declared output keys for this step
        """
        ...


class MockTextGenerationAgent(Agent):
    """Returns deterministic generated text."""

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        prompt = inputs.get("prompt", "")
        return {
            "outputs": {
                "text": f"[MOCK] Generated response to: {prompt[:60]}",
                "tokens_used": 42
            }
        }


class MockFileWriteAgent(Agent):
    """Writes to a temp file, returns path."""

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import tempfile
        path_str = inputs.get("path")
        content = inputs.get("content", "")
        # Actually write to a temp file to verify it works
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            temp_path = f.name
        return {"outputs": {"file_path": temp_path, "success": True}}
