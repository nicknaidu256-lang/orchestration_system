"""
WSL-to-Windows bridge utility.

When the orchestration system runs inside WSL/Ubuntu but the coding CLIs
(Claude Code, OpenCode, KiloCode, Gemini CLI) are installed on the Windows
host, this module provides helpers to call those Windows executables from
within WSL using the cmd.exe interop layer.
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


def _try_cmd_exe(name: str) -> bool:
    """Check if a CLI is callable via cmd.exe (Windows PATH)."""
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", f"where {name}"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def _is_windows_script(path: str) -> bool:
    """
    Return True if the found path is a Windows batch/cmd script that
    cannot execute natively in Linux and needs cmd.exe routing.
    """
    if not path:
        return False
    # Try executing it — if it fails with the npm "wrong version" message
    # or a Windows-script error, it needs cmd.exe
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True, text=True, timeout=8
        )
        combined = (result.stdout + result.stderr).lower()
        if "package manager failed to install" in combined:
            return True
        if "cannot execute binary file" in combined:
            return True
        return False
    except (PermissionError, OSError):
        # Can't execute at all — definitely needs cmd.exe
        return True
    except Exception:
        return False


def find_cli(name: str) -> Optional[str]:
    """
    Try to locate a CLI by name.
    Returns:
      - A native Linux path string if it runs natively in WSL
      - "__via_cmd__" if it must be called through cmd.exe (Windows-only script)
      - None if not found anywhere
    """
    # Check native PATH first
    native = shutil.which(name)
    if native:
        # Verify it actually runs natively (not a Windows batch wrapper)
        if not _is_windows_script(native):
            return native
        # It's a Windows script — route via cmd.exe if available
        if is_wsl() and _try_cmd_exe(name):
            return "__via_cmd__"
        return None

    # Not in native PATH — if in WSL, try Windows PATH via cmd.exe
    if is_wsl() and _try_cmd_exe(name):
        return "__via_cmd__"

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
    """
    location = find_cli(cli_name)

    if location is None:
        return subprocess.CompletedProcess(
            args=[cli_name] + args,
            returncode=127,
            stdout="",
            stderr=f"{cli_name}: command not found in PATH or Windows host"
        )

    if location == "__via_cmd__":
        win_cwd = _to_windows_path(working_dir)
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
    """Convert a Linux/WSL path to a Windows path."""
    if not linux_path or linux_path == ".":
        linux_path = os.getcwd()

    linux_path = os.path.abspath(linux_path)

    if linux_path.startswith("/mnt/"):
        parts = linux_path[len("/mnt/"):].split("/", 1)
        drive = parts[0].upper() + ":"
        rest = parts[1].replace("/", "\\") if len(parts) > 1 else ""
        return f"{drive}\\{rest}"

    return linux_path


def _escape_arg(arg: str) -> str:
    """Wrap an argument in double-quotes if it contains spaces."""
    if " " in arg:
        return f'"{arg}"'
    return arg
