"""
tester_agent.py
----------------
Actually executes the generated project: runs setup commands, then runs
the test command (or falls back to the run command), and checks whether
it succeeded.

This is intentionally code-based (subprocess) rather than another "AI says
it looks fine" check, since real execution is the only reliable signal.
"""

import os
import ast
import subprocess

SETUP_TIMEOUT = 180
RUN_TIMEOUT = 60
BASIC_RUN_TIMEOUT = 20


def _run(command, cwd, timeout):
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "command": command,
            "returncode": None,
            "stdout": (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
            "stderr": (e.stderr or b"").decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or ""),
            "timed_out": True,
        }


def check_python_syntax(project_dir):
    """
    Quickly compiles every .py file in the project to catch syntax errors
    before bothering to install dependencies / run anything. Returns a list
    of human-readable error strings (empty if everything compiles).
    """
    errors = []
    for root, dirs, filenames in os.walk(project_dir):
        if ".git" in dirs:
            dirs.remove(".git")
        for name in filenames:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, project_dir)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    source = f.read()
                ast.parse(source, filename=rel)
            except SyntaxError as e:
                lines = source.splitlines()
                lineno = e.lineno or 1
                start = max(0, lineno - 4)
                end = min(len(lines), lineno + 1)
                context = "\n".join(
                    f"    {i + 1}: {lines[i]}" for i in range(start, end)
                )
                errors.append(
                    f"{rel}: line {lineno}: {e.msg}\n"
                    f"  Context (the error is often a few lines ABOVE the reported line, "
                    f"e.g. an unclosed string that started earlier):\n{context}"
                )
    return errors


def test_project(project_dir, setup_commands, test_command, run_command, thorough=True):
    """
    Returns a dict:
      {
        "success": bool,
        "reason": str,
        "logs": [ {command, returncode, stdout, stderr, timed_out}, ... ]
      }

    If thorough=True, runs test_command (falling back to run_command) and
    requires it to exit cleanly (the usual full test-suite behavior).

    If thorough=False, this is a "basic" check: just confirm the project has
    valid syntax and that run_command starts up without crashing. A timeout
    with no traceback is treated as success (e.g. a server or interactive
    program that's still running happily).
    """
    logs = []

    # 0. Fast syntax check first — catches malformed code (e.g. bad string
    #    literals) without wasting a setup+run cycle.
    syntax_errors = check_python_syntax(project_dir)
    if syntax_errors:
        logs.append({
            "command": "(python syntax check)",
            "returncode": 1,
            "stdout": "",
            "stderr": "\n".join(syntax_errors),
            "timed_out": False,
        })
        return {
            "success": False,
            "reason": "Python syntax error(s) found before running anything.",
            "logs": logs,
        }

    # 1. Run setup commands (install deps, etc.)
    for cmd in setup_commands or []:
        if not cmd or not cmd.strip():
            continue
        res = _run(cmd, project_dir, SETUP_TIMEOUT)
        logs.append(res)
        if res["timed_out"]:
            return {"success": False, "reason": f"Setup command timed out: {cmd}", "logs": logs}
        if res["returncode"] != 0:
            return {"success": False, "reason": f"Setup command failed: {cmd}", "logs": logs}

    if not thorough:
        return _basic_run_check(project_dir, run_command, test_command, logs)

    # 2. Pick the command that actually checks the project
    command_to_run = (test_command or "").strip() or (run_command or "").strip()
    if not command_to_run:
        return {"success": False, "reason": "No test_command or run_command was provided.", "logs": logs}

    res = _run(command_to_run, project_dir, RUN_TIMEOUT)
    logs.append(res)

    if res["timed_out"]:
        combined_output = (res["stdout"] or "") + (res["stderr"] or "")
        server_markers = ("Running on http", "Uvicorn running", "Listening on", "Serving Flask app", "Debugger is active")
        if any(marker in combined_output for marker in server_markers):
            return {
                "success": False,
                "reason": (
                    f"Command timed out: {command_to_run}. This command started a web server "
                    "that never exits on its own, which cannot be used as a test. Use a separate "
                    "test file with the framework's test client (e.g. Flask's app.test_client() "
                    "or FastAPI's TestClient) instead of running the server directly."
                ),
                "logs": logs,
            }
        return {"success": False, "reason": f"Command timed out: {command_to_run}", "logs": logs}

    if res["returncode"] != 0:
        return {"success": False, "reason": f"Command exited with code {res['returncode']}: {command_to_run}", "logs": logs}

    if "Traceback (most recent call last)" in res["stderr"]:
        return {"success": False, "reason": "A traceback was detected in the output.", "logs": logs}

    return {"success": True, "reason": "All checks passed.", "logs": logs}


def _basic_run_check(project_dir, run_command, test_command, logs):
    """Basic mode: just confirm run_command (or test_command) starts without crashing."""
    command_to_run = (run_command or "").strip() or (test_command or "").strip()
    if not command_to_run:
        return {"success": False, "reason": "No run_command or test_command was provided.", "logs": logs}

    res = _run(command_to_run, project_dir, BASIC_RUN_TIMEOUT)
    logs.append(res)

    if "Traceback (most recent call last)" in res["stderr"]:
        return {"success": False, "reason": "A traceback was detected when running the program.", "logs": logs}

    if res["timed_out"]:
        # Still running with no error after the timeout — treat as a healthy
        # long-running process (e.g. a server) for a basic check.
        return {
            "success": True,
            "reason": f"Program ran for {BASIC_RUN_TIMEOUT}s without crashing (basic check).",
            "logs": logs,
        }

    if res["returncode"] != 0:
        return {"success": False, "reason": f"Command exited with code {res['returncode']}: {command_to_run}", "logs": logs}

    return {"success": True, "reason": "Program ran without crashing (basic check).", "logs": logs}


def format_error_feedback(test_result, max_chars=1500):
    """Turn a failed test_result into a readable string to feed back to the builder agent."""
    parts = [f"Reason: {test_result['reason']}"]
    for log in test_result["logs"]:
        parts.append(f"\n$ {log['command']}")
        if log.get("returncode") is not None:
            parts.append(f"(exit code: {log['returncode']})")
        if log["stdout"]:
            parts.append(f"STDOUT:\n{log['stdout'][:max_chars]}")
        if log["stderr"]:
            parts.append(f"STDERR:\n{log['stderr'][:max_chars]}")
    return "\n".join(parts)
