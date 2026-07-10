"""browse_tools.py — browse_page (fetch + read one URL) and compare_pages
(fetch several URLs side by side), for live web browsing."""

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

REQUEST_TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 DevAgent/1.0"
)


def _fetch_readable_text(url: str, max_chars: int) -> str:
    """Fetch a URL and return its main text content, stripped of markup.
    Raises on network/HTTP errors; caller turns those into a tool-friendly string."""
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    if "html" not in content_type and "text" not in content_type:
        return f"[non-text content: {content_type}]"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[...truncated...]"
    return text


def build_browse_page_tool():
    @tool
    def browse_page(url: str) -> str:
        """Fetch a web page and return its readable text content (markup
        stripped). Use this to read an article, docs page, or any URL you
        found via web_search."""
        try:
            return _fetch_readable_text(url, max_chars=8_000)
        except Exception as e:
            return f"ERROR fetching '{url}': {e}"

    return browse_page


def build_compare_pages_tool():
    @tool
    def compare_pages(urls: list[str]) -> str:
        """Fetch 2-5 URLs and return their readable text content side by
        side, each labeled with its URL, so you can compare/contrast them
        (e.g. pricing, features, claims across sources) in one pass."""
        if len(urls) < 2:
            return "ERROR: give at least 2 URLs to compare."
        if len(urls) > 5:
            return "ERROR: at most 5 URLs at a time, to keep the comparison focused."

        per_page_budget = 4_000
        sections = []
        for url in urls:
            try:
                text = _fetch_readable_text(url, max_chars=per_page_budget)
            except Exception as e:
                text = f"ERROR fetching this URL: {e}"
            sections.append(f"=== {url} ===\n{text}")

        return "\n\n".join(sections)

    return compare_pages
