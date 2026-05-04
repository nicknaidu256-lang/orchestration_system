"""
KiloCode agent wrapper — handles text_generation capability.
Protocol: JSON stdin/stdout with {"inputs": {...}} → {"outputs": {...}}

Agent ID: "kilocode"
"""

import json
import subprocess
from typing import Any, Dict

from ai_workflows.agents import Agent


class KiloCodeAgent(Agent):
    """
    Agent that delegates text generation to KiloCode CLI.
    Communicates via JSON over stdin/stdout.
    """

    def __init__(self, kilocode_path: str = "kilo"):
        self.kilocode_path = kilocode_path
        self._verify_available()

    def _verify_available(self):
        try:
            subprocess.run(
                [self.kilocode_path, "--version"],
                capture_output=True, text=True, timeout=5,
                shell=True
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"KiloCode not found at '{self.kilocode_path}'. "
                f"Ensure KiloCode CLI is installed and in PATH."
            )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute text generation via KiloCode.

        Protocol:
        stdin:  {"inputs": {"prompt": "...", "temperature": 0.7, ...}}
        stdout: {"outputs": {"text": "...", "tokens_used": 123}}

        Args:
            inputs: Resolved input dict (must contain "prompt")

        Returns:
            Dict with "outputs" key containing generated text
        """
        if "prompt" not in inputs:
            raise ValueError("text_generation requires 'prompt' in inputs")

        payload = {"inputs": inputs}

        try:
            result = subprocess.run(
                [self.kilocode_path, "complete", "--json-io"],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=60,
                shell=True
            )

            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, self.kilocode_path, result.stdout, result.stderr
                )

            response = json.loads(result.stdout.strip())

            # Enforce protocol: must have top-level "outputs"
            if "outputs" not in response:
                raise ValueError(
                    f"KiloCode response missing 'outputs' key. Got: {list(response.keys())}"
                )

            # Validate required output field
            if "text" not in response["outputs"]:
                raise ValueError(
                    f"KiloCode outputs missing 'text' field. Got: {list(response['outputs'].keys())}"
                )

            return response

        except json.JSONDecodeError as e:
            raise ValueError(f"KiloCode returned invalid JSON: {e}")
        except subprocess.TimeoutExpired:
            raise TimeoutError("KiloCode execution timed out after 60s")

