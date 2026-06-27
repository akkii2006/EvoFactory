"""
config.py
---------
Handles loading the Gemini API key and GitHub token from a local .env file,
prompting the user for them if they're missing, and optionally saving them
for future runs.
"""

import os
import getpass
from dotenv import load_dotenv, set_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")


def load_config():
    """Load config values, prompting the user for any that are missing."""
    load_dotenv(ENV_PATH)

    gemini_key = os.getenv("GEMINI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")

    if not gemini_key:
        print("\nNo Gemini API key found.")
        gemini_key = getpass.getpass("Enter your Gemini API key: ").strip()
        _maybe_persist("GEMINI_API_KEY", gemini_key)

    if not github_token:
        print("\nNo GitHub token found.")
        print("(Needs a Personal Access Token with 'repo' scope: "
              "https://github.com/settings/tokens)")
        github_token = getpass.getpass("Enter your GitHub personal access token: ").strip()
        _maybe_persist("GITHUB_TOKEN", github_token)

    if not gemini_key or not github_token:
        raise SystemExit("Both a Gemini API key and a GitHub token are required to continue.")

    return {
        "gemini_api_key": gemini_key,
        "github_token": github_token,
    }


def _maybe_persist(key_name, value):
    save = input(f"Save {key_name} to .env for future runs? (y/n): ").strip().lower()
    if save == "y":
        if not os.path.exists(ENV_PATH):
            open(ENV_PATH, "a").close()
        set_key(ENV_PATH, key_name, value)
        print(f"Saved {key_name} to {ENV_PATH}")
