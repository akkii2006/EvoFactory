"""
pipeline.py
-----------
Builds the project. Testing has been removed for now: the AI generates the
project and it's written straight to disk, no automated test/run step.
"""

import os
import shutil

from agents import builder_agent


def run_build(client, idea, language, project_dir, complexity="simple"):
    """
    Builds the project and writes it to project_dir. Returns the build_result
    dict (files, setup_commands, run_command).
    """
    os.makedirs(project_dir, exist_ok=True)

    print("\nBuilding project...")
    build_result = builder_agent.build_project(client, idea, language, complexity)

    _write_files(project_dir, build_result.get("files", {}))

    print("Build complete.")
    return build_result


def _write_files(project_dir, files):
    """Writes the files dict {relative_path: content} to disk, overwriting old contents."""
    # Clean out everything from a previous attempt (but keep .git if it exists)
    for entry in os.listdir(project_dir):
        if entry == ".git":
            continue
        full = os.path.join(project_dir, entry)
        if os.path.isdir(full):
            shutil.rmtree(full, ignore_errors=True)
        else:
            try:
                os.remove(full)
            except OSError:
                pass

    for relative_path, content in files.items():
        # Normalize and prevent path escapes
        safe_path = os.path.normpath(relative_path).lstrip(os.sep)
        full_path = os.path.join(project_dir, safe_path)

        parent = os.path.dirname(full_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
