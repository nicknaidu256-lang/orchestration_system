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
    Capability: "file_write", "file_read"

    Optional input: output_key (str)
        When provided, the agent adds {output_key: True} to the outputs dict
        (for file_write only).
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute file operations.

        Inputs:
        - operation: "file_write" (default) or "file_read"
        - path: str (file path)
        - content: str (required for file_write)
        - output_key: str (optional, for file_write)
        """
        operation = inputs.get("operation", "file_write")

        if operation == "file_read":
            path_str = inputs.get("path")
            if not path_str:
                raise ValueError("file_read requires 'path' parameter.")
            path = Path(path_str)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path_str}")
            return {"outputs": {"content": path.read_text(encoding="utf-8"), "file_path": str(path.resolve())}}

        # Handle file_write operations
        if "file_name" in inputs:
            path_str = inputs.get("file_name")
            content = inputs.get("content")
        elif "destination_folder" in inputs and "file_content" in inputs:
            path_str = os.path.join(inputs.get("destination_folder"), "output.py")
            content = inputs.get("file_content")
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

        output_key = inputs.get("output_key")
        if output_key:
            outputs[output_key] = True

        return {"outputs": outputs}
