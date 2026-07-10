"""command_tools.py — run_command tool, sandboxed to the project directory."""

import subprocess
from pathlib import Path

from langchain_core.tools import tool
from langgraph.types import interrupt

COMMAND_TIMEOUT = 60

DANGEROUS_PATTERNS = [
    "rm ", "del ", "rmdir", "git push", "git reset", "sudo",
    "format", "shutdown", "> /", "mkfs", "dd ",
]


def build_run_command_tool(project_dir: Path):
    @tool
    def run_command(command: str) -> str:
        """Run a shell command inside the project directory (e.g. run tests,
        list files, git status). Output is returned to you. Dangerous commands
        require the human's approval."""
        lowered = command.lower()
        if any(pat in lowered for pat in DANGEROUS_PATTERNS):
            # See file_tools.build_write_file_tool for why interrupt() must
            # stay outside any try/except that could swallow it.
            approved = interrupt({
                "kind": "approval",
                "action": "run_command",
                "command": command,
                "summary": f"Run: {command}",
            })
            if not approved:
                return "DENIED: the human rejected this command. Try another approach."
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
            )
            output = (result.stdout + result.stderr).strip() or "(no output)"
            if len(output) > 8_000:
                output = output[:8_000] + "\n[...output truncated...]"
            return f"exit code {result.returncode}\n{output}"
        except subprocess.TimeoutExpired:
            return f"ERROR: command timed out after {COMMAND_TIMEOUT}s."
        except Exception as e:
            return f"ERROR: {e}"

    return run_command
