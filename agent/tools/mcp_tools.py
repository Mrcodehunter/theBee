"""mcp_tools.py — loads tools from configured MCP (Model Context Protocol)
servers and wraps each one in the same human-in-the-loop approval gate used
by write_file/run_command, unless that server is marked "trusted".

MultiServerMCPClient.get_tools() is async and opens a fresh MCP session per
tool call (documented library behavior, not a shortcut we're taking). That
lets each returned tool be wrapped in a plain sync LangChain tool whose
func() does interrupt() then asyncio.run(tool.ainvoke(...)) — a fresh event
loop per call is fine because there's no cross-call session state to
preserve. This keeps agent_graph.py/server.py/dev_agent.py fully sync, with
no changes needed there.
"""

import asyncio
import json
from pathlib import Path

from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import interrupt

MCP_CONFIG_PATH = Path(__file__).resolve().parent.parent / "mcp_servers.json"


def _load_config() -> dict:
    if not MCP_CONFIG_PATH.exists():
        return {}
    raw = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
    return raw.get("mcpServers", {})


def _substitute_project_dir(args: list, project_dir: Path) -> list:
    return [str(project_dir) if a == "{project_dir}" else a for a in args]


def _wrap_with_approval(mcp_tool: BaseTool, server_name: str, trusted: bool) -> StructuredTool:
    def call(**kwargs):
        if not trusted:
            # See file_tools.build_write_file_tool for why interrupt() must
            # stay outside any try/except that could swallow it.
            approved = interrupt({
                "kind": "approval",
                "action": "mcp_tool",
                "server": server_name,
                "tool": mcp_tool.name,
                "summary": f"Call MCP tool '{mcp_tool.name}' on server '{server_name}'",
                "preview": json.dumps(kwargs, indent=2)[:600],
            })
            if not approved:
                return "DENIED: the human rejected this tool call."
        return asyncio.run(mcp_tool.ainvoke(kwargs))

    return StructuredTool.from_function(
        func=call,
        name=mcp_tool.name,
        description=mcp_tool.description,
        args_schema=mcp_tool.args_schema,
    )


def load_mcp_tools(project_dir: Path) -> list:
    """Load tools from every server in mcp_servers.json, sandboxed to
    project_dir via the {project_dir} arg placeholder. Returns [] if no
    config file is present — MCP support is fully optional."""
    servers = _load_config()
    if not servers:
        return []

    from langchain_mcp_adapters.client import MultiServerMCPClient

    trust: dict = {}
    clean_configs: dict = {}
    for name, cfg in servers.items():
        cfg = dict(cfg)
        trust[name] = cfg.pop("trusted", False)
        if "args" in cfg:
            cfg["args"] = _substitute_project_dir(cfg["args"], project_dir)
        clean_configs[name] = cfg

    client = MultiServerMCPClient(clean_configs)

    async def _discover():
        pairs = []
        for name in clean_configs:
            try:
                tools = await client.get_tools(server_name=name)
            except Exception as e:
                # One misconfigured/unreachable server shouldn't take down
                # the whole agent — MCP support is meant to be optional.
                print(f"MCP server '{name}' failed to load, skipping: {e}")
                continue
            pairs.extend((t, name) for t in tools)
        return pairs

    discovered = asyncio.run(_discover())
    return [_wrap_with_approval(tool, name, trust[name]) for tool, name in discovered]
