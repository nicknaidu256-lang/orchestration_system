
from docx import Document
import os
from typing import Any, Dict
from ai_workflows.agents import Agent

class DocxAgent(Agent):
    """
    Agent for DOCX operations.
    Capability: "docx_write", "docx_read"
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        operation = inputs.get("operation", "docx_write")

        if operation == "docx_read":
            path = inputs.get("path")
            if not path or not os.path.exists(path):
                raise ValueError(f"docx_read requires valid 'path', got: {path}")

            doc = Document(path)
            text = "\n".join([p.text for p in doc.paragraphs])
            return {
                "outputs": {
                    "content": text,
                    "file_path": str(os.path.abspath(path))
                }
            }

        # Write operation
        content = inputs.get("content", "")
        path = inputs.get("path", "output/document.docx")

        doc = Document()
        doc.add_paragraph(content)

        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc.save(path)

        return {
            "outputs": {
                "file_path": path,
                "success": True,
                "size_bytes": os.path.getsize(path)
            }
        }
