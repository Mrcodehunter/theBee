"""image_tools.py — analyze_image tool, sandboxed to the project directory.

Always uses a fixed vision-capable model (see models.get_vision_model_id())
rather than whatever model the user is chatting with, so image analysis
works even when the active conversation model can't see images at all.
"""

import base64
from pathlib import Path
from typing import Callable

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from models import build_llm, get_vision_model_id

# Extension -> MIME type. Also imported by server.py's upload endpoint so
# the web UI's file-picker validation and this tool's own check never drift.
SUPPORTED_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

_DEFAULT_PROMPT = """Look at this image carefully and describe it in detail.
If it depicts an event, scene, or occasion, extract as much of the
following as the image actually shows evidence for (don't guess at
anything it doesn't support):

- What is happening / what kind of event or scene this is
- Who — people, subjects, roles visible
- When — any date/time cues (visible dates, season, time of day, lighting)
- Where — location cues (venue type, setting, signage, geography)
- Why — the apparent purpose or occasion
- How — the activity, method, or process depicted
- Any visible text (signs, banners, captions) — quote it exactly
- Other notable visual details (mood, composition, notable objects)

Be concrete and specific. If something isn't determinable from the image,
say so rather than inventing it."""


def build_analyze_image_tool(safe_path: Callable[[str], Path]):
    @tool
    def analyze_image(path: str, focus: str = "") -> str:
        """Look at an image file and describe what it shows. `path` is
        relative to the project directory. Works well with no other
        argument — it extracts a thorough description (what/who/when/
        where/why/how) by default. Use `focus` to ask about something
        specific (e.g. "identify the venue") in addition to the default
        extraction."""
        try:
            p = safe_path(path)
        except Exception as e:
            return f"ERROR reading '{path}': {e}"

        mime_type = SUPPORTED_IMAGE_TYPES.get(p.suffix.lower())
        if mime_type is None:
            return f"ERROR: unsupported image type '{p.suffix}'. Supported: {', '.join(SUPPORTED_IMAGE_TYPES)}"

        model_id = get_vision_model_id()
        if model_id is None:
            return (
                "ERROR: no vision-capable model is configured. Set "
                "ANTHROPIC_API_KEY or GOOGLE_API_KEY to enable image analysis."
            )

        try:
            data = p.read_bytes()
        except Exception as e:
            return f"ERROR reading '{path}': {e}"

        b64 = base64.standard_b64encode(data).decode("utf-8")
        prompt = _DEFAULT_PROMPT + (f"\n\nAdditional focus: {focus}" if focus else "")

        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image", "source_type": "base64", "data": b64, "mime_type": mime_type},
        ])

        try:
            llm = build_llm(model_id)
            response = llm.invoke([message])
            return response.text
        except Exception as e:
            return f"ERROR analyzing '{path}': {e}"

    return analyze_image
