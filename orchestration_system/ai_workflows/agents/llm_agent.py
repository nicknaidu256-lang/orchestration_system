"""
LLMAgent — handles text_generation and code_generation capabilities.
Uses Cerebras API. Automatically falls back to Gemini on rate limits (429).

Output contract:
- Always returns {"outputs": {"content": str, "model": str, "tokens_used": int}}
- The executor handles output key aliasing: if a step declares a single output key
  other than "content", the executor maps content → declared_key automatically.
- Do NOT add plan-specific key aliases here. That is a plan concern, not an agent concern.
"""
import os
import json
import urllib.request
import urllib.error
from pathlib import Path


class LLMAgent:
    """Real LLM agent using Cerebras API with Gemini fallback."""

    CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    DEFAULT_MODEL = "llama3.1-8b"
    DEFAULT_MAX_TOKENS = 2048

    def _load_key(self, env_var_name: str) -> str | None:
        key = os.environ.get(env_var_name)
        if key:
            return key
        env_path = Path(__file__).parents[3] / "Resume_Intactor" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith(f"{env_var_name}="):
                    val = line.split("=", 1)[1].strip()
                    print(f"DEBUG: Loaded {env_var_name} from {env_path}")
                    return val
        print(f"DEBUG: Failed to load {env_var_name}")
        return None

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

        # Try Cerebras first
        cerebras_key = self._load_key("CEREBRAS_API_KEY")
        if cerebras_key:
            try:
                result = self._call_cerebras(full_prompt, max_tokens, cerebras_key)
                content = result["content"]
                if fmt in ("python", "javascript", "bash", "json"):
                    content = self._strip_fences(content)
                return {
                    "outputs": {
                        "content": content,
                        "model": result["model"],
                        "tokens_used": result["tokens_used"],
                    }
                }
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    raise RuntimeError(f"Cerebras API error {e.code}: {e.reason}") from e
                # 429 — fall through to Gemini
            except Exception as e:
                raise RuntimeError(f"Cerebras call failed: {e}") from e

        # Gemini fallback (only reached if Cerebras 429 or no Cerebras key)
        gemini_key = self._load_key("GEMINI_API_KEY")
        if not gemini_key:
            raise RuntimeError("Cerebras rate-limited and no GEMINI_API_KEY available")
        try:
            result = self._call_gemini(full_prompt, max_tokens, gemini_key)
            content = result["content"]
            if fmt in ("python", "javascript", "bash", "json"):
                content = self._strip_fences(content)
            return {
                "outputs": {
                    "content": content,
                    "model": result["model"],
                    "tokens_used": result["tokens_used"],
                }
            }
        except Exception as e:
            raise RuntimeError(f"Gemini fallback failed: {e}") from e

    def _strip_fences(self, content: str) -> str:
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0].strip()
        return content

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
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return {
            "content": body["choices"][0]["message"]["content"],
            "model": body.get("model", self.DEFAULT_MODEL),
            "tokens_used": body.get("usage", {}).get("total_tokens", 0),
        }

    def _call_gemini(self, prompt: str, max_tokens: int, api_key: str) -> dict:
        url = f"{self.GEMINI_URL}?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            print(f"Gemini API error body: {error_body}")
            raise RuntimeError(f"Gemini API error: {error_body}") from e

        return {
            "content": body["candidates"][0]["content"]["parts"][0]["text"],
            "model": body.get("modelName", "gemini-1.5-flash"),
            "tokens_used": body.get("usageMetadata", {}).get("totalTokenCount", 0),
        }
