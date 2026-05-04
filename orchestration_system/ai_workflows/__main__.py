#!/usr/bin/env python3
"""
ai-workflow — entry point for AI Workflows CLI.

Usage:
  ai-workflow run <plan.json>
  ai-workflow new <workflow_id> --param key=value
  ai-workflow list
  ai-workflow validate <plan.json>
  ai-workflow show-run <run_id>
"""

import sys
from pathlib import Path

# Ensure ai_workflows is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_workflows.cli import main

if __name__ == "__main__":
    main()

