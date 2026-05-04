
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
        path = inputs.get("path", "output/document.docx")
        os.makedirs(os.path.dirname(path), exist_ok=True)

        doc = Document()

        # Handle structured content if it's passed as a list of dicts/sections
        # otherwise default to single paragraph
        content = inputs.get("content", "")
        if isinstance(content, str):
            # Split by double newline for paragraph breaks
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.startswith("# "):
                    doc.add_heading(para[2:], level=1)
                elif para.startswith("## "):
                    doc.add_heading(para[3:], level=2)
                else:
                    doc.add_paragraph(para)
        else:
            # Fallback for simple content
            doc.add_paragraph(str(content))

        doc.save(path)

        outputs = {
            "file_path": path,
            "success": True,
            "size_bytes": os.path.getsize(path)
        }

        output_key = inputs.get("output_key")
        if output_key:
            outputs[output_key] = True

        return {"outputs": outputs}
