import json
import time
import os
import hashlib
from pathlib import Path
from .core import validate_plan, compute_plan_hash
from cerebras.cloud.sdk import Cerebras

class PlanGenerator:
    def __init__(self, registry_path=Path("./ai_workflows/registry/registry.json")):
        self.registry_path = registry_path
        self.template_path = Path(__file__).parent / "hermes_prompt_template.md"
        self.temp_dir = Path("./temp")
        self.prompt_file = self.temp_dir / "pending_prompt.txt"
        self.response_file = self.temp_dir / "response.json"

    def _load_registry(self):
        with open(self.registry_path, 'r') as f:
            return json.load(f)

    def _load_template(self):
        return self.template_path.read_text()

    def _call_llm(self, prompt):
        api_key = os.environ.get("CEREBRAS_API_KEY")
        if not api_key:
            env_path = Path("C:/Users/abhil/Project_A/Resume_Intactor/.env")
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if line.startswith("CEREBRAS_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break

        if not api_key:
            raise Exception("No API Key found")

        client = Cerebras(api_key=api_key)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3.1-8b",
        )
        return response.choices[0].message.content

    def _run_manual_bridge(self, prompt):
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_file.write_text(prompt)

        print("""
   ============================================================
   MANUAL PLAN GENERATION REQUIRED
   ============================================================
   1. Open the file: orchestration_system\\temp\\pending_prompt.txt
   2. Copy the full contents
   3. Paste into any AI agent (Hermes, Claude, etc.)
   4. Copy the JSON response from the agent
   5. Paste it into: orchestration_system\\temp\\response.json
   6. Save the file
   The generator will continue automatically once response.json appears.
   ============================================================
        """)

        # Poll for response.json
        timeout = 600 # 10 minutes
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.response_file.exists():
                break
            time.sleep(3)
        else:
            raise Exception("Timeout waiting for manual response.json")

        response = self.response_file.read_text()
        self.response_file.unlink()
        return response

    def generate(self, goal, workflow_id, output_dir=Path("./plans")):
        registry = self._load_registry()
        template = self._load_template()

        prompt = template.format(
            capabilities_list=json.dumps(registry.get("mapping", {}), indent=2),
            user_goal=goal
        )

        try:
            print("[INFO] Using Cerebras live backend")
            response = self._call_llm(prompt)
        except Exception as e:
            print(f"[INFO] API call failed: {e}. Falling back to manual bridge")
            response = self._run_manual_bridge(prompt)

        # Strip markdown fences
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
            response = response.strip()

        try:
            plan = json.loads(response)
        except json.JSONDecodeError:
            raise Exception("Invalid JSON in response")

        plan["workflow_id"] = workflow_id
        plan["version"] = "1.0"
        plan["created_by"] = "hermes"

        # Compute plan_hash
        plan["plan_hash"] = compute_plan_hash(plan["steps"])

        try:
            validate_plan(plan)
            output_dir.mkdir(parents=True, exist_ok=True)
            plan_path = output_dir / f"{workflow_id}.json"
            plan_path.write_text(json.dumps(plan, indent=2))

            return plan
        except ValueError as e:
            raise Exception(f"Validation failed: {e}")
