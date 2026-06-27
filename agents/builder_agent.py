"""
builder_agent.py
-----------------
Given an approved project idea, generates a complete set of project files,
plus the commands needed to set up and run the project.
"""

SYSTEM_PROMPT = (
    "You are an expert software engineer. You write complete, working, "
    "self-contained projects. You always respond with valid JSON only — "
    "no markdown, no commentary, no placeholders or TODOs in the code."
)


COMPLEXITY_GUIDANCE = {
    "simple": "Keep the project very small: 2 to 4 files total (e.g. one main file and a "
              "requirements file if needed). Minimal structure, no subfolders.",
    "medium": "Build a moderately sized project: around 5 to 7 files. Split logic into a "
              "couple of modules (e.g. core logic, helpers/utilities, a CLI or entry point), "
              "plus a requirements file.",
    "complex": "Build a more complete, multi-module project: around 8 to 12 files. Use a small "
               "package structure (e.g. a package directory with multiple modules for distinct "
               "concerns such as core logic, data models, utilities, CLI/entry point, and "
               "configuration), plus a requirements file.",
}


def build_project(client, idea, language, complexity="simple"):
    complexity_text = COMPLEXITY_GUIDANCE.get(complexity, COMPLEXITY_GUIDANCE["simple"])

    prompt = f"""Build a complete, working {language} project for this idea:

Title: {idea['title']}
Description: {idea['description']}
Key Features: {", ".join(idea.get('key_features', []))}

Project size/complexity target: {complexity_text}

Respond with ONLY a JSON object in this exact format:
{{
  "files": {{
    "relative/path/to/file1.ext": "full file contents as a string",
    "relative/path/to/file2.ext": "full file contents as a string"
  }},
  "setup_commands": ["list of shell commands to install dependencies, e.g. pip install -r requirements.txt"],
  "run_command": "the command to run the project, e.g. python main.py"
}}

Requirements:
- Code must be complete and runnable — no placeholders, no "TODO: implement this".
- Follow the project size/complexity target given above for the number of files and structure.
- If the language is Python, include a requirements.txt (even if it's just an empty file / minimal deps).
- All file contents must be valid strings, with newlines escaped as \\n (this must be valid JSON).
- Never compare a string to an empty triple-quoted literal (e.g. `!= """"""`). For empty-string
  checks, always use `== ""`, `!= ""`, or `if not value:`. Be very careful with quote counts in
  triple-quoted strings — miscounted quotes cause syntax errors.
- Any string literal that spans multiple lines, or contains a literal newline character, MUST use
  triple quotes (\"\"\"...\"\"\" or '''...'''). A single-quoted string (\"...\" or '...') can never
  contain a real line break.
- Do not use em dashes anywhere in code, comments, docstrings, or output strings (the character
  that looks like a long hyphen, "—"). Use a period, comma, or "and"/"but" instead.
- Do not use emojis anywhere in code, comments, docstrings, or output strings.
- "setup_commands" should only install dependencies (e.g. "pip install -r requirements.txt").
  Do NOT include commands like "mkdir ..." — any directories needed for paths in "files" are
  created automatically.
- Do not include a README — that is generated separately.
"""

    return client.generate_json(prompt, system_instruction=SYSTEM_PROMPT, temperature=0.3)
