# EvoFactory

An autonomous pipeline that goes from a project idea to a pushed GitHub repo with minimal input. It uses Google Gemini to generate code and a README, then publishes directly to your GitHub account.

**GitHub:** [akkii2006/EvoFactory](https://github.com/akkii2006/EvoFactory)

## How it works

```
idea -> build -> README -> create GitHub repo -> git push
```

You pick a genre, language, and complexity level. Either you describe the idea or the AI generates one for you. EvoFactory builds the project, writes a README, and optionally pushes it to GitHub.

Batch mode lets you generate 2 to 30 projects in one run, with all ideas chosen by the AI.

## Setup

```bash
pip install -r requirements.txt
```

You need:
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- A GitHub Personal Access Token (classic) with the `repo` scope from [github.com/settings/tokens](https://github.com/settings/tokens)

Either add these to a `.env` file, or just run the script and it will prompt you and offer to save them.

## Usage

```bash
python main.py
```

You will be asked for a genre, language, complexity (`simple` / `med` / `complex`), and how many projects to generate. For a single project you can describe the idea yourself or let the AI pick one (with approve/reject). In batch mode all ideas are AI-generated automatically.

Generated projects are saved under `workspace/<RepoName>/`.

## Project layout

```
EvoFactory/
├── main.py              # entry point
├── config.py            # loads API keys
├── gemini_client.py     # Gemini API wrapper
├── pipeline.py          # build pipeline
├── publisher.py         # GitHub repo creation and git push
└── agents/
    ├── idea_agent.py    # generates project ideas
    ├── builder_agent.py # generates project files
    ├── tester_agent.py  # runs and validates generated code
    └── readme_agent.py  # writes the project README
```

## Notes

- Each project is `git init`'d independently inside `workspace/` and pushed as its own repo.
- `gemini-2.5-flash-lite` is fast and cheap, but occasionally wraps JSON output in markdown fences. The client retries and strips these automatically.
- The tester agent (`tester_agent.py`) is fully implemented and catches syntax errors, failed setup commands, and runtime crashes. It is not yet wired into the main pipeline.
