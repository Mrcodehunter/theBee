"""prompts/ — all static prompt text, one file per prompt."""

from .init_prompt import INIT_TASK
from .story_templates import (
    FORMAL_SUMMARY_TEMPLATE,
    NARRATIVE_STORY_TEMPLATE,
    NEWS_REPORT_TEMPLATE,
)
from .system_prompt import build_system_prompt

__all__ = [
    "build_system_prompt",
    "INIT_TASK",
    "NEWS_REPORT_TEMPLATE",
    "NARRATIVE_STORY_TEMPLATE",
    "FORMAL_SUMMARY_TEMPLATE",
]
