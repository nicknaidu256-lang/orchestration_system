# AI Workflows System — v1

Structured, deterministic workflow execution with explicit plan → state → executor separation.

## Architecture

```
ai_workflows/
  planner/        # Hermes → produces JSON plan only
  executor/       # deterministic runner (no LLM calls)
  state/          # per-run isolated state manager
  registry/       # capability → agent mapping
  agents/         # OpenCode, KiloCode, local_fs wrappers
  schemas/        # JSON schemas for validation
```

## Core Principle

**The Plan is data. Everything else is a function over that data.**

- Planner (Hermes) produces a structured JSON plan once, upfront
- Executor reads it mechanically — NO LLM calls, NO reasoning, NO branching
- Plan hash: `sha256(json.dumps(steps, sort_keys=True))`
- Errors classified as Planning vs Execution failures explicitly

## State Guarantees

- Per-run isolation: `~/.ai-workflows/runs/{run_id}/`
- Atomic writes: `.tmp` → `rename()`
- Append-only: duplicate key writes raise `StateConflictError`
- Status + outputs committed together
- Snapshots are forensic logs only (best-effort, after commit)

## Error Taxonomy

| Error | Cause | Action |
|-------|-------|--------|
| `CorruptStateError` | Status says completed but outputs missing | Halt — operator inspect |
| `StepFailure` | Agent returned missing declared output | Retry if `retryable: true`, else halt |
| `MissingStateError` | `$ref` key not found in state during resolution | Halt — bad plan or upstream failure |
| `UnknownCapabilityError` | Capability not in registry | Halt — config error |
| `StateConflictError` | Step tried to overwrite existing state key | Halt — planning error |
| `ApprovalDeniedError` | User rejected at approval gate | Halt — user decision |

## Execution Order

1. **state/** — StateManager with atomic writes, append-only checks
2. **schemas/** — JSON schemas for plan and state validation
3. **errors.py** — All exception classes
4. **resolve_inputs** — $ref resolution with MissingStateError on failure
5. **executor/** — Deterministic for-loop with idempotency checks
6. **registry/** — Flat JSON mapping, no scoring
7. **agents/** — Uniform `Agent.execute(inputs) -> dict` interface
8. **planner/** — Hermes prompt templates + plan validator

## First Build Target

Workflow: `generate_text → write_file`

Tests:
1. Idempotency on resume (kill mid-step-2, rerun)
2. Missing $ref raises before agent call
3. Missing output key raises after agent returns, before state write
