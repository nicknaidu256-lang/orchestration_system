"""
ATSAgent — analyzes resume against job description.
Uses LLM to provide structured feedback (score, keywords, suggestions).
"""

from typing import Any, Dict
from ai_workflows.agents import Agent
from ai_workflows.agents.llm_agent import LLMAgent

class ATSAgent(Agent):
    """Real ATS analysis agent using LLM."""

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inputs:
        - resume_text: str
        - job_description: str

        Returns:
        - ats_score: int
        - matched_keywords: list
        - missing_keywords: list
        - recommendations: str
        - required_missing: list
        - preferred_missing: list
        """
        resume = inputs.get("resume_text", "")
        job = inputs.get("job_description", "")

        prompt = f"""You are an ATS expert. Analyze this resume against the job description.
Resume: {resume}
Job Description: {job}

Return ONLY valid JSON with this structure:
{{
  "ats_score": 85,
  "matched_keywords": ["python", "api design"],
  "missing_keywords": ["kubernetes"],
  "required_missing": ["kubernetes"],
  "preferred_missing": ["docker"],
  "recommendations": "Improve summary."
}}

Only flag technical skills, tools, frameworks, libraries, and domain-specific terms.
Categorize missing keywords into 'required_missing' and 'preferred_missing' based on the job description.
Do not flag generic English verbs or nouns (e.g. "build", "design", "system") — these are not ATS keywords."""

        # Reuse LLMAgent logic
        llm = LLMAgent()
        result = llm.execute({"prompt": prompt, "format": "json"})

        import json
        content = result["outputs"]["content"]
        # Basic parsing check
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Fallback if LLM failed JSON
            data = {
                "ats_score": 0,
                "matched_keywords": [],
                "missing_keywords": [],
                "required_missing": [],
                "preferred_missing": [],
                "recommendations": "Error parsing LLM output: " + content
            }

        return {"outputs": data}
