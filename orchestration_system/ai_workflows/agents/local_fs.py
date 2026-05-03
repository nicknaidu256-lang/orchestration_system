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
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute file operations.

        Expected inputs (after resolution):
        - operation: "file_write" (default if not provided)
        - path: str (file path to write, or 'file_name' for backward compatibility)
        - content: str (file contents)

        Returns:
            {"outputs": {"success": bool, "path": str, "output_code": str}}
        """
        operation = inputs.get("operation", "file_write")

        # Handle code generation inputs for compatibility
        if operation == "file_write":
            if "file_name" in inputs:
                path_str = inputs.get("file_name")
                content = inputs.get("content")
            elif "destination_folder" in inputs and "file_content" in inputs:
                # Assuming destination_folder + file_content is provided separately,
                # but need a file name. Default to a dummy file name if not provided.
                path_str = os.path.join(inputs.get("destination_folder"), "output.py")
                content = inputs.get("file_content")
            else:
                path_str = inputs.get("path")
                content = inputs.get("content")
        else:
            path_str = inputs.get("path")
            content = inputs.get("content")

        if path_str is None or content is None:
            raise ValueError(f"file_write requires 'path'/'file_name' and 'content' parameters. Got: {list(inputs.keys())}")

        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        return {
            "outputs": {
                "success": True,
                "path": str(path.resolve()),
                "output_code": content,
                "file_a": str(path.resolve()),  # Add missing keys for compatibility
                "file_b": str(path.resolve()),
                "file_c": str(path.resolve())
            }
        }

