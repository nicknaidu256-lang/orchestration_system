"""
WSL-to-Windows bridge utility.

When the orchestration system runs inside WSL/Ubuntu but the coding CLIs
(Claude Code, OpenCode, KiloCode, Gemini CLI) are installed on the Windows
host, this module provides helpers to call those Windows executables from
within WSL using the cmd.exe interop layer.

Usage:
    from ai_workflows.agents.wsl_bridge import run_cli

    result = run_cli(
        cli_name="claude",
        args=["--print", "my task"],
        working_dir=".",
        timeout=300
    )
"""

import os
import platform
import shutil
import subprocess
from typing import List, Optional


def is_wsl() -> bool:
    """Return True if we are running inside WSL."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


def find_cli(name: str) -> Optional[str]:
    """
    Try to locate a CLI by name.
    1. Check native PATH (works on both Linux-native and Windows-native installs).
    2. If in WSL, check common Windows install locations via /mnt/c.
    Returns the command/path to use, or None if not found.
    """
    # Native path first
    native = shutil.which(name)
    if native:
        return native

    # WSL: try Windows PATH via cmd.exe
    if is_wsl():
        try:
            result = subprocess.run(
                ["cmd.exe", "/c", f"where {name}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                # cmd.exe found it — we'll use cmd.exe /c to call it
                return "__via_cmd__"
        except Exception:
            pass

    return None


def run_cli(
    cli_name: str,
    args: List[str],
    working_dir: str = ".",
    timeout: int = 300,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """
    Run a CLI command, automatically bridging through cmd.exe if in WSL
    and the CLI is only available on the Windows side.

    Args:
        cli_name: The base CLI name, e.g. "claude", "kilo", "opencode"
        args: Arguments to pass after the CLI name
        working_dir: Working directory (Linux path; converted for cmd.exe)
        timeout: Timeout in seconds
        env: Optional environment variables

    Returns:
        subprocess.CompletedProcess with stdout, stderr, returncode
    """
    location = find_cli(cli_name)

    if location is None:
        # Not found anywhere — return a synthetic failure result
        return subprocess.CompletedProcess(
            args=[cli_name] + args,
            returncode=127,
            stdout="",
            stderr=f"{cli_name}: command not found in PATH or Windows host"
        )

    if location == "__via_cmd__":
        # Build a cmd.exe /c call, converting the working dir to a Windows path
        win_cwd = _to_windows_path(working_dir)
        # Escape args for cmd
        escaped_args = " ".join(_escape_arg(a) for a in args)
        cmd_line = f"cd /d {win_cwd} && {cli_name} {escaped_args}"
        return subprocess.run(
            ["cmd.exe", "/c", cmd_line],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
    else:
        # Native — call directly
        return subprocess.run(
            [location] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
            env=env
        )


def run_verify(command: str, working_dir: str = ".", timeout: int = 120) -> subprocess.CompletedProcess:
    """
    Run a verify/shell command, bridging through cmd.exe if in WSL.
    The command is a shell string (not a list).
    """
    if is_wsl():
        win_cwd = _to_windows_path(working_dir)
        cmd_line = f"cd /d {win_cwd} && {command}"
        return subprocess.run(
            ["cmd.exe", "/c", cmd_line],
            capture_output=True, text=True, timeout=timeout
        )
    else:
        return subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=timeout, cwd=working_dir
        )


def _to_windows_path(linux_path: str) -> str:
    """
    Convert a Linux/WSL path to a Windows path.
    /mnt/c/Users/... -> C:\\Users\\...
    Relative paths are resolved against the current directory.
    """
    if not linux_path or linux_path == ".":
        linux_path = os.getcwd()

    linux_path = os.path.abspath(linux_path)

    if linux_path.startswith("/mnt/"):
        parts = linux_path[len("/mnt/"):].split("/", 1)
        drive = parts[0].upper() + ":"
        rest = parts[1].replace("/", "\\") if len(parts) > 1 else ""
        return f"{drive}\\{rest}"

    # Fallback — just return as-is and hope for the best
    return linux_path


def _escape_arg(arg: str) -> str:
    """Wrap an argument in double-quotes if it contains spaces."""
    if " " in arg:
        return f'"{arg}"'
    return arg
