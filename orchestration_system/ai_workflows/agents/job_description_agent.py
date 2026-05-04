
from typing import Any, Dict
from ai_workflows.agents import Agent
from ai_workflows.agents.web_fetch_agent import WebFetchAgent
from ai_workflows.agents.local_fs import LocalFSAgent

class JobDescriptionAgent(Agent):
    """
    Orchestrator for loading job descriptions from either local file or URL.
    Capability: "job_description_loader"
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inputs:
        - job_file: str (path) OR
        - job_url: str (url)
        """
        job_file = inputs.get("job_file")
        job_url = inputs.get("job_url")

        if job_file:
            # Load from file
            fs_agent = LocalFSAgent()
            result = fs_agent.execute({"operation": "file_read", "path": job_file})
            return {"outputs": {"job_description": result["outputs"]["content"]}}

        elif job_url:
            # Fetch from URL
            fetch_agent = WebFetchAgent()
            result = fetch_agent.execute({"url": job_url})
            return {"outputs": {"job_description": result["outputs"]["content"]}}

        else:
            raise ValueError("JobDescriptionAgent requires either 'job_file' or 'job_url'.")
