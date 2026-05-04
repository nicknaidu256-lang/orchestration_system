"""
Agent loader — dynamic agent instantiation based on agent identifier.
Central point for creating agent instances from registry mappings.
"""

from typing import Any, Dict

from ai_workflows.agents import Agent
from ai_workflows.agents.local_fs import LocalFSAgent
from ai_workflows.agents.opencode import OpenCodeAgent
from ai_workflows.agents.kilocode import KiloCodeAgent
from ai_workflows.agents.terminal import TerminalAgent
from ai_workflows.agents.web_search_agent import WebSearchAgent
from ai_workflows.agents.docx_agent import DocxAgent
from ai_workflows.agents.llm_agent import LLMAgent
from ai_workflows.agents.ats_agent import ATSAgent
from ai_workflows.agents.web_fetch_agent import WebFetchAgent
from ai_workflows.agents.job_description_agent import JobDescriptionAgent
from ai_workflows.agents.browser_agent import BrowserAgent
from ai_workflows.agents.docx_manipulation_agent import DocxManipulationAgent
from ai_workflows.agents.gemini_cli_agent import GeminiCLIAgent
from ai_workflows.agents.verification_agent import VerificationAgent
from ai_workflows.agents.claude_code_agent import ClaudeCodeAgent

# Registry: agent_id -> Agent class
_AGENT_REGISTRY = {
    "local_fs": LocalFSAgent,
    "opencode": OpenCodeAgent,
    "kilocode": KiloCodeAgent,
    "terminal": TerminalAgent,
    "web_search_agent": WebSearchAgent,
    "docx_agent": DocxAgent,
    "llm_agent": LLMAgent,
    "ats_agent": ATSAgent,
    "web_fetch_agent": WebFetchAgent,
    "job_description_agent": JobDescriptionAgent,
    "browser_agent": BrowserAgent,
    "docx_manipulation_agent": DocxManipulationAgent,
    "gemini_cli_agent": GeminiCLIAgent,
    "verification_agent": VerificationAgent,
    "claude_code_agent": ClaudeCodeAgent,
}


def load_agent(agent_id: str, **kwargs) -> Agent:
    """
    Instantiate an agent by its identifier.

    Args:
        agent_id: String key from the capability registry (e.g. "opencode")
        **kwargs: Additional arguments passed to the agent constructor

    Returns:
        Agent instance

    Raises:
        ValueError: If agent_id is not recognized
    """
    if agent_id not in _AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent ID: '{agent_id}'. "
            f"Known agents: {list(_AGENT_REGISTRY.keys())}"
        )
    agent_class = _AGENT_REGISTRY[agent_id]
    return agent_class(**kwargs)

