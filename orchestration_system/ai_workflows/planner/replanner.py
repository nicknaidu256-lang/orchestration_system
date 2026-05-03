"""
Replanner — called by the executor when a step fails after all retries.
Sends failed step context + current state + remaining steps to Cerebras.
Returns a revised list of steps to execute.
"""
import os
import json
import urllib.request
from pathlib import Path

from ai_workflows.planner.core import validate_plan, compute_plan_hash


def _load_api_key() -> str | None:
    key = os.environ.get("CEREBRAS_API_KEY")
    if key:
        return key
    env_path = Path(__file__).parents[3] / "Resume_Intactor" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("CEREBRAS_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


REPLAN_PROMPT_TEMPLATE = """
You are an AI workflow orchestration replanner.

A workflow step has failed. You must produce a revised plan for the REMAINING
steps only. Do not include completed steps. Do not re-run the failed step
unless there is a fundamentally different approach.

FAILED STEP:
{failed_step}

CURRENT STATE (available $key values):
{current_state}

REMAINING STEPS (what was originally planned next):
{remaining_steps}

AVAILABLE CAPABILITIES:
{capabilities}

Rules:
- Output pure JSON only — a list of step objects, no wrapper object
- Each step must have: id, capability, inputs, outputs (list), idempotent, retryable, requires_approval
- Input state references use "$key" notation (e.g. "content": "$generated_text")
- Do not include plan_hash — the system computes it
- If no recovery is possible, return an empty list []

Respond with the revised steps JSON only. No explanation.
""".strip()


class Replanner:
    CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
    MODEL = "llama3.1-8b"

    def replan(
        self,
        failed_step: dict,
        current_state: dict,
        remaining_steps: list[dict],
        registry: dict,
    ) -> list[dict] | None:
        """
        Returns revised list of steps, or None if replanning is not possible.
        """
        api_key = _load_api_key()
        if not api_key:
            print("[Replanner] No API key — cannot replan. Halting.")
            return None

        capabilities = list(registry.keys())
        prompt = REPLAN_PROMPT_TEMPLATE.format(
            failed_step=json.dumps(failed_step, indent=2),
            current_state=json.dumps(
                {k: str(v)[:200] for k, v in current_state.items()}, indent=2
            ),
            remaining_steps=json.dumps(remaining_steps, indent=2),
            capabilities=json.dumps(capabilities),
        )

        print("[Replanner] Step failed. Requesting Cerebras replan...")
        raw = self._call_cerebras(prompt, api_key)
        if not raw:
            return None

        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            revised_steps = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"[Replanner] Failed to parse Cerebras response: {e}")
            return None

        if not isinstance(revised_steps, list):
            print("[Replanner] Response was not a list of steps.")
            return None

        if len(revised_steps) == 0:
            print("[Replanner] Cerebras determined no recovery is possible.")
            return []

        # Validate the revised steps
        dummy_plan = {
            "workflow_id": "replan",
            "version": "1.0",
            "created_by": "replanner",
            "plan_hash": compute_plan_hash(revised_steps),
            "steps": revised_steps,
        }
        errors = validate_plan(dummy_plan)
        if errors:
            print(f"[Replanner] Revised steps failed validation: {errors}")
            return None

        print(f"[Replanner] Revised plan accepted — {len(revised_steps)} steps.")
        return revised_steps

    def _call_cerebras(self, prompt: str, api_key: str) -> str | None:
        payload = {
            "model": self.MODEL,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.CEREBRAS_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Mozilla/5.0"
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[Replanner] Cerebras call failed: {e}")
            return None
