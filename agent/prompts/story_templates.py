"""story_templates.py — structural skeletons for writing up extracted
details (e.g. from analyze_image) as a story/report. These are guidance on
structure and tone, not literal placeholders to fill in mechanically —
the model should pick, combine, or adapt them in its own words."""

NEWS_REPORT_TEMPLATE = """- Headline: one line, states the core fact
- Lede: the who/what/when/where in 1-2 sentences up front
- Body: why it happened and how it unfolded, most important details first
- Closing: any notable quote-worthy detail or forward-looking note
Tone: factual, concise, inverted-pyramid (most important information first)."""

NARRATIVE_STORY_TEMPLATE = """- Opening: set the scene — where and when, establish atmosphere
- Rising detail: introduce who is involved and what is happening, in order
- Turning point or highlight: the most interesting or significant moment
- Closing: how it concluded or what it left behind
Tone: descriptive and engaging, chronological, written to be read for
enjoyment rather than to convey facts as fast as possible."""

FORMAL_SUMMARY_TEMPLATE = """- Event:
- Date/Time:
- Location:
- Participants:
- Purpose:
- Key Details:
- Notes:
Tone: structured and factual, one clause per line, no embellishment —
leave a field out entirely if the source material has no evidence for it
rather than guessing."""
