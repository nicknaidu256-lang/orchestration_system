"""
OpenCode agent wrapper — handles code_generation capability.
Protocol: JSON stdin/stdout with {"inputs": {...}} → {"outputs": {...}}

Agent ID: "opencode"
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict

from ai_workflows.agents import Agent


class OpenCodeAgent(Agent):
    """
    Agent that delegates code generation tasks to OpenCode CLI.
    Communicates via JSON over stdin/stdout.
    """

    def __init__(self, opencode_path: str = "opencode"):
        self.opencode_path = opencode_path
        self._verify_available()

    def _verify_available(self):
        try:
            subprocess.run(
                [self.opencode_path, "--version"],
                capture_output=True, text=True, timeout=5
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"OpenCode not found at '{self.opencode_path}'. "
                f"Ensure OpenCode CLI is installed and in PATH."
            )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute code generation via OpenCode.

        Protocol:
        stdin:  {"inputs": <inputs_dict>}
        stdout: {"outputs": {"code": "...", "explanation": "..."}}}

        Args:
            inputs: Resolved input dict from executor

        Returns:
            Dict with "outputs" key containing generated code
        """
        payload = {"inputs": inputs}

        try:
            result = subprocess.run(
                [self.opencode_path, "--json-io", "--no-prompt"],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, self.opencode_path, result.stdout, result.stderr
                )

            response = json.loads(result.stdout.strip())

            # Enforce protocol: must have top-level "outputs"
            if "outputs" not in response:
                raise ValueError(
                    f"OpenCode response missing 'outputs' key. Got: {list(response.keys())}"
                )

            return response

        except json.JSONDecodeError as e:
            raise ValueError(f"OpenCode returned invalid JSON: {e}")
        except subprocess.TimeoutExpired:
            raise TimeoutError("OpenCode execution timed out after 300s")

