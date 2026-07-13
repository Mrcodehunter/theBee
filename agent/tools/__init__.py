"""tools/ — the agent's hands, one file per tool family.

Each tool is built by a factory function that closes over the project
directory (the sandbox), so read_file/write_file/run_command can't touch
anything outside it. get_tools() assembles the full toolset that
agent_graph.py binds to the model.
"""

from pathlib import Path

from .browse_tools import build_browse_page_tool, build_compare_pages_tool
from .command_tools import build_run_command_tool
from .file_tools import build_read_file_tool, build_write_file_tool
from .image_tools import build_analyze_image_tool
from .mcp_tools import load_mcp_tools
from .sandbox import make_safe_path
from .search_tools import build_web_search_tool
from .story_tools import build_list_story_templates_tool


def get_tools(project_dir: Path) -> list:
    safe_path = make_safe_path(project_dir)
    tools = [
        build_read_file_tool(safe_path),
        build_write_file_tool(safe_path),
        build_run_command_tool(project_dir),
        build_web_search_tool(),
        build_browse_page_tool(),
        build_compare_pages_tool(),
        build_analyze_image_tool(safe_path),
        build_list_story_templates_tool(),
    ]
    tools.extend(load_mcp_tools(project_dir))
    return tools
