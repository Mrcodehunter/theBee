"""
agent_graph.py — the agent's brain, built as an explicit LangGraph.
Its hands (the tools) live in tools/.

This replaces the prebuilt create_react_agent with a hand-written graph:

        START ──► agent ──(tool call?)──► tools ──► back to agent
                    │
                    └──(no tool call = final answer)──► END

Exposes one function:  build_graph(project_dir) -> compiled graph
The compiled graph is checkpointed (MemorySaver), so a run can pause on
interrupt() (human approval) and be resumed later with Command(resume=...),
identified by a `thread_id` in the run config. This is what lets both the
CLI (dev_agent.py) and the web backend (server.py) share one approval model.
"""

from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

from prompts import build_system_prompt
from tools import get_tools

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "qwen3:8b"


def build_graph(project_dir: Path):
    """Build and compile the agent graph, sandboxed to `project_dir`."""
    project_dir = Path(project_dir).resolve()

    tools = get_tools(project_dir)

    # -- the model, with tools bound to it -----------------------------------
    # bind_tools() attaches the tool schemas to every request, so the model
    # knows what it can call. create_react_agent did this for us before.

    llm = ChatOllama(model=MODEL_NAME, temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = build_system_prompt(project_dir)

    # -- NODE 1: call the model ----------------------------------------------

    def call_model(state: MessagesState):
        """Send system prompt + full conversation to the model.
        Returns its response; MessagesState appends it automatically."""
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # -- NODE 2: execute tools -----------------------------------------------
    # ToolNode reads the last message's tool_calls, runs the matching
    # functions, and returns their results as tool-messages. If a tool calls
    # interrupt(), the whole graph run pauses here until it's resumed with
    # Command(resume=...) against the same thread_id.

    tool_node = ToolNode(tools)

    # -- EDGE LOGIC: after the model speaks, continue or stop? ----------------

    def should_continue(state: MessagesState):
        last_message = state["messages"][-1]
        if last_message.tool_calls:   # model asked for a tool
            return "tools"
        return END                    # plain text = final answer

    # -- ASSEMBLE ---------------------------------------------------------

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, ["tools", END])
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=MemorySaver())
