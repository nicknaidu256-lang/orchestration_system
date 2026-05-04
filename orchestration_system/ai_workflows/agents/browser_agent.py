import time
import os
from typing import Any, Dict
from ai_workflows.agents import Agent

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

class BrowserAgent(Agent):
    """
    Agent for browser automation using Playwright.
    Capabilities: screenshot, get_text, click.
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if not PLAYWRIGHT_AVAILABLE:
            return {
                "outputs": {
                    "content": "BrowserAgent: playwright not installed. pip install playwright",
                    "screenshot_path": ""
                }
            }

        url = inputs.get("url")
        action = inputs.get("action")
        selector = inputs.get("selector")

        if not url:
            raise ValueError("BrowserAgent requires 'url' parameter.")
        if not action:
            raise ValueError("BrowserAgent requires 'action' parameter.")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle")

                content = ""
                screenshot_path = ""

                if action == "get_text":
                    if selector:
                        element = page.query_selector(selector)
                        content = element.inner_text() if element else f"Selector '{selector}' not found."
                    else:
                        content = page.inner_text("body")

                elif action == "screenshot":
                    timestamp = int(time.time())
                    os.makedirs("output", exist_ok=True)
                    screenshot_path = os.path.join("output", f"screenshot_{timestamp}.png")
                    page.screenshot(path=screenshot_path)
                    content = f"Screenshot saved to {screenshot_path}"

                elif action == "click":
                    if not selector:
                        raise ValueError("Action 'click' requires a 'selector'.")
                    page.click(selector)
                    # Small wait for action to settle if needed, but click usually is enough
                    content = f"Clicked element matching selector: {selector}"
                else:
                    browser.close()
                    raise ValueError(f"Unknown action: {action}")

                browser.close()
                return {
                    "outputs": {
                        "content": content,
                        "screenshot_path": screenshot_path
                    }
                }
        except Exception as e:
            return {
                "outputs": {
                    "content": f"BrowserAgent error: {str(e)}",
                    "screenshot_path": ""
                }
            }
