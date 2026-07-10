"""sandbox.py — path-safety helper shared by the file tools.

Keeps the agent boxed to project_dir: any relative path that resolves
outside of it is rejected before a tool touches the filesystem.
"""

from pathlib import Path
from typing import Callable


def make_safe_path(project_dir: Path) -> Callable[[str], Path]:
    def safe_path(relative_path: str) -> Path:
        p = (project_dir / relative_path).resolve()
        if not p.is_relative_to(project_dir):
            raise ValueError(
                f"Access denied: '{relative_path}' is outside the project directory."
            )
        return p

    return safe_path
