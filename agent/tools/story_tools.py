"""story_tools.py — list_story_templates tool."""

from langchain_core.tools import tool

from prompts import (
    FORMAL_SUMMARY_TEMPLATE,
    NARRATIVE_STORY_TEMPLATE,
    NEWS_REPORT_TEMPLATE,
)


def build_list_story_templates_tool():
    @tool
    def list_story_templates() -> str:
        """Optional structural starting points for writing up extracted
        details (e.g. from analyze_image) as a story or report. These are
        not a fixed menu — use one as-is, combine/modify elements from
        several, or ignore them entirely and write your own structure if
        that fits the image or context better. Calling this tool is itself
        optional; skip it if you already know how you want to write the
        result up."""
        return "\n\n".join([
            f"## {name}\n{template}"
            for name, template in [
                ("News Report", NEWS_REPORT_TEMPLATE),
                ("Narrative Story", NARRATIVE_STORY_TEMPLATE),
                ("Formal Event Summary", FORMAL_SUMMARY_TEMPLATE),
            ]
        ])

    return list_story_templates
