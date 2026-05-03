"""
Local filesystem agent — handles file_write capability.
Protocol: receives {"inputs": {...}}, returns {"outputs": {...}}
"""

import os
from pathlib import Path
from typing import Any, Dict

from ai_workflows.agents import Agent


class LocalFSAgent(Agent):
    """
    Agent for local filesystem operations.
    Capability: "file_write"

    Optional input: output_key (str)
        When provided, the agent adds {output_key: True} to the outputs dict.
        This lets plan steps declare a semantically-named output key
        (e.g. "summary_written") rather than the agent's fixed keys,
        avoiding StepFailure on output-key validation.

        Without output_key, the agent returns only the fixed keys:
        {"success": bool, "path": str, "output_code": str}

        With output_key="summary_written", it returns:
        {"success": bool, "path": str, "output_code": str, "summary_written": True}
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute file operations.

        Expected inputs (after resolution):
        - path: str (file path to write, or 'file_name' for backward compatibility)
        - content: str (file contents)
        - output_key: str (optional — adds {output_key: True} to outputs)
        - operation: "file_write" (default if not provided)

        Returns:
            {"outputs": {"success": bool, "path": str, "output_code": str[, output_key: True]}}
        """
        operation = inputs.get("operation", "file_write")

        # Handle code generation inputs for compatibility
        if operation == "file_write":
            if "file_name" in inputs:
                path_str = inputs.get("file_name")
                content = inputs.get("content")
            elif "destination_folder" in inputs and "file_content" in inputs:
                path_str = os.path.join(inputs.get("destination_folder"), "output.py")
                content = inputs.get("file_content")
            else:
                path_str = inputs.get("path")
                content = inputs.get("content")
        else:
            path_str = inputs.get("path")
            content = inputs.get("content")

        if path_str is None or content is None:
            raise ValueError(
                f"file_write requires 'path'/'file_name' and 'content' parameters. "
                f"Got: {list(inputs.keys())}"
            )

        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        outputs = {
            "success": True,
            "path": str(path.resolve()),
            "output_code": content,
        }

        # If the plan step declared a semantic output key, include it so the
        # executor's output-key validation passes without a StepFailure.
        output_key = inputs.get("output_key")
        if output_key:
            outputs[output_key] = True

        return {"outputs": outputs}
