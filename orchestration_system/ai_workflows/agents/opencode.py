"""
OpenCode agent wrapper — handles opencode_task capability.
Supports both native installs and Windows-side installs called from WSL.
Agent ID: "opencode"
"""

import subprocess
from typing import Any, Dict
from ai_workflows.agents import Agent
from ai_workflows.agents.wsl_bridge import find_cli, run_cli, run_verify


class OpenCodeAgent(Agent):
    capability = "opencode_task"

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        task = inputs.get("task", "")
        working_dir = inputs.get("working_dir", ".")
        verify_command = inputs.get("verify_command")
        timeout = int(inputs.get("timeout", 300))

        location = find_cli("opencode")
        if location is None:
            return {
                "outputs": {
                    "success": False,
                    "output": "OpenCodeAgent: opencode CLI not found in PATH or Windows host. Install OpenCode.",
                    "verify_result": "",
                    "verify_passed": False
                }
            }

        try:
            result = run_cli(
                cli_name="opencode",
                args=["run", "--message", task],
                working_dir=working_dir,
                timeout=timeout
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
        except subprocess.TimeoutExpired:
            output = f"OpenCodeAgent: execution timed out after {timeout}s"
            success = False
        except Exception as e:
            output = f"OpenCodeAgent error: {str(e)}"
            success = False

        verify_result = ""
        verify_passed = False
        if verify_command and success:
            try:
                v = run_verify(verify_command, working_dir=working_dir)
                verify_result = v.stdout + v.stderr
                verify_passed = v.returncode == 0
            except Exception as e:
                verify_result = f"Verification error: {str(e)}"

        return {
            "outputs": {
                "success": success,
                "output": output,
                "verify_result": verify_result,
                "verify_passed": verify_passed
            }
        }
