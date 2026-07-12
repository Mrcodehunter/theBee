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
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

from models import DEFAULT_MODEL_ID, build_llm
from prompts import build_system_prompt
from tools import get_tools

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = DEFAULT_MODEL_ID


def build_graph(project_dir: Path):
    """Build and compile the agent graph, sandboxed to `project_dir`."""
    project_dir = Path(project_dir).resolve()

    tools = get_tools(project_dir)
    system_prompt = build_system_prompt(project_dir)

    # -- the model, with tools bound to it -----------------------------------
    # bind_tools() attaches the tool schemas to every request, so the model
    # knows what it can call. create_react_agent did this for us before.
    # Which model backs a given turn is chosen per-request (via config, keyed
    # by thread_id like everything else) rather than fixed at graph-build
    # time, so a conversation can switch models turn-by-turn. Bound llms are
    # cached per model id since building/binding isn't free.

    llm_cache: dict[str, object] = {}

    def get_bound_llm(model_id: str):
        if model_id not in llm_cache:
            llm_cache[model_id] = build_llm(model_id).bind_tools(tools)
        return llm_cache[model_id]

    # -- NODE 1: call the model ----------------------------------------------

    def call_model(state: MessagesState, config: RunnableConfig):
        """Send system prompt + full conversation to the model.
        Returns its response; MessagesState appends it automatically."""
        model_id = config.get("configurable", {}).get("model_id", DEFAULT_MODEL_ID)
        llm_with_tools = get_bound_llm(model_id)
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
