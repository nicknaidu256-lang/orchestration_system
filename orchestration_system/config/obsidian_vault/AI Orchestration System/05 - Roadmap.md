# Roadmap

## Completed
- [x] Deterministic executor with sequential + parallel execution
- [x] State manager with atomic writes, snapshots, idempotency
- [x] Real agents: file writes, shell commands, web search, DOCX
- [x] Natural language plan generation via Cerebras live backend
- [x] Manual bridge fallback for plan generation
- [x] 22 capabilities registered, 5 plans tested
- [x] All acceptance tests passing

## Planned (Priority Order)
- [ ] Resume tailoring E2E with real DOCX output (1–2 hrs)
- [ ] Live LLM at agent level — wire Cerebras into text_generation (2–3 hrs)
- [ ] Dynamic replanning on failure (3–4 hrs)
- [ ] Agent memory across runs (2–3 hrs)
- [ ] Visual monitoring dashboard (4–6 hrs)

## Known Limitations
- 	ext_generation, code_generation, ts_analysis agents are stubs
- No UI for monitoring running workflows
- No agent-to-agent communication
