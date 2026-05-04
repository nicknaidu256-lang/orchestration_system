
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_workflows.agents.web_fetch_agent import WebFetchAgent
from ai_workflows.agents.job_description_agent import JobDescriptionAgent

print("--- Testing WebFetchAgent ---")
fetcher = WebFetchAgent()
try:
    res = fetcher.execute({"url": "https://www.google.com"})
    print("Content preview:", res["outputs"]["content"][:100])
except Exception as e:
    print("WebFetch failed:", e)

print("\n--- Testing JobDescriptionAgent (URL) ---")
loader = JobDescriptionAgent()
try:
    res = loader.execute({"job_url": "https://www.google.com"})
    print("Job description loaded, length:", len(res["outputs"]["job_description"]))
except Exception as e:
    print("JobDescriptionAgent failed:", e)
