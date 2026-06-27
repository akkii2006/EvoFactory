"""
EvoFactory
==========
An autonomous pipeline that:
  1. Asks you for a genre, language, complexity, and testing strictness
  2. Generates one or more project ideas (Gemini)
  3. Builds each project (Gemini)
  4. Tests it for real (subprocess), looping back to the builder on failure
  5. Generates a README (Gemini)
  6. Creates a GitHub repo and pushes the project (GitHub API + git)

Supports a batch mode: type "batch <number>" (2-30) to generate and process
that many projects in one run, with all ideas chosen by the AI.

Run with:  python main.py
"""

import os
import sys

from config import load_config
from gemini_client import GeminiClient
from agents import idea_agent, readme_agent
from pipeline import run_build
import publisher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")


def banner():
    print("=" * 56)
    print("   EvoFactory - Autonomous Project Generator")
    print("   idea -> build -> test -> README -> GitHub push")
    print("=" * 56)


def get_repo_name(idea):
    return idea.get("repo_name") or "".join(word.capitalize() for word in idea["title"].split())


def ask_complexity():
    print(
        "\nHow complex should the project(s) be?\n"
        "  [simple]  - a few files\n"
        "  [med]     - around 5 files\n"
        "  [complex] - around 10 files, multi-module\n"
    )
    while True:
        choice = input("> ").strip().lower()
        if choice in ("simple", "s"):
            return "simple"
        if choice in ("med", "medium", "m"):
            return "medium"
        if choice in ("complex", "c"):
            return "complex"
        print("Please enter 'simple', 'med', or 'complex'.")


def ask_run_count():
    print(
        "\nHow many projects do you want to generate?\n"
        "  Press Enter (or type 'single') for one project.\n"
        "  Type 'batch <number>' (2-30) to generate that many automatically.\n"
        "  All batch ideas are chosen by the AI.\n"
    )
    while True:
        choice = input("> ").strip().lower()
        if choice in ("", "single", "1"):
            return 1
        parts = choice.split()
        if parts and parts[0] == "batch" and len(parts) == 2 and parts[1].isdigit():
            n = int(parts[1])
            if 2 <= n <= 30:
                return n
        if choice.isdigit():
            n = int(choice)
            if n == 1:
                return 1
            if 2 <= n <= 30:
                return n
        print("Please type 'single', or 'batch <number>' with a number from 2 to 30.")


def ask_extra_unique():
    return input(
        "\nTry extra hard for unique, non-generic idea(s)? (y/n): "
    ).strip().lower() == "y"


def generate_ai_idea(client, genre, language, rejected_titles, existing_repos, extra_unique, auto_confirm):
    """Generates an idea, optionally looping until the user approves it."""
    while True:
        print("\nGenerating an idea...")
        idea = idea_agent.generate_idea(
            client, genre, language, rejected_titles, existing_repos, extra_unique=extra_unique
        )

        print(f"\nIdea: {idea['title']}")
        print(f"   {idea['description']}")
        if idea.get("key_features"):
            print("   Features:")
            for feat in idea["key_features"]:
                print(f"     - {feat}")
        print(f"   Repo name: {idea.get('repo_name')}")

        if auto_confirm:
            return idea

        confirm = input("\nUse this idea? (y = build it / n = try another): ").strip().lower()
        if confirm == "y":
            return idea

        rejected_titles.append(idea["title"])


def ask_idea_source(client, genre, language, existing_repos):
    """Returns an idea dict, either user-supplied or AI-generated + approved."""
    choice = input(
        "\nWho should come up with the project idea?\n"
        "  [me] - I'll describe it myself\n"
        "  [ai] - Let the AI decide\n"
        "> "
    ).strip().lower()

    if choice in ("me", "mine", "myself", "user"):
        print("\nDescribe your project idea:")
        title = input("  Title: ").strip()
        description = input("  Description: ").strip()
        features_raw = input("  Key features (comma-separated): ").strip()
        repo_name = input("  Repo name (two words joined, e.g. EvoMind, SuperCool): ").strip()
        return {
            "title": title,
            "description": description,
            "key_features": [f.strip() for f in features_raw.split(",") if f.strip()],
            "repo_name": repo_name,
        }

    extra_unique = ask_extra_unique()
    return generate_ai_idea(client, genre, language, [], existing_repos, extra_unique, auto_confirm=False)


def run_project_pipeline(client, config, idea, language, complexity, repo_name, push_mode):
    """
    push_mode: "ask" to prompt the user, or True/False to decide automatically
    (used in batch mode). Returns True once the project has been built and
    its README written, regardless of whether it was pushed.
    """
    project_dir = os.path.join(WORKSPACE_DIR, repo_name)
    print(f"\nProject will be built in: {project_dir}")

    build_result = run_build(client, idea, language, project_dir, complexity=complexity)

    print("\nGenerating README...")
    readme_content = readme_agent.generate_readme(
        client,
        idea,
        language,
        build_result.get("files", {}),
        build_result.get("run_command"),
        build_result.get("setup_commands"),
    )
    with open(os.path.join(project_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("   README.md written.")

    if push_mode == "ask":
        do_push = input(f"\nCreate a GitHub repo '{repo_name}' and push this project now? (y/n): ").strip().lower() == "y"
    else:
        do_push = bool(push_mode)

    if do_push:
        try:
            print("\nCreating GitHub repo and pushing...")
            repo_info = publisher.create_github_repo(
                config["github_token"], repo_name, idea.get("description", "")
            )
            publisher.push_project(
                project_dir,
                config["github_token"],
                repo_info["owner"],
                repo_info["clone_url"],
            )
            print(f"\nDone! Repo is live at: {repo_info['html_url']}")
        except Exception as e:
            print(f"\nFailed to publish to GitHub: {e}")
            print(f"   Your project is still saved locally at: {project_dir}")
    else:
        print(f"\nProject saved locally at: {project_dir}")

    return True


def main():
    banner()

    try:
        config = load_config()
    except SystemExit as e:
        print(f"\n{e}")
        sys.exit(1)

    client = GeminiClient(api_key=config["gemini_api_key"])

    print("\nFetching your existing GitHub repos to avoid duplicate ideas...")
    try:
        existing_repos = publisher.list_repo_names(config["github_token"])
        print(f"Found {len(existing_repos)} existing repo(s).")
    except Exception as e:
        print(f"Could not fetch existing repos ({e}). Continuing without this check.")
        existing_repos = []

    genre = input("\nWhat genre/category? (e.g. AI tools, automation, games, web): ").strip()
    language = input("What programming language? (e.g. Python, JavaScript): ").strip()
    complexity = ask_complexity()
    num_projects = ask_run_count()

    if num_projects == 1:
        idea = ask_idea_source(client, genre, language, existing_repos)
        repo_name = get_repo_name(idea)
        run_project_pipeline(client, config, idea, language, complexity, repo_name, push_mode="ask")
        print("\nEvoFactory run complete.")
        return

    # Batch mode: all ideas chosen by the AI
    extra_unique = ask_extra_unique()
    auto_push = input(
        f"\nAutomatically create GitHub repos and push all {num_projects} projects when done with each? (y/n): "
    ).strip().lower() == "y"

    rejected_titles = []

    for i in range(num_projects):
        print(f"\n{'=' * 56}")
        print(f"  Project {i + 1}/{num_projects}")
        print("=" * 56)

        while True:
            idea = generate_ai_idea(
                client, genre, language, rejected_titles, existing_repos, extra_unique, auto_confirm=True
            )
            repo_name = get_repo_name(idea)
            if repo_name not in existing_repos:
                break
            print(f"Repo name '{repo_name}' collides with an existing repo, regenerating idea...")
            rejected_titles.append(idea["title"])

        rejected_titles.append(idea["title"])
        existing_repos.append(repo_name)

        run_project_pipeline(client, config, idea, language, complexity, repo_name, push_mode=auto_push)

    print(f"\nBatch complete: {num_projects} project(s) processed.")


if __name__ == "__main__":
    main()
