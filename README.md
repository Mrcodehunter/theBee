# 🐝 theBee

A sandboxed AI coding agent — think "your own tiny Claude Code" — built from
scratch on [LangGraph](https://www.langchain.com/langgraph). The web UI's
model picker lets you switch between several model backends (all with a free
tier, plus Claude) at any point in a conversation; every backend is
registered in one place (`agent/models.py`), so adding another is a small,
localized change.

It ships with two front ends that share the same brain:

- a **CLI** (`dev_agent.py`) for quick terminal use, and
- a **web chat UI** (React + Vite + Tailwind, in `ui/`) served by a FastAPI
  backend (`server.py`) that streams the agent's thoughts, tool calls, and
  results over SSE.

## Goal

Give an LLM hands and eyes on a real project — the ability to read files,
write/edit files, run shell commands, and search and browse the live web —
while keeping a human in the loop for anything risky, regardless of which
model backend is answering. The project is both a working dev-assistant tool
and a learning reference for how to hand-roll an agent loop with LangGraph
instead of using a prebuilt `create_react_agent`, and how to wire that same
graph into both a CLI and a streaming web app.

Design principles baked into the code:

- **Sandboxed by construction** — every file tool resolves paths through
  `tools/sandbox.py`, which rejects anything that escapes the target
  project directory. The agent cannot read or write outside the folder
  it was pointed at.
- **Human-in-the-loop approval** — file writes and "dangerous" shell
  commands (`rm`, `git push`, `sudo`, `shutdown`, etc.) pause the graph via
  LangGraph's `interrupt()` and wait for explicit yes/no approval — in the
  terminal for the CLI, as an approval card in the web UI.
- **One graph, two front ends** — `agent_graph.py` is the single source of
  truth for the agent's behavior. Both `dev_agent.py` and `server.py` just
  drive that same compiled graph, keyed by a `thread_id`, so conversation
  history and pending approvals are handled entirely by LangGraph's
  checkpointer (`MemorySaver`).
- **Freshness over guessing** — the system prompt forces a `web_search` (and
  a follow-up `browse_page` read of the full article) whenever a question
  could depend on anything that changed after the model's training cutoff,
  instead of letting the model guess from stale memory.
- **Self-documenting** — an `init` command audits the target project and
  generates an `AGENT.md` (tech stack, structure, conventions, how to
  run/test), mirroring what tools like Claude Code do with `/init`.

## Technologies

**Agent / backend** (`agent/`)
- [Python 3](https://www.python.org/) 3.11+ (built/tested on 3.14)
- [LangGraph](https://www.langchain.com/langgraph) — explicit `StateGraph`
  (agent ⇄ tools loop), `MemorySaver` checkpointing, `interrupt()` /
  `Command(resume=...)` for human-in-the-loop pauses
- [LangChain Core](https://python.langchain.com/) — messages, `@tool`
  decorator, tool binding
- Model backends, all registered in `agent/models.py` (pick any subset by
  setting the matching API key — see Prerequisites):
  [langchain-ollama](https://python.langchain.com/docs/integrations/chat/ollama/)
  (against [Ollama Cloud](https://ollama.com/cloud), the default),
  [langchain-google-genai](https://python.langchain.com/docs/integrations/chat/google_generative_ai/)
  (Gemini), [langchain-groq](https://python.langchain.com/docs/integrations/chat/groq/),
  [langchain-openai](https://python.langchain.com/docs/integrations/chat/openai/)
  (pointed at [OpenRouter](https://openrouter.ai/)'s free models), and
  [langchain-anthropic](https://python.langchain.com/docs/integrations/chat/anthropic/)
  (Claude)
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
  — HTTP API and Server-Sent Events (SSE) streaming to the UI
- [Pydantic](https://docs.pydantic.dev/) — request body validation
- [Requests](https://requests.readthedocs.io/) + [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
  — fetching and stripping web pages for `browse_page` / `compare_pages`
- [ddgs](https://pypi.org/project/ddgs/) — DuckDuckGo search, no API key
  required, for `web_search`

**Web UI** (`ui/`)
- [React 19](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vite.dev/) — dev server and build
- [Tailwind CSS 4](https://tailwindcss.com/) — styling
- [oxlint](https://oxc.rs/) — linting
- Native `fetch` + `ReadableStream` — hand-rolled SSE client (no extra
  streaming library) in `src/api.ts`

## Project structure

```
theBee/
├── agent/
│   ├── agent_graph.py       # the graph: agent node ⇄ tools node, build_graph(project_dir)
│   ├── dev_agent.py         # CLI front end — run a task, approve/deny in the terminal
│   ├── server.py            # FastAPI backend — sessions + SSE streaming for the web UI
│   ├── requirements.txt
│   ├── prompts/
│   │   ├── system_prompt.py # the agent's system prompt (rules, search policy)
│   │   └── init_prompt.py   # the one-off task behind the CLI's `init` command
│   └── tools/
│       ├── sandbox.py       # make_safe_path() — keeps every tool inside project_dir
│       ├── file_tools.py    # read_file, write_file (write requires approval)
│       ├── command_tools.py # run_command (dangerous commands require approval)
│       ├── search_tools.py  # web_search (DuckDuckGo)
│       └── browse_tools.py  # browse_page, compare_pages
└── ui/
    ├── src/
    │   ├── App.tsx           # session list + active chat window
    │   ├── api.ts             # REST + SSE client for the FastAPI backend
    │   ├── components/        # Sidebar, ChatWindow, ChatInput, MessageBubble, ToolCallChip, ApprovalCard
    │   └── ...
    └── package.json
```

## Prerequisites

- **Python** 3.11+
- **Node.js** 18+ (with npm) — only needed for the web UI
- **At least one model API key.** Every entry in the model picker (they're
  registered in `agent/models.py`) needs its own key — nothing works without
  at least one set, since there's no bundled zero-signup model anymore. All
  of these have a free tier:

  | Model | Env var | Get a key |
  |---|---|---|
  | GPT-OSS 20B via **Ollama Cloud** (default) | `OLLAMA_API_KEY` | [ollama.com/settings/keys](https://ollama.com/settings/keys) |
  | **Gemini** 3.5 Flash | `GOOGLE_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
  | Llama 3.3 70B via **Groq** | `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) |
  | Llama 3.3 70B via **OpenRouter** (`:free`) | `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) |
  | **Claude** Sonnet 5 (paid, no free tier) | `ANTHROPIC_API_KEY` | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) |

  Set whichever ones you want in the environment before starting the
  backend, or copy `agent/.env.example` to `agent/.env` and fill it in there
  (auto-loaded on startup, gitignored). Models without a key configured show
  as unavailable (greyed out) in the picker instead of erroring.

## Setup

1. **Clone and enter the repo**
   ```bash
   git clone <this-repo-url>
   cd theBee
   ```

2. **Install the agent's Python dependencies** (a virtualenv is recommended)
   ```bash
   cd agent
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

3. **Install the UI's dependencies** (only if you want the web chat, not just the CLI)
   ```bash
   cd ../ui
   npm install
   ```

4. **Set at least one model API key** — copy `agent/.env.example` to
   `agent/.env` and fill in the key(s) for whichever model(s) you want to
   use (see the table in Prerequisites).

## How to use

### Option A — CLI

Run the agent against any project directory (defaults to the current
working directory if omitted):

```bash
cd agent
python dev_agent.py C:/path/to/your/project
```

- On first run against a project without an `AGENT.md`, it offers to
  **audit the project and generate one**.
- Type a task in plain English (e.g. `add input validation to login.py`)
  and watch it plan, call tools, and report back.
- Special commands at the prompt:
  - `init` — (re)generate `AGENT.md`
  - `reset` — clear conversation memory (new thread)
  - `quit` / `exit` — end the session
- When the agent wants to **write a file** or run a **potentially dangerous
  command**, it pauses and asks `Allow? [y/N]` — review the preview/command
  before approving.

### Option B — Web UI (chat interface)

Run the backend and frontend in two terminals.

**Terminal 1 — backend**
```bash
cd agent
uvicorn server:app --reload --port 8000
```
By default the backend is sandboxed to the theBee repo's parent project
directory. Point it at a different project with an environment variable:
```bash
# Windows PowerShell
$env:AGENT_PROJECT_DIR = "C:\path\to\your\project"
uvicorn server:app --reload --port 8000
```

**Terminal 2 — frontend**
```bash
cd ui
npm run dev
```
Open the printed local URL (typically `http://localhost:5173`) in your
browser. Start a new chat, send a task, and watch tokens, tool calls, and
tool results stream in live. When the agent requests a file write or a
risky command, an approval card appears in the chat — approve or deny it
inline.

A model picker sits above the chat — switch between any configured model
(Ollama Cloud, Gemini, Groq, OpenRouter, Claude) at any point, even
mid-thread; the next message you send is answered by whichever model is
selected, with the full conversation history still shared between them.
Models without an API key set show up disabled in the dropdown.

### Verifying the backend is up

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/models
```
`/api/health` returns `{"status": "ok", "project_dir": "...", "model":
"ollama-cloud-gpt-oss-20b"}`. `/api/models` lists every registered model
with an `available` flag showing whether its API key is set.

## Available tools (what the agent can actually do)

| Tool | Purpose | Approval required? |
|---|---|---|
| `read_file` | Read a text file (relative to the sandboxed project dir) | No |
| `write_file` | Create or overwrite a text file | **Yes** |
| `run_command` | Run a shell command in the project directory | Only for patterns like `rm`, `del`, `git push`, `git reset`, `sudo`, `shutdown`, `format`, `mkfs`, `dd` |
| `web_search` | DuckDuckGo search — titles, URLs, snippets | No |
| `browse_page` | Fetch and read one URL's full text | No |
| `compare_pages` | Fetch 2–5 URLs and compare their content side by side | No |

Plus whatever's configured in `agent/mcp_servers.json` (see below) — every
MCP tool requires approval too, unless its server is marked `"trusted"`.

## MCP servers

Beyond the hand-written tools above, the agent can call tools from any
[MCP](https://modelcontextprotocol.io/) server you configure. Copy
`agent/mcp_servers.example.json` to `agent/mcp_servers.json` (gitignored)
and list servers under `mcpServers`:

```json
{
  "mcpServers": {
    "git": {
      "transport": "stdio",
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "{project_dir}"],
      "trusted": false
    }
  }
}
```

- `{project_dir}` in `args` is substituted with the agent's sandboxed
  project directory at startup — the same directory `read_file`/
  `write_file`/`run_command` are confined to.
- `trusted` (default `false`) is our own field, not part of MCP — every
  tool from a non-trusted server pauses for approval, same `interrupt()`
  mechanism and same `ApprovalCard`/`Allow? [y/N]` prompt as `write_file`
  and dangerous `run_command`s. Set it to `true` per server once you trust
  it, to skip the pause.
- No config file → zero MCP tools, agent behaves exactly as it did before
  MCP support existed. Fully optional.
- Each MCP tool call opens a fresh session (a fresh subprocess, for
  `stdio` servers like the git one above) — this is `langchain-mcp-adapters`'
  documented default behavior, not a shortcut. It costs a bit of latency per
  call in exchange for a much simpler implementation (the rest of the app —
  `agent_graph.py`, `server.py`, `dev_agent.py` — stays fully synchronous,
  with no changes needed to support this).

## Future goals

theBee is as much a **learning project** as it is a tool — the point is to
build enough of an agent stack by hand to actually understand how the
pieces fit together, not just consume a framework's abstractions. Planned
directions:

- **Dissect how AI agents actually work.** Keep the graph hand-written
  (rather than reaching for `create_react_agent`) so every part of the
  agent ⇄ tools loop — state, edges, conditional routing, checkpointing,
  interrupts/resume — stays visible and hackable. Use this as a base for
  experimenting with different loop shapes (e.g. planner/executor split,
  reflection steps, multi-turn self-critique) and seeing how each changes
  behavior.
- **Dissect how the underlying models work.** Go beyond treating the LLM
  as a black box: study how each registered model (open-weight ones via
  Ollama Cloud/Groq/OpenRouter, and Gemini/Claude) actually consumes the
  system prompt, message history, and tool schemas — context window
  pressure, why models sometimes emit a tool call as text instead of
  calling it, how model size/quantization affect tool-calling reliability,
  and how much of "agentic" behavior is really just prompting discipline
  vs. model capability. The side-by-side picker makes this comparison easy
  to run directly.
- **MCP (Model Context Protocol) integration — done, and growing.** The
  agent now discovers and calls tools from any configured MCP server (see
  MCP servers above), starting with the git server, via
  `langchain-mcp-adapters` — a good concrete look at how MCP's
  discovery/schema/invocation handshake compares to the hand-written
  `@tool` approach used everywhere else in `tools/`. Currently every MCP
  call opens a fresh session per invocation (simple, but adds latency);
  a natural next step is a persistent-session mode for servers under
  heavy use, which would require converting the sync execution model to
  async end-to-end. Longer term: expose theBee's own tools *as* an MCP
  server, so other agents/hosts (e.g. Claude Code) could call into it.
- **Multi-agent orchestration.** Experiment with splitting today's single
  agent into cooperating sub-agents (e.g. a planner, a coder, a reviewer)
  and compare that against the current single-graph approach — same
  motivation as LangGraph's own multi-agent patterns, but built from
  scratch here to understand the trade-offs first-hand.
- **Persistent memory.** Swap `MemorySaver` (in-memory, lost on restart)
  for a durable checkpointer (SQLite/Postgres) so sessions and long-term
  project context survive restarts, and explore longer-term memory
  (e.g. a project knowledge base built up over many sessions, beyond the
  one-shot `AGENT.md`).
- **Broader tool + model support.** Ollama Cloud, Gemini, Groq, OpenRouter,
  and Claude are all available side-by-side via the registry in
  `agent/models.py` — useful for comparing how agent reliability (tool-call
  correctness especially) changes across models and providers, at little
  to no cost. Next up: locally-run GGUF models for a true zero-signup
  option again, plus more sandboxed tools (structured diffs/patches instead
  of whole-file overwrites, test-runner-aware feedback loops, git-aware
  operations).
- **Evaluation.** Some way to systematically test agent behavior across
  models/prompts/graph shapes (does it call tools when it should? does it
  correctly refuse unsafe commands? does it search when it should?) rather
  than relying on manual spot-checking.

## Notes & limits

- Every model backend is now a cloud API call (Ollama Cloud included) — the
  earlier "nothing leaves the machine" local-only setup has been replaced by
  the multi-provider picker above. Sandboxing of file/command tools to the
  target project directory is unaffected either way.
- Shell commands time out after 60 seconds; file reads/command output are
  truncated (20k / 8k characters respectively) to keep context manageable.
- Conversation history and pending approvals live in memory
  (`MemorySaver`) — restarting the backend or CLI clears all sessions.
