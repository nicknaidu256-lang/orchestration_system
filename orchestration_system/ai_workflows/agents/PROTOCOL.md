# Agent Communication Protocol — v1

## Contract

All agents must implement the same input/output contract. The executor enforces this.

### Request (from executor → agent)

```json
{
  "inputs": {
    "arg1": "value",
    "arg2": 123,
    "$ref_key": "resolved_value"
  }
}
```

**Rules:**
- Top-level key: `inputs` (dict)
- All `$ref` values have already been resolved by the executor
- No other top-level keys (no `task`, no `prompt`, no `context`)
- The agent receives exactly what the step's `inputs` dict contains after resolution

### Response (from agent → executor)

```json
{
  "outputs": {
    "output_key_1": "value1",
    "output_key_2": "value2"
  }
}
```

**Rules:**
- Top-level key: `outputs` (dict)
- Keys MUST match exactly the step's `outputs` list
- Values can be any JSON-serializable type (str, int, float, bool, list, dict, null)
- If an output is missing, the executor raises `StepFailure`

### Error Handling

If an agent encounters an exception, it should raise the exception — do NOT catch and return error objects. The executor's error handler will catch and classify.

**Do NOT wrap errors in JSON.** Let exceptions propagate.

### Example

Step definition:
```json
{
  "id": "generate",
  "capability": "text_generation",
  "inputs": {"prompt": "Write a haiku"},
  "outputs": ["poem"]
}
```

Executor calls:
```python
result = agent.execute({"prompt": "Write a haiku"})
# Expected: {"outputs": {"poem": "Rustling leaves / Fall softly on mossy stones / Quiet morning light"}}
```

Executor extracts: `result["outputs"]` → must contain key `"poem"`.

---

## Agent Implementation Template

```python
class MyAgent(Agent):
    def execute(self, inputs: dict) -> dict:
        # inputs is already resolved (no $refs)
        # Do work
        outputs = {
            "output_key_1": computed_value,
            "output_key_2": other_value
        }
        return {"outputs": outputs}
```

---

## Validation in Executor

Executor does:
```python
result = agent.execute(inputs)
if "outputs" not in result:
    raise StepFailure(..., message="Agent response missing top-level 'outputs' key")
for key in step["outputs"]:
    if key not in result["outputs"]:
        raise StepFailure(..., missing_output=key)
```
