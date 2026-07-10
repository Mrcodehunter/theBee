"""search_tools.py — web_search, backed by DuckDuckGo (no API key needed)."""

from langchain_core.tools import tool

MAX_RESULTS_CAP = 10


def build_web_search_tool():
    @tool
    def web_search(query: str, max_results: int = 5) -> str:
        """Search the web (DuckDuckGo) and return titles, URLs, and snippets.
        Use this to find current information or discover URLs to browse_page.
        Keep `max_results` small (default 5, capped at 10)."""
        try:
            from ddgs import DDGS

            n = max(1, min(max_results, MAX_RESULTS_CAP))
            results = DDGS().text(query, max_results=n)
            if not results:
                return f"No results found for: {query}"

            lines = []
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. {r.get('title', '(no title)')}\n   {r.get('href', '')}\n   {r.get('body', '')}")
            return "\n\n".join(lines)
        except Exception as e:
            return f"ERROR searching for '{query}': {e}"

    return web_search
