
import requests
from typing import Any, Dict
from ai_workflows.agents import Agent
from html.parser import HTMLParser

class ResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_result = {}
        self.in_result = False
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # DuckDuckGo HTML result parsing logic
        if tag == "a" and "result__a" in attrs_dict.get("class", "").split():
            self.current_result = {"title": "", "url": attrs_dict.get("href", "")}
            self.in_result = True
            self.in_title = True
        elif tag == "a" and "result__snippet" in attrs_dict.get("class", "").split():
            self.current_result["snippet"] = ""

    def handle_endtag(self, tag):
        if tag == "a":
            if self.in_title:
                self.in_title = False
            elif self.in_result:
                self.results.append(self.current_result)
                self.in_result = False
                self.current_result = {}

    def handle_data(self, data):
        if self.in_title:
            self.current_result["title"] += data
        elif self.in_result and "snippet" in self.current_result:
            self.current_result["snippet"] += data

class WebSearchAgent(Agent):
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        query = inputs.get("query")
        # Ensure proper encoding
        url = f"https://html.duckduckgo.com/html/"
        data = {'q': query}

        # Use POST to avoid URL encoding issues
        response = requests.post(url, data=data, verify=False, headers={'User-Agent': 'Mozilla/5.0'})

        parser = ResultParser()
        parser.feed(response.text)

        results = parser.results[:5]

        return {
            "outputs": {
                "results": results,
                "result_count": len(results),
                "query": query
            }
        }
