# AI Workflow Orchestration System

A personal AI operations platform. Describe a goal in plain English ? Hermes plans it ? 
the executor runs it deterministically.

**Location:** C:\Users\abhil\Project_A\orchestration_system\
**Full reference:** See PROJECT_BIBLE.md in the orchestration_system root

## Status
- Core: Complete ?
- All acceptance tests passing ?
- Live LLM plan generation via Cerebras ?
- Parallel execution ?

## Quick Start
cd C:\Users\abhil\Project_A\orchestration_system
$env:PYTHONPATH="C:\Users\abhil\Project_A\orchestration_system"
python -m ai_workflows.cli list
python -m ai_workflows.cli generate "your goal here"
python -m ai_workflows.cli run plans/my_plan.json
"@

Set-Content -Path (Join-Path C:\Users\abhil\Project_A\orchestration_system\config\obsidian_vault\AI Orchestration System "01 - Architecture.md") -Value @"
# Architecture

## Flow
You ? Hermes (plans) ? CLI ? Validator ? Executor ? Agent Registry ? State Manager

## Key Principle
Hermes thinks ONCE before anything runs. Execution is deterministic — no LLM during execution.

## Parallel Execution
Steps sharing a parallel_group value run simultaneously via ThreadPoolExecutor.
Steps without a group run sequentially.

## State
- Atomic writes — crash-safe
- Snapshots per step — full audit trail
- Idempotency — completed steps skipped on re-run
