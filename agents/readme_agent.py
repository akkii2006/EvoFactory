"""
readme_agent.py
----------------
Generates a polished README.md for the finished project.
"""

SYSTEM_PROMPT = (
    "You are a technical writer who writes clear, professional README files "
    "for software projects. You respond with raw markdown only — no JSON, "
    "no surrounding code fences for the document as a whole."
)


def generate_readme(client, idea, language, files, run_command, setup_commands):
    file_list = "\n".join(f"- `{name}`" for name in files.keys())
    setup_str = ", ".join(setup_commands or []) or "None"

    prompt = f"""Write a complete README.md for this project.

Project Title: {idea['title']}
Description: {idea['description']}
Language: {language}
Key Features:
{chr(10).join(f"- {f}" for f in idea.get('key_features', []))}

Files in the project:
{file_list}

Setup commands: {setup_str}
Run command: {run_command}

Write the README with these sections:
1. Title (as an H1)
2. A short, engaging description (2-3 sentences max)
3. "## Features" - bullet list
4. "## Setup" - how to install dependencies
5. "## Usage" - how to run it
6. "## License" - MIT License (just mention it's MIT licensed)

Keep the whole thing short and to the point - no filler, no repeated information.
Do not use em dashes anywhere (the character that looks like a long hyphen, "—"). Use a period, comma, or "and"/"but" instead. Do not use emojis anywhere.

Respond with ONLY the raw markdown content of the README. Do not wrap the whole thing in code fences.
"""

    text = client.generate(prompt, system_instruction=SYSTEM_PROMPT, temperature=0.5)
    return _strip_outer_fences(text)


def _strip_outer_fences(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip() + "\n"
