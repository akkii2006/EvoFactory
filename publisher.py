"""
publisher.py
------------
Handles creating a GitHub repository via the API and pushing the local
project to it via git.
"""

import subprocess
import requests

GITHUB_API = "https://api.github.com"


def get_github_username(token):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    response = requests.get(f"{GITHUB_API}/user", headers=headers, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch GitHub user info ({response.status_code}): {response.text}")
    return response.json()["login"]


def list_repo_names(token, max_repos=300):
    """Returns a list of repo names (not full paths) owned by the authenticated user."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    names = []
    page = 1
    while len(names) < max_repos:
        response = requests.get(
            f"{GITHUB_API}/user/repos",
            headers=headers,
            params={"per_page": 100, "page": page, "affiliation": "owner"},
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Failed to list GitHub repos ({response.status_code}): {response.text}")
        batch = response.json()
        if not batch:
            break
        names.extend(repo["name"] for repo in batch)
        if len(batch) < 100:
            break
        page += 1
    return names


def create_github_repo(token, repo_name, description, private=False):
    """Creates a new repo under the authenticated user's account."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {
        "name": repo_name,
        "description": description[:200] if description else "",
        "private": private,
        "auto_init": False,
    }

    response = requests.post(f"{GITHUB_API}/user/repos", json=payload, headers=headers, timeout=30)

    if response.status_code == 201:
        data = response.json()
        return {
            "html_url": data["html_url"],
            "clone_url": data["clone_url"],
            "owner": data["owner"]["login"],
        }

    if response.status_code == 422:
        raise RuntimeError(
            f"GitHub rejected repo creation — a repo named '{repo_name}' may already exist "
            f"on your account, or the name is invalid.\nDetails: {response.text}"
        )

    raise RuntimeError(f"Failed to create GitHub repo ({response.status_code}): {response.text}")


def push_project(project_dir, token, username, clone_url, commit_message="Initial commit by EvoFactory"):
    """Initializes git (if needed), commits everything, and pushes to the new repo."""

    def run(cmd):
        result = subprocess.run(cmd, shell=True, cwd=project_dir, capture_output=True, text=True)
        return result

    # Embed the token in the remote URL for authentication
    if clone_url.startswith("https://"):
        auth_url = clone_url.replace("https://", f"https://{username}:{token}@", 1)
    else:
        raise RuntimeError(f"Unexpected clone URL format: {clone_url}")

    steps = [
        "git init",
        'git config user.name "EvoFactory"',
        'git config user.email "evofactory@local"',
        "git add -A",
        f'git commit -m "{commit_message}"',
        "git branch -M main",
    ]

    for cmd in steps:
        res = run(cmd)
        # "nothing to commit" on a re-run isn't fatal
        if res.returncode != 0 and "nothing to commit" not in res.stdout.lower():
            raise RuntimeError(f"Command failed: {cmd}\n{res.stderr or res.stdout}")

    # Set / replace the remote
    run("git remote remove origin")  # ignore failure if it doesn't exist
    res = run(f"git remote add origin {auth_url}")
    if res.returncode != 0:
        raise RuntimeError(f"Failed to set remote: {res.stderr}")

    res = run("git push -u origin main")
    if res.returncode != 0:
        raise RuntimeError(f"Failed to push to GitHub: {res.stderr or res.stdout}")

    return True
