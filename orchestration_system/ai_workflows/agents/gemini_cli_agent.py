import subprocess
import os
import shutil
from typing import Any, Dict
from ai_workflows.agents import Agent

class GeminiCLIAgent(Agent):
    """
    Agent for running tasks via Gemini CLI.
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        task = inputs.get("task")
        working_dir = inputs.get("working_dir", ".")
        verify_command = inputs.get("verify_command")
        timeout = inputs.get("timeout", 300)

        if not task:
            raise ValueError("GeminiCLIAgent requires 'task' parameter.")

        # Ensure working directory exists
        if not os.path.exists(working_dir):
            os.makedirs(working_dir, exist_ok=True)

        # Check if gemini CLI is available
        if not self._is_cli_available("gemini"):
            return {
                "outputs": {
                    "success": False,
                    "output": "GeminiCLIAgent: gemini CLI not found. Install Gemini CLI.",
                    "verify_result": "",
                    "verify_passed": False
                }
            }

        try:
            # Try gemini -p "{task}"
            result = subprocess.run(
                ["gemini", "-p", task],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True
            )

            # Fallback if -p fails (e.g. unknown flag)
            if result.returncode != 0 and ("unknown" in result.stderr.lower()):
                result = subprocess.run(
                    ["gemini", "--prompt", task],
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=True
                )

            success = (result.returncode == 0)
            output = result.stdout + result.stderr
            verify_result = ""
            verify_passed = False

            if verify_command:
                v_res = subprocess.run(
                    verify_command,
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    shell=True
                )
                verify_result = v_res.stdout + v_res.stderr
                verify_passed = (v_res.returncode == 0)

            return {
                "outputs": {
                    "success": success,
                    "output": output,
                    "verify_result": verify_result,
                    "verify_passed": verify_passed
                }
            }

        except subprocess.TimeoutExpired:
            return {
                "outputs": {
                    "success": False,
                    "output": f"GeminiCLIAgent: Task timed out after {timeout}s",
                    "verify_result": "",
                    "verify_passed": False
                }
            }
        except Exception as e:
            return {
                "outputs": {
                    "success": False,
                    "output": f"GeminiCLIAgent error: {str(e)}",
                    "verify_result": "",
                    "verify_passed": False
                }
            }

    def _is_cli_available(self, name: str) -> bool:
        try:
            # Use shell=True for Windows compatibility
            subprocess.run([name, "--version"], capture_output=True, shell=True)
            return True
        except:
            return shutil.which(name) is not None
