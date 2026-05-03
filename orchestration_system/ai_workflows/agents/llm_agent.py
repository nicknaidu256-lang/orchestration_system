"""
LLMAgent — handles text_generation and code_generation capabilities.
Uses Cerebras API. Falls back to placeholder if API unavailable.
"""
import os
import json
import urllib.request
import urllib.error
from pathlib import Path


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


class LLMAgent:
    """Real LLM agent using Cerebras API."""

    CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
    DEFAULT_MODEL = "llama3.1-8b"
    DEFAULT_MAX_TOKENS = 2048

    def execute(self, inputs: dict) -> dict:
        prompt = inputs.get("prompt") or inputs.get("template") or ""
        context = inputs.get("context", "")
        fmt = inputs.get("format", "plain")
        max_tokens = int(inputs.get("max_tokens", self.DEFAULT_MAX_TOKENS))

        if context:
            full_prompt = f"{context}\n\n{prompt}"
        else:
            full_prompt = prompt

        if fmt in ("python", "javascript", "bash", "json"):
            full_prompt += f"\n\nRespond with only the {fmt} code. No explanation."
        elif fmt == "markdown":
            full_prompt += "\n\nRespond in clean markdown format."

        api_key = _load_api_key()
        if not api_key:
            return {
                "outputs": {
                    "content": f"[LLMAgent fallback — no API key] Prompt was: {prompt[:100]}",
                    "model": "none",
                    "tokens_used": 0,
                }
            }

        try:
            result = self._call_cerebras(full_prompt, max_tokens, api_key)
            return {
                "outputs": {
                    "content": result["content"],
                    "model": result["model"],
                    "tokens_used": result["tokens_used"],
                }
            }
        except Exception as e:
            return {
                "outputs": {
                    "content": f"[LLMAgent error — {e}] Prompt was: {prompt[:100]}",
                    "model": "error",
                    "tokens_used": 0,
                }
            }

    def _call_cerebras(self, prompt: str, max_tokens: int, api_key: str) -> dict:
        payload = {
            "model": self.DEFAULT_MODEL,
            "max_tokens": max_tokens,
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return {
            "content": body["choices"][0]["message"]["content"],
            "model": body.get("model", self.DEFAULT_MODEL),
            "tokens_used": body.get("usage", {}).get("total_tokens", 0),
        }
