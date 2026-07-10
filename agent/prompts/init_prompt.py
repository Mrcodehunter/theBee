"""init_prompt.py — the one-off task that audits a project and writes AGENT.md
(the CLI's 'init' command, mirroring Claude Code's /init)."""

INIT_TASK = """Audit this project and create an AGENT.md file at the project root.

Follow these steps exactly:
1. Use run_command to list the files (on Windows use: dir /s /b — on
   Linux/Mac use: find . -type f). Ignore folders like .git, venv,
   node_modules, __pycache__.
2. Use read_file on the most important files: the main entry point,
   README if present, and dependency files (requirements.txt,
   package.json, pyproject.toml).
3. Then use write_file to create AGENT.md with these sections:
   # Project Overview  (2-3 sentences: what this project does)
   ## Tech Stack       (languages, frameworks, key dependencies)
   ## Structure        (what the important files/folders are for)
   ## Conventions      (naming, style patterns you observed)
   ## How to Run & Test (the commands, if you can determine them)

Keep AGENT.md under 60 lines. Only state what you actually observed
in the files — do not invent details."""
