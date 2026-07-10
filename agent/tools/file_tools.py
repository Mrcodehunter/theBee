"""file_tools.py — read_file / write_file tools, sandboxed to the project directory."""

from pathlib import Path
from typing import Callable

from langchain_core.tools import tool
from langgraph.types import interrupt


def build_read_file_tool(safe_path: Callable[[str], Path]):
    @tool
    def read_file(path: str) -> str:
        """Read a text file. `path` is relative to the project directory.
        Use this to inspect code before editing it."""
        try:
            p = safe_path(path)
            content = p.read_text(encoding="utf-8", errors="replace")
            if len(content) > 20_000:
                return content[:20_000] + "\n\n[...file truncated at 20k chars...]"
            return content
        except Exception as e:
            return f"ERROR reading '{path}': {e}"

    return read_file


def build_write_file_tool(safe_path: Callable[[str], Path]):
    @tool
    def write_file(path: str, content: str) -> str:
        """Write (or overwrite) a text file. `path` is relative to the project
        directory. Always read_file first if the file exists, so you don't
        destroy content you haven't seen."""
        # NOTE: interrupt() raises a special GraphInterrupt exception that must
        # propagate out of this function to actually pause the graph — it must
        # never be caught by a bare `except Exception`, so it lives outside
        # the try/except blocks below.
        try:
            p = safe_path(path)
        except Exception as e:
            return f"ERROR writing '{path}': {e}"

        action = "OVERWRITE existing" if p.exists() else "create new"
        approved = interrupt({
            "kind": "approval",
            "action": "write_file",
            "path": path,
            "summary": f"{action} file: {path} ({len(content)} chars)",
            "preview": content[:600] + ("\n[...truncated...]" if len(content) > 600 else ""),
        })
        if not approved:
            return "DENIED: the human rejected this write. Ask them what they want instead."

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"OK: wrote {len(content)} chars to '{path}'."
        except Exception as e:
            return f"ERROR writing '{path}': {e}"

    return write_file
