# AI Workflow Orchestration System

This system provides a structured, deterministic framework for executing complex, multi-agent AI workflows. It features state management, dynamic replanning, and robust LLM provider abstraction to ensure reliable execution of tasks like resume tailoring and ATS analysis.

## Quick Start

1.  **Installation**: Ensure Python 3.14+ is installed. Install dependencies:
    ```bash
    pip install -r config/requirements/base.txt
    ```
2.  **Environment Setup**: Create `Resume_Intactor/.env` with your API keys:
    ```
    CEREBRAS_API_KEY=<your-key>
    GEMINI_API_KEY=<your-key>
    ```
3.  **Validation**: Verify the setup by running the pipeline validation plan:
    ```bash
    python -m ai_workflows.cli run plans/pipeline_validation.json
    ```

## Running the Resume Tailoring Pipeline

The system can tailor resumes based on a job description (file or URL) and an existing resume (.docx).

```bash
python -m ai_workflows.cli run plans/resume_tailoring_v2.json \
  --input job_url=https://example.com/job-posting \
  --input resume_file=resumes/my_resume.docx
```

## Adding a New Capability

1.  **Define Agent**: Implement the agent class in `ai_workflows/agents/` inheriting from `ai_workflows.agents.Agent`.
2.  **Register Agent**: Add the agent to `ai_workflows/agents/loader.py` in the `_AGENT_REGISTRY`.
3.  **Map Capability**: Update `ai_workflows/registry/registry.json` to map your new capability name to the agent ID defined in the loader.

## Environment Variables

| Variable | Description |
| :--- | :--- |
| `CEREBRAS_API_KEY` | Primary API key for LLM tasks |
| `GEMINI_API_KEY` | Fallback API key for LLM tasks |
| `LOG_LEVEL` | Logging level (default: INFO) |
