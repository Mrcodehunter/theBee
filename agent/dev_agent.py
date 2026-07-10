"""
dev_agent.py — the human interface (CLI). The graph lives in agent_graph.py.

Run:
    python dev_agent.py C:/path/to/your/project
"""

import sys
import uuid
from pathlib import Path

from langgraph.types import Command

from agent_graph import build_graph, MODEL_NAME
from prompts import INIT_TASK

MAX_ITERATIONS = 15

# ---------------------------------------------------------------------------
# Resolve the project directory (the sandbox)
# ---------------------------------------------------------------------------

if len(sys.argv) > 1:
    PROJECT_DIR = Path(sys.argv[1]).resolve()
else:
    PROJECT_DIR = Path.cwd().resolve()

if not PROJECT_DIR.is_dir():
    sys.exit(f"Project directory not found: {PROJECT_DIR}")

# Build the graph once; reuse it for every task in the session. The graph is
# checkpointed, so conversation history lives in the checkpointer keyed by
# thread_id rather than being passed in by hand on every call.
agent = build_graph(PROJECT_DIR)
thread_id = str(uuid.uuid4())
printed_upto = 0

def _print_new_messages(messages: list) -> None:
    """Print any messages appended to the thread since we last printed."""
    global printed_upto
    for msg in messages[printed_upto:]:
        msg_type = getattr(msg, "type", "")
        if msg_type == "ai":
            tool_calls = getattr(msg, "tool_calls", []) or []
            for call in tool_calls:
                print(f"  🔧 {call['name']}({call['args']})")
            if msg.content:
                if not tool_calls and '"name"' in str(msg.content) and '"arguments"' in str(msg.content):
                    print("  ⚠️  Model wrote a tool call as TEXT instead of calling it!")
                print(f"\n🤖 {msg.content}\n")
        elif msg_type == "tool":
            preview = str(msg.content)[:300].replace("\n", " ")
            print(f"     ↳ {preview}")
    printed_upto = len(messages)


def _handle_interrupts(result: dict, config: dict) -> dict:
    """If the graph paused on interrupt() (a tool wants approval), ask the
    human in the terminal and resume. Loops in case of back-to-back
    approvals. Returns the final result once the graph reaches END."""
    while result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        if payload.get("action") == "write_file":
            print(f"\n📝 Agent wants to {payload['summary']}")
            print("-" * 50)
            print(payload.get("preview", ""))
            print("-" * 50)
        else:
            print(f"\n⚠️  Agent wants to run: {payload.get('command', payload.get('summary'))}")
        answer = input("   Allow? [y/N]: ").strip().lower() == "y"
        result = agent.invoke(Command(resume=answer), config=config)
    return result


def run_task(task: str) -> None:
    """Send one task through the graph, print its steps as they resolve."""
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": MAX_ITERATIONS * 2,
    }

    print("  ⏳ thinking... (first request loads the model, can take a minute)")

    result = agent.invoke({"messages": [{"role": "user", "content": task}]}, config=config)
    result = _handle_interrupts(result, config)
    _print_new_messages(result["messages"])


def main() -> None:
    global agent, thread_id, printed_upto
    print("=" * 60)
    print(f"  Dev Agent  |  model: {MODEL_NAME}  |  graph: agent_graph.py")
    print(f"  Sandbox:   {PROJECT_DIR}")
    print("  Type a task, or 'quit' to exit. 'reset' clears memory.")
    print("  'init' audits the project and (re)generates AGENT.md.")
    print("=" * 60)

    # Offer to generate AGENT.md if the project doesn't have one yet.
    if not (PROJECT_DIR / "AGENT.md").exists():
        answer = input(
            "\nNo AGENT.md found. Audit the project and generate one? [y/N]: "
        ).strip().lower()
        if answer == "y":
            try:
                run_task(INIT_TASK)
                if (PROJECT_DIR / "AGENT.md").exists():
                    print("  🔄 Rebuilding agent so it loads the new AGENT.md...")
                    agent = build_graph(PROJECT_DIR)
                    thread_id = str(uuid.uuid4())
                    printed_upto = 0
            except Exception as e:
                print(f"Init failed: {e}")

    while True:
        try:
            task = input("\nYou> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not task:
            continue
        if task.lower() in {"quit", "exit"}:
            break
        if task.lower() == "reset":
            thread_id = str(uuid.uuid4())
            printed_upto = 0
            print("(memory cleared)")
            continue
        if task.lower() == "init":
            try:
                run_task(INIT_TASK)
                if (PROJECT_DIR / "AGENT.md").exists():
                    print("  🔄 Rebuilding agent so it loads the new AGENT.md...")
                    agent = build_graph(PROJECT_DIR)
                    thread_id = str(uuid.uuid4())
                    printed_upto = 0
            except Exception as e:
                print(f"Init failed: {e}")
            continue
        try:
            run_task(task)
        except Exception as e:
            print(f"Agent error: {e}")

    print("Bye!")


if __name__ == "__main__":
    main()
