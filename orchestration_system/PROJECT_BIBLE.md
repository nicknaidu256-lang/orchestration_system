# Project Bible — AI Workflow Orchestration System
**Location:** `C:\Users\abhil\Project_A\orchestration_system\`
**Last Updated:** 2026-05-03
**Status:** Production-ready core. Feature additions in progress.

---

## 1. What This System Is

A personal AI operations platform. You describe a goal in plain English to Hermes. Hermes produces a deterministic execution plan. The orchestration engine runs that plan step-by-step, assigning real tools to each step, managing state, and handing you a result.

**The key difference from other AI agent tools:**
- Hermes thinks *once* — before anything runs
- Execution is fully deterministic — no LLM involved during execution
- Every step is traceable — state snapshots mean you know exactly what happened and why
- Failures are explicit — nothing fails silently or self-heals without your knowledge
- Approval gates protect destructive actions

---

## 2. Architecture Overview

```
You
 │
 ▼
Hermes (AI Planner — Cerebras/manual)
 │  Produces: plan JSON
 ▼
CLI  ──►  Validator ──►  Plan Hash Check
                              │
                              ▼
                         Executor (deterministic loop)
                          │         │
                    Sequential   Parallel Group
                    Steps        (ThreadPoolExecutor)
                          │
                          ▼
                    Agent Registry
                    ├── LocalFSAgent      (file_write)
                    ├── TerminalAgent     (shell_command, git_*, package_*)
                    ├── WebSearchAgent    (web_search)
                    ├── DocxAgent         (docx_write)
                    └── [future agents]
                          │
                          ▼
                    State Manager
                    ├── Atomic writes
                    ├── Step snapshots
                    └── Corruption detection
```

---

## 3. Directory Structure

```
orchestration_system/
├── ai_workflows/
│   ├── agents/
│   │   ├── loader.py              # Loads agents by name
│   │   ├── local_fs_agent.py      # Real file writes
│   │   ├── terminal_agent.py      # Real shell commands
│   │   ├── web_search_agent.py    # Real DuckDuckGo search
│   │   └── docx_agent.py          # Real DOCX creation (python-docx)
│   ├── executor/
│   │   └── __init__.py            # Sequential + parallel execution engine
│   ├── planner/
│   │   ├── core.py                # validate_plan(), compute_plan_hash()
│   │   ├── generator.py           # NL → JSON plan generator (Cerebras live + manual fallback)
│   │   └── hermes_prompt_template.md
│   ├── registry/
│   │   └── registry.json          # Capability → agent mapping (22 capabilities)
│   ├── state/
│   │   └── __init__.py            # StateManager — atomic writes, snapshots
│   ├── tests/
│   │   └── test_acceptance.py     # Idempotency, missing refs, missing outputs
│   ├── cli.py                     # Entry point: list, run, generate subcommands
│   ├── errors.py
│   └── resolve_inputs.py          # $key state reference resolution
├── plans/
│   ├── generate_and_write.json
│   ├── github_graphify_onboarding_v1.json
│   ├── hello_world.json
│   ├── parallel_test.json
│   └── resume_tailoring_v1.json
├── projects/                      # Generated project outputs
├── config/                        # Shared graphs, Obsidian vault config
├── temp/                          # Manual bridge: pending_prompt.txt, response.json
└── PROJECT_BIBLE.md               # This file
```

---

## 4. Key Design Decisions (and Why)

| Decision | Reason |
|---|---|
| Hermes plans, executor runs — no overlap | Keeps execution predictable; LLM reasoning errors don't cascade into broken state |
| Plan hash validation before every run | Detects tampered or corrupted plans before a single step executes |
| Atomic state writes | A crash mid-step leaves state consistent, not half-written |
| Step snapshots on every step | Full audit trail; re-run from any point |
| $key notation for state refs | Simple, readable, unambiguous — resolver catches missing keys before agent call |
| Manual bridge as LLM fallback | Zero-cost backup when API quotas are exhausted |
| ThreadPoolExecutor for parallel groups | Stdlib only, no additional dependencies; lock protects state writes |

---

## 5. How to Run

### Prerequisites
```powershell
cd C:\Users\abhil\Project_A\orchestration_system
$env:PYTHONPATH="C:\Users\abhil\Project_A\orchestration_system"
```

### List available plans and capabilities
```powershell
python -m ai_workflows.cli list
```

### Generate a new plan from natural language
```powershell
python -m ai_workflows.cli generate "your goal here" --workflow-id my_plan
```
- Uses Cerebras live backend automatically (key loaded from `Resume_Intactor\.env`)
- Falls back to manual bridge if API unavailable
- Saves to `plans/my_plan.json`

### Run an existing plan
```powershell
python -m ai_workflows.cli run plans/my_plan.json
```

### Run acceptance tests
```powershell
python ai_workflows/tests/test_acceptance.py
```

---

## 6. Capability → Agent Registry

| Capability | Agent | Real or Stub |
|---|---|---|
| file_write | LocalFSAgent | ✅ Real |
| shell_command | TerminalAgent | ✅ Real |
| web_search | WebSearchAgent | ✅ Real (DuckDuckGo) |
| docx_write | DocxAgent | ✅ Real (python-docx) |
| text_generation | TerminalAgent | ⚠️ Static content (Cerebras not wired at agent level yet) |
| code_generation | TerminalAgent | ⚠️ Stub |
| git_* (clone, add, commit, push) | TerminalAgent | ✅ Real (shell passthrough) |
| github_* | TerminalAgent | ✅ Real (shell passthrough via gh CLI) |
| graphify_* | TerminalAgent | ✅ Real (shell passthrough) |
| ats_analysis | TerminalAgent | ⚠️ Stub |
| docx_manipulation | TerminalAgent | ⚠️ Stub |
| browser_automation | TerminalAgent | ⚠️ Stub |

---

## 7. Plan Schema Reference

```json
{
  "workflow_id": "my_workflow",
  "version": "1.0",
  "created_by": "hermes",
  "plan_hash": "<sha256 of steps array>",
  "steps": [
    {
      "id": "step_1",
      "capability": "file_write",
      "inputs": {
        "path": "output/hello.py",
        "content": "$generated_code"
      },
      "outputs": ["written_file"],
      "idempotent": true,
      "retryable": false,
      "requires_approval": false,
      "parallel_group": "optional_group_name"
    }
  ]
}
```

**State reference rules:**
- Use `"$key"` to reference a previous step's output in inputs
- Steps in the same `parallel_group` CANNOT reference each other's outputs
- `requires_approval: true` steps CANNOT be in a parallel group

---

## 8. Current System Status

### ✅ Complete and verified
- Deterministic executor with sequential and parallel execution
- State management with atomic writes, snapshots, corruption detection
- Idempotency — completed steps are skipped on re-run
- Retry logic per step
- Approval gates
- Plan hash validation
- Natural language → plan via Cerebras (live) with manual bridge fallback
- 22 capabilities registered
- 5 workflow plans created and tested
- Acceptance tests passing
- Real agents: LocalFSAgent, TerminalAgent, WebSearchAgent, DocxAgent
- Code clean — no duplicate imports, no known technical debt

### ⚠️ Known limitations (planned feature additions)
- `text_generation` at agent level is static — not wired to live LLM
- `code_generation`, `ats_analysis`, `docx_manipulation`, `browser_automation` are stubs
- No visual dashboard for monitoring running workflows
- No agent memory across workflow runs
- No dynamic replanning on step failure (system halts cleanly instead)
- Resume tailoring workflow runs end-to-end but DOCX output is stub

---

## 9. Planned Feature Additions (Priority Order)

| # | Feature | Description | Effort |
|---|---|---|---|
| 1 | Resume tailoring E2E | Wire DocxAgent fully into resume_tailoring_v1 plan | 1–2 hrs |
| 2 | Live LLM at agent level | Wire Cerebras into text_generation and code_generation agents | 2–3 hrs |
| 3 | Dynamic replanning | On step failure, Hermes re-plans the remaining steps | 3–4 hrs |
| 4 | Agent memory | Agents retain context from previous runs via shared state | 2–3 hrs |
| 5 | Visual dashboard | Real-time workflow monitoring UI | 4–6 hrs |

---

## 10. Agents and Their Roles

| Agent | File | Real Tool Used |
|---|---|---|
| Hermes | External (your AI agent) | Plans only — never executes |
| OpenCode | External CLI | Code generation (not yet wired as agent) |
| KiloCode | External CLI (interactive only) | Cannot be used headlessly |
| LocalFSAgent | `agents/local_fs_agent.py` | Python `open()` |
| TerminalAgent | `agents/terminal_agent.py` | `subprocess.run()` |
| WebSearchAgent | `agents/web_search_agent.py` | `urllib` → DuckDuckGo |
| DocxAgent | `agents/docx_agent.py` | `python-docx` |

---

## 11. Environment Setup

**Required environment variable (auto-loaded from Resume_Intactor\.env):**
```
CEREBRAS_API_KEY=<your key>
```

**Optional overrides:**
```
AI_WORKFLOWS_PLANS_DIR=<custom plans path>
```

**PYTHONPATH must always be set:**
```powershell
$env:PYTHONPATH="C:\Users\abhil\Project_A\orchestration_system"
```

---

## 12. Related Projects

| Project | Location | Relationship |
|---|---|---|
| Resume_Intactor | `Project_A/Resume_Intactor/` | Standalone product; first real use case for orchestration |
| JobGetter | `Project_A/JobGetter/` | Future orchestration target |
| mobileapp | `Project_A/mobileapp/` | Future orchestration target |

---

## 13. For New Sessions — Onboarding Prompt

Paste this at the start of any new Claude or Hermes session to restore full context:

```
We are continuing work on the AI workflow orchestration system located at:
C:\Users\abhil\Project_A\orchestration_system\

The system is a deterministic AI operations platform. Hermes plans, the executor runs.
Read PROJECT_BIBLE.md at the root of orchestration_system for full context.

Current status: core is complete and tested. All acceptance tests pass.
PYTHONPATH: C:\Users\abhil\Project_A\orchestration_system

Pending work: [describe what you want to do next]
```
