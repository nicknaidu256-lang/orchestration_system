#!/usr/bin/env python3
"""
AI Workflow CLI — command-line interface for running AI workflows.

Commands:
  run <plan.json>          Execute a workflow plan
  new <workflow_id>        Create a fresh run directory and execute
  list                     List available workflow plans in registry
  validate <plan.json>     Validate a plan file without executing
  show-run <run_id>        Show state and snapshots for a run

Examples:
  ai-workflow run ./plans/generate_and_write.json
  ai-workflow new generate_and_write --param prompt="Hello world"
  ai-workflow list
  ai-workflow validate ./plans/generate_and_write.json
  ai-workflow show-run 20240101_120000_abc123
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_workflows.executor import run_workflow
from ai_workflows.planner import validate_plan, PlanGenerator
from ai_workflows.state import StateManager


def cmd_run(args):
    """Execute a workflow plan."""
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"Error: Plan file not found: {plan_path}", file=sys.stderr)
        sys.exit(1)

    try:
        plan = json.loads(plan_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in plan file: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate plan structure and hash
    try:
        validate_plan(plan)
    except ValueError as e:
        print(f"Error: Invalid plan: {e}", file=sys.stderr)
        sys.exit(1)

    # Create run directory
    runs_base = Path.home() / ".ai-workflows" / "runs"
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + plan["workflow_id"][:8]
    run_dir = runs_base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save plan copy to run_dir for provenance
    (run_dir / "plan.json").write_text(json.dumps(plan, indent=2))

    print(f"Starting workflow: {plan['workflow_id']} v{plan.get('version', '?')}")
    print(f"Run ID: {run_id}")
    print(f"Run dir: {run_dir}")

    # Execute
    initial_state = {}
    if args.input:
        for item in args.input:
            key, val = item.split("=", 1)
            initial_state[key] = val

    run_workflow(plan=plan, run_dir=run_dir, initial_state=initial_state)


def cmd_new(args):
    """Create a new run from a workflow template with parameters."""
    # This is a convenience command that parameterizes a template
    # For v1, it just wraps 'run' with parameter substitution if needed
    # In future: template engine with {{param}} substitution
    print("'new' command not yet fully implemented — use 'run' for now.")
    sys.exit(1)


def cmd_list(args):
    """List available workflow plans."""
    # Try home directory registry first, then local package registry
    registry_path = Path.home() / ".ai-workflows" / "registry" / "registry.json"
    if not registry_path.exists():
        # Fallback to local package registry
        package_root = Path(__file__).parent
        registry_path = package_root / "registry" / "registry.json"

    if not registry_path.exists():
        print("No registry found at ~/.ai-workflows/registry/registry.json or locally.")
        print("Create it to enable workflow discovery.")
        sys.exit(0)

    registry = json.loads(registry_path.read_text())
    mapping = registry.get("mapping", {})

    print("Available capabilities (registry mapping):")
    for capability, agent in mapping.items():
        print(f"  {capability:25s} -> {agent}")

    # Also look for plan files in standard locations
    print("\nScanning for plan files...")
    search_paths = [
        Path.home() / ".ai-workflows" / "plans",
        Path.cwd() / "ai_workflows" / "plans",
        Path.cwd() / "plans",
    ]

    # Add environment variable path if set
    env_plans = os.getenv("AI_WORKFLOWS_PLANS_DIR") or os.getenv("AI_WORKFLOWS_PLANS")
    if env_plans:
        search_paths.append(Path(env_plans))

    # Add explicit CLI flag path if set
    if getattr(args, "plans_dir", None):
        search_paths.append(Path(args.plans_dir))
    found = []
    for search_path in search_paths:
        if search_path.exists():
            for plan_file in search_path.glob("*.json"):
                try:
                    plan = json.loads(plan_file.read_text())
                    found.append(f"  {plan_file}  (workflow_id={plan.get('workflow_id','?')})")
                except Exception:
                    pass

    if found:
        print("Discovered plan files:")
        for line in found:
            print(line)
    else:
        print("  No plan files found in standard locations.")

def cmd_validate(args):
    """Validate a plan file without executing."""
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"Error: Plan file not found: {plan_path}", file=sys.stderr)
        sys.exit(1)

    try:
        plan = json.loads(plan_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        validate_plan(plan)
        print(f"Plan is valid.")
        print(f"  Workflow ID: {plan['workflow_id']}")
        print(f"  Version: {plan.get('version', '?')}")
        print(f"  Created by: {plan.get('created_by', '?')}")
        print(f"  Plan hash: {plan['plan_hash']}")
        print(f"  Steps: {len(plan['steps'])}")
        for i, step in enumerate(plan["steps"]):
            print(f"    {i+1}. {step['id']}  ({step['capability']}) → outputs: {step['outputs']}")
    except ValueError as e:
        print(f"Error: Invalid plan: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_generate(args):
    """Generate a workflow plan."""
    generator = PlanGenerator()
    output_dir = args.output_dir or Path("./plans")
    plan = generator.generate(
        goal=args.goal,
        workflow_id=args.workflow_id,
        output_dir=output_dir
    )
    print(f"Generated plan: {plan['workflow_id']}")
    print(json.dumps(plan, indent=2))


def cmd_show_run(args):
    """Show state and snapshots for a run."""
    run_id = args.run_id
    run_dir = Path.home() / ".ai-workflows" / "runs" / run_id
    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    state_path = run_dir / "state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text())
        print(f"State for run {run_id}:")
        print(json.dumps(state, indent=2))
    else:
        print(f"No state.json found in {run_dir}")

    steps_dir = run_dir / "steps"
    if steps_dir.exists():
        snapshots = sorted(steps_dir.glob("*.json"))
        if snapshots:
            print(f"\nSnapshots ({len(snapshots)}):")
            for snap in snapshots:
                data = json.loads(snap.read_text())
                status = data.get("status", "?")
                print(f"  {snap.name}: {status}")


def main():
    parser = argparse.ArgumentParser(
        description="AI Workflow CLI — execute structured deterministic workflows"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run
    run_parser = subparsers.add_parser("run", help="Execute a workflow plan")
    run_parser.add_argument("plan", help="Path to plan JSON file")
    run_parser.add_argument("--run-id", help="Custom run identifier (default: timestamp)")
    run_parser.add_argument("--input", action="append", help="Initial state key=value")
    run_parser.set_defaults(func=cmd_run)

    # new
    new_parser = subparsers.add_parser("new", help="Create new run from template")
    new_parser.add_argument("workflow_id", help="Workflow template ID")
    new_parser.add_argument("--param", action="append", help="Parameter key=value")
    new_parser.set_defaults(func=cmd_new)

    # list
    list_parser = subparsers.add_parser("list", help="List available workflows")
    list_parser.add_argument("--plans-dir", help="Additional directory to scan for plans")
    list_parser.set_defaults(func=cmd_list)

    # validate
    val_parser = subparsers.add_parser("validate", help="Validate a plan file")
    val_parser.add_argument("plan", help="Path to plan JSON file")
    val_parser.set_defaults(func=cmd_validate)

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate a workflow plan")
    gen_parser.add_argument("goal", help="The goal for the workflow")
    gen_parser.add_argument("--output-dir", type=Path, help="Directory to save the plan")
    gen_parser.add_argument("--workflow-id", required=True, help="Workflow ID")
    gen_parser.set_defaults(func=cmd_generate)

    # show-run
    show_parser = subparsers.add_parser("show-run", help="Show run state")
    show_parser.add_argument("run_id", help="Run identifier")
    show_parser.set_defaults(func=cmd_show_run)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

