import os
import json
from typing import Any, Dict
from ai_workflows.agents import Agent
from docx import Document

class DocxManipulationAgent(Agent):
    """
    Agent for manipulating .docx files.
    Operations: find_replace, add_section, get_metadata.
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        operation = inputs.get("operation")
        path = inputs.get("path")

        if not operation:
            raise ValueError("DocxManipulationAgent requires 'operation' parameter.")
        if not path:
            raise ValueError("DocxManipulationAgent requires 'path' parameter.")
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            doc = Document(path)
            result = ""
            output_path = ""

            if operation == "find_replace":
                find_str = inputs.get("find")
                replace_str = inputs.get("replace")
                if find_str is None or replace_str is None:
                    raise ValueError("Operation 'find_replace' requires 'find' and 'replace' parameters.")
                
                count = 0
                for p in doc.paragraphs:
                    if find_str in p.text:
                        p.text = p.text.replace(find_str, replace_str)
                        count += 1
                
                # Also check tables
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for p in cell.paragraphs:
                                if find_str in p.text:
                                    p.text = p.text.replace(find_str, replace_str)
                                    count += 1
                
                doc.save(path)
                result = f"replaced {count} instances"
                output_path = path

            elif operation == "add_section":
                heading = inputs.get("heading")
                content = inputs.get("content")
                if heading is None or content is None:
                    raise ValueError("Operation 'add_section' requires 'heading' and 'content' parameters.")
                
                doc.add_heading(heading, level=1)
                doc.add_paragraph(content)
                doc.save(path)
                result = "section added"
                output_path = path

            elif operation == "get_metadata":
                props = doc.core_properties
                metadata = {
                    "author": props.author,
                    "created": str(props.created) if props.created else "unknown",
                    "last_modified": str(props.modified) if props.modified else "unknown"
                }
                result = json.dumps(metadata)
                output_path = path

            else:
                raise ValueError(f"Unknown operation: {operation}")

            return {
                "outputs": {
                    "result": result,
                    "output_path": output_path
                }
            }
        except Exception as e:
            raise RuntimeError(f"DocxManipulationAgent failed: {str(e)}")
