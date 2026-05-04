"""
KiloCode agent wrapper — handles kilocode_task capability.
Supports both native installs and Windows-side installs called from WSL.
Agent ID: "kilocode"
"""

import os
import subprocess
from typing import Any, Dict
from ai_workflows.agents import Agent
from ai_workflows.agents.wsl_bridge import find_cli, run_cli, run_verify

# @kilocode/cli registers as 'kilo-code'; older installs used 'kilo'
_KILO_CMD = None

def _get_kilo_cmd():
    global _KILO_CMD
    if _KILO_CMD is None:
        for candidate in ["kilo-code", "kilo"]:
            if find_cli(candidate):
                _KILO_CMD = candidate
                break
    return _KILO_CMD


class KiloCodeAgent(Agent):
    capability = "kilocode_task"

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        task = inputs.get("task")
        working_dir = inputs.get("working_dir", ".")
        verify_command = inputs.get("verify_command")
        timeout = inputs.get("timeout", 300)

        if not task:
            raise ValueError("KiloCodeAgent requires 'task' parameter.")

        if not os.path.exists(working_dir):
            os.makedirs(working_dir, exist_ok=True)

        cmd = _get_kilo_cmd()
        if cmd is None:
            return {
                "outputs": {
                    "success": False,
                    "output": "KiloCodeAgent: kilo-code/kilo CLI not found. Install via: npm install -g @kilocode/cli",
                    "verify_result": "",
                    "verify_passed": False
                }
            }

        try:
            result = run_cli(
                cli_name=cmd,
                args=["--message", task],
                working_dir=working_dir,
                timeout=timeout
            )

            # Fallback if --message flag not recognised
            if result.returncode != 0 and "unknown" in result.stderr.lower():
                result = run_cli(
                    cli_name=cmd,
                    args=["run", task],
                    working_dir=working_dir,
                    timeout=timeout
                )

            success = result.returncode == 0
            output = result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            return {
                "outputs": {
                    "success": False,
                    "output": f"KiloCodeAgent: Task timed out after {timeout}s",
                    "verify_result": "",
                    "verify_passed": False
                }
            }
        except Exception as e:
            return {
                "outputs": {
                    "success": False,
                    "output": f"KiloCodeAgent error: {str(e)}",
                    "verify_result": "",
                    "verify_passed": False
                }
            }

        verify_result = ""
        verify_passed = False
        if verify_command:
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
