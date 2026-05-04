# AI Workflow Orchestration System

This system provides a deterministic framework for executing complex, multi-agent AI workflows. It separates orchestration logic from execution; Hermes plans the workflow steps once, and the executor runs them deterministically in a secure sandbox, ensuring consistency and reliability without LLM intervention during the execution phase.

## Quick Start

Prerequisites: Python 3.10+, pip install -r requirements.txt, copy .env.example to ..\Resume_Intactor\.env and add API keys.

Run the validation pipeline to confirm everything works:
  python -m ai_workflows.cli run plans/pipeline_validation.json

## Resume Tailoring Pipeline

How to use it with a local file:
  python -m ai_workflows.cli run plans/resume_tailoring_v2.json --input job_file=jobs/your_job.txt --input resume_file=resumes/your_resume.docx

How to use it with a job posting URL:
  python -m ai_workflows.cli run plans/resume_tailoring_v2.json --input job_url=https://example.com/jobs/role --input resume_file=resumes/your_resume.docx

Outputs: output/Tailored_Resume.docx, output/ATS_Report.txt

## How to Add a New Capability

4 steps:
1. Create ai_workflows/agents/your_agent.py implementing Agent.execute()
2. Register it in ai_workflows/registry/registry.json: "your_capability": "your_agent"
3. Add the import in ai_workflows/agents/loader.py
4. Reference "capability": "your_capability" in any plan step

## Environment Variables

| Variable | Purpose | Required |
| :--- | :--- | :--- |
| CEREBRAS_API_KEY | Primary LLM provider | Yes |
| GEMINI_API_KEY | Fallback LLM (auto on 429) | Recommended |
| CEREBRAS_MODEL | Model name override | No (default: llama3.1-8b) |
| GEMINI_MODEL | Model name override | No (default: gemini-2.5-flash) |

File location: C:\Users\abhil\Project_A\Resume_Intactor\.env

## Running Tests
  python ai_workflows/tests/test_acceptance.py

## Resuming a Crashed Run
  python -m ai_workflows.cli run plans/resume_tailoring_v2.json --resume <run-id>
  Run IDs are in ~/.ai-workflows/runs/
