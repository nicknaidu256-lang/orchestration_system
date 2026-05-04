import subprocess
from typing import Any, Dict
from ai_workflows.agents import Agent
from ai_workflows.agents.wsl_bridge import find_cli, run_cli, run_verify


class ClaudeCodeAgent(Agent):
    """
    Agent that invokes the Claude Code CLI non-interactively.
    Supports both native installs and Windows-side installs called from WSL.
    Capability: "claude_code_task"
    """
    capability = "claude_code_task"

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        task = inputs.get("task")
        working_dir = inputs.get("working_dir", ".")
        verify_command = inputs.get("verify_command")
        timeout = inputs.get("timeout", 300)

        if not task:
            raise ValueError("ClaudeCodeAgent requires a 'task' description.")

        location = find_cli("claude")
        if location is None:
            return {
                "outputs": {
                    "success": False,
                    "output": "ClaudeCodeAgent: claude CLI not found in PATH. Install Claude Code.",
                    "verify_result": "",
                    "verify_passed": False
                }
            }

        try:
            result = run_cli(
                cli_name="claude",
                args=["--print", task],
                working_dir=working_dir,
                timeout=timeout
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
        except subprocess.TimeoutExpired:
            return {
                "outputs": {
                    "success": False,
                    "output": "ClaudeCodeAgent: Task timed out.",
                    "verify_result": "",
                    "verify_passed": False
                }
            }
        except Exception as e:
            return {
                "outputs": {
                    "success": False,
                    "output": f"ClaudeCodeAgent: Unexpected error: {str(e)}",
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
                verify_result = f"Verification failed: {str(e)}"
                verify_passed = False

        return {
            "outputs": {
                "success": success,
                "output": output,
                "verify_result": verify_result,
                "verify_passed": verify_passed
            }
        }
