"""
idea_agent.py
-------------
Generates a single, simple, buildable project idea given a genre/category
and a programming language. Avoids repeating ideas the user has already
rejected.
"""

SYSTEM_PROMPT = (
    "You are a creative software project idea generator. You come up with "
    "small, buildable, interesting project ideas. You always respond with "
    "valid JSON only — no markdown, no commentary."
)


def generate_idea(client, genre, language, rejected_ideas=None, existing_repos=None, extra_unique=False):
    rejected_text = ""
    if rejected_ideas:
        rejected_list = "\n".join(f"- {title}" for title in rejected_ideas)
        rejected_text = (
            "\nThe user has already rejected these ideas — do NOT suggest "
            f"anything similar to them again:\n{rejected_list}\n"
        )

    existing_repos_text = ""
    if existing_repos:
        repo_list = "\n".join(f"- {name}" for name in existing_repos)
        existing_repos_text = (
            "\nThe user already has these GitHub repositories. Do NOT suggest an idea that is "
            "the same as, a clone of, or very close in concept to any of these:\n"
            f"{repo_list}\n"
        )

    uniqueness_text = ""
    temperature = 0.9
    if extra_unique:
        temperature = 1.1
        uniqueness_text = """
The user explicitly wants a HIGHLY UNIQUE, CREATIVE idea. Try really, really hard here.
- Absolutely avoid common/overdone project types: to-do apps, calculators, weather apps,
  chatbots, note apps, expense trackers, password managers, URL shorteners, quote generators,
  pomodoro timers, file organizers, basic web scrapers, simple games like tic-tac-toe or snake.
- Think of unusual angles, niche but genuinely useful tools, surprising combinations of two
  domains, or a clever twist on how something is normally done.
- The goal is for the user to react with "oh, that's actually cool, I haven't seen that before."
- It is fine if the idea is a bit unconventional, as long as it is still buildable as a small
  project in the given language.
"""

    prompt = f"""Generate ONE simple, buildable software project idea.

Genre/Category: {genre}
Programming Language: {language}
{rejected_text}{existing_repos_text}{uniqueness_text}
Respond with ONLY a JSON object in this exact format:
{{
  "title": "Project Title",
  "description": "1-2 short sentences describing what the project does. This will also be used as the GitHub repo description, so keep it concise (under 150 characters).",
  "key_features": ["feature 1", "feature 2", "feature 3"],
  "repo_name": "TwoWordsJoined"
}}

Guidelines:
- The project should be small enough to fit in a handful of files and be built/tested quickly.
- Keep "description" short and to the point (1-2 sentences, under 150 characters). It is used
  directly as the GitHub repository description, so avoid long or flowery wording.
- Avoid generic, overdone ideas (basic to-do list, basic calculator, basic weather app) unless given a genuinely interesting twist.
- "repo_name" must be exactly two words joined directly together with no separator at all
  (no hyphens, no underscores, no spaces). Each word should start with a capital letter,
  e.g. "EvoMind", "SuperCool", "PixelForge". It must be a valid GitHub repository name
  (letters and numbers only).
- Do not use em dashes anywhere (the character that looks like a long hyphen, "—"). Do not use emojis.
"""

    return client.generate_json(prompt, system_instruction=SYSTEM_PROMPT, temperature=temperature)
