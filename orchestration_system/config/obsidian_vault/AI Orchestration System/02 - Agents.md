# Agents

| Agent | Capability | Status |
|---|---|---|
| LocalFSAgent | file_write | ? Real |
| TerminalAgent | shell_command, git_*, github_* | ? Real |
| WebSearchAgent | web_search | ? Real (DuckDuckGo) |
| DocxAgent | docx_write | ? Real (python-docx) |
| TerminalAgent | text_generation | ?? Static (not live LLM) |
| TerminalAgent | code_generation, ats_analysis | ?? Stub |

## Adding a New Agent
1. Create i_workflows/agents/my_agent.py with class MyAgent(Agent)
2. Implement execute(self, inputs: dict) -> dict returning {"outputs": {...}}
3. Add to i_workflows/agents/loader.py
4. Map capability in i_workflows/registry/registry.json
"@

Set-Content -Path (Join-Path C:\Users\abhil\Project_A\orchestration_system\config\obsidian_vault\AI Orchestration System "03 - Plans.md") -Value @"
# Plans

Plans live in: orchestration_system/plans/

## Current Plans
- hello_world.json — writes a hello.py file
- generate_and_write.json — generates text and writes to disk
- esume_tailoring_v1.json — resume tailoring workflow (DOCX stub)
- github_graphify_onboarding_v1.json — GitHub + Graphify setup
- parallel_test.json — demonstrates parallel step execution

## Plan Schema (key fields)
`json
{
  "workflow_id": "my_plan",
  "plan_hash": "<sha256 of steps>",
  "steps": [
    {
      "id": "step_1",
      "capability": "file_write",
      "inputs": {"path": "output/file.txt", "content": ""},
      "outputs": ["my_output_key"],
      "idempotent": true,
      "retryable": false,
      "requires_approval": false,
      "parallel_group": "optional"
    }
  ]
}
`

## Generating a New Plan
python -m ai_workflows.cli generate "describe your goal" --workflow-id my_plan
"@

Set-Content -Path (Join-Path C:\Users\abhil\Project_A\orchestration_system\config\obsidian_vault\AI Orchestration System "04 - Running the System.md") -Value @"
# Running the System

## Always set PYTHONPATH first
$env:PYTHONPATH="C:\Users\abhil\Project_A\orchestration_system"

## Commands
# List all plans and capabilities
python -m ai_workflows.cli list

# Generate a new plan from plain English
python -m ai_workflows.cli generate "my goal" --workflow-id plan_name

# Run a plan
python -m ai_workflows.cli run plans/plan_name.json

# Run acceptance tests
python ai_workflows/tests/test_acceptance.py

## API Key
Cerebras API key is auto-loaded from:
C:\Users\abhil\Project_A\Resume_Intactor\.env

## Manual Bridge Fallback
If Cerebras is unavailable, generate command will:
1. Write prompt to 	emp/pending_prompt.txt
2. Pause and wait for you to paste JSON into 	emp/response.json
3. Automatically validate and save the plan
