
import requests
from typing import Any, Dict
from ai_workflows.agents import Agent
from bs4 import BeautifulSoup

class WebFetchAgent(Agent):
    """Fetches and extracts text content from a URL."""
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        url = inputs.get("url")
        if not url:
            raise ValueError("web_fetch requires 'url' parameter.")

        try:
            response = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()

            # Extract text
            soup = BeautifulSoup(response.text, 'html.parser')
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text(separator=' ')
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return {
                "outputs": {
                    "content": text,
                    "url": url
                }
            }
        except Exception as e:
            raise RuntimeError(f"Failed to fetch {url}: {e}")
