"""
Verification agent wrapper — handles verify_tests capability.

Runs test commands and returns structured pass/fail data.

Agent ID: "verification"
"""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict

from ai_workflows.agents import Agent


class VerificationAgent(Agent):
    """
    Agent that runs verification tests and returns pass/fail data.
    """

    capability = "verify_tests"

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute test command.

        Args:
            inputs: {
                "test_command": str,
                "working_dir": str,
                "timeout": int (default: 120)
            }

        Returns:
            {
                "outputs": {
                    "tests_passed": bool,
                    "test_output": str,
                    "pass_count": int,
                    "fail_count": int,
                    "summary": str
                }
            }
        """
        test_command = inputs.get("test_command", "")
        working_dir = inputs.get("working_dir", ".")
        timeout = int(inputs.get("timeout", 120))

        try:
            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
                shell=True
            )
            test_output = result.stdout + "\n" + result.stderr
            tests_passed = result.returncode == 0

        except subprocess.TimeoutExpired:
            test_output = f"Test execution timed out after {timeout}s"
            tests_passed = False
        except Exception as e:
            test_output = f"Test error: {str(e)}"
            tests_passed = False

        # Count only lines that end with a [PASS]/[FAIL]/[OK] marker.
        # This avoids false positives from summary lines like
        # "ALL ACCEPTANCE TESTS PASSED" or "65 passed, 1 failed".
        pass_count = sum(
            1 for line in test_output.split('\n')
            if re.search(r'\[PASS\]|\[OK\]', line)
        )
        fail_count = sum(
            1 for line in test_output.split('\n')
            if re.search(r'\[FAIL\]|\[ERROR\]', line)
        )

        # Fallback for pytest-style output ("X passed, Y failed")
        if pass_count == 0 and fail_count == 0:
            match = re.search(r'(\d+)\s+passed', test_output, re.IGNORECASE)
            if match:
                pass_count = int(match.group(1))
            match = re.search(r'(\d+)\s+failed', test_output, re.IGNORECASE)
            if match:
                fail_count = int(match.group(1))

        summary = f"{pass_count} passed, {fail_count} failed"

        return {
            "outputs": {
                "tests_passed": tests_passed,
                "test_output": test_output,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "summary": summary
            }
        }
