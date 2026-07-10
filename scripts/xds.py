#!/usr/bin/env python3
"""Deterministic runtime for the Xixi development system."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
from pathlib import Path


CONFIG = ".xixi-dev-system.json"


def die(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def project(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        die(f"project directory does not exist: {path}")
    return path


def run_git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True)
    if check and result.returncode:
        die(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def load(root: Path) -> dict:
    path = root / CONFIG
    if not path.exists():
        die(f"missing {CONFIG}; run onboard first")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        die(f"invalid {CONFIG}: {error}")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def runtime_python(root: Path, config: dict, name: str) -> Path:
    suffix = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    return root / ".xds" / "venvs" / name / suffix


def expand(value: str, *, python: Path, namespace: str) -> str:
    return value.replace("{python}", shlex.quote(str(python))).replace("{namespace}", namespace)


def onboard(args: argparse.Namespace) -> None:
    root = project(args.project)
    target = root / CONFIG
    if target.exists():
        die(f"refusing to overwrite {target}")
    config = {
        "schemaVersion": 1,
        "projectName": args.name,
        "repository": args.repo,
        "defaultBranch": args.default_branch,
        "runtime": {
            "manager": args.manager,
            "python": args.python,
            "startCommand": args.start_command,
            "doctorCommand": args.doctor_command,
            "portEnvironment": "PORT",
            "dataNamespaceEnvironment": "XDS_DATA_NAMESPACE",
            "workingDirectory": ".",
            "requirements": [],
        },
        "collaboration": {
            "focusAuthors": args.focus_author,
            "riskPathPatterns": args.risk_path,
        },
    }
    write_json(target, config)
    for path in (root / ".xds" / "reports" / "updates", root / ".xds" / "runtime"):
        path.mkdir(parents=True, exist_ok=True)
    if run_git(root, "rev-parse", "--is-inside-work-tree", check=False) == "true":
        exclude_path = Path(run_git(root, "rev-parse", "--git-path", "info/exclude"))
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
        if ".xds/" not in existing.splitlines():
            exclude_path.write_text(existing.rstrip() + "\n.xds/\n", encoding="utf-8")
    print(f"Created {target}")


def doctor(args: argparse.Namespace) -> None:
    root = project(args.project)
    config = load(root)
    needed = ["schemaVersion", "projectName", "repository", "defaultBranch"]
    runtime = config.get("runtime", {})
    missing = [key for key in needed if not config.get(key)]
    missing.extend(f"runtime.{key}" for key in ("manager", "startCommand", "doctorCommand", "workingDirectory") if not runtime.get(key))
    git_ok = run_git(root, "rev-parse", "--is-inside-work-tree", check=False) == "true"
    reports_ok = (root / ".xds" / "reports" / "updates").is_dir()
    print(f"project: {config.get('projectName', 'unknown')}")
    print(f"git: {'pass' if git_ok else 'fail'}")
    print(f"adapter: {'pass' if not missing else 'fail'}")
    print(f"report-directory: {'pass' if reports_ok else 'fail'}")
    if missing:
        print("missing: " + ", ".join(missing))
    ok = git_ok and reports_ok and not missing
    print("VERDICT: " + ("pass" if ok else "fail"))
    raise SystemExit(0 if ok else 1)


def date_window(value: str) -> tuple[dt.date, str, str]:
    try:
        date = dt.date.fromisoformat(value)
    except ValueError:
        die("date must be YYYY-MM-DD")
    zone = dt.timezone(dt.timedelta(hours=8))
    start = dt.datetime.combine(date, dt.time.min, tzinfo=zone)
    return date, start.isoformat(), (start + dt.timedelta(days=1)).isoformat()


def updates(args: argparse.Namespace) -> None:
    root = project(args.project)
    config = load(root)
    date, start, end = date_window(args.date)
    run_git(root, "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--prune")
    raw = run_git(root, "log", "--remotes=origin", f"--since={start}", f"--before={end}", "--format=%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1e")
    patterns = [re.compile(value, re.I) for value in config.get("collaboration", {}).get("riskPathPatterns", [])]
    focus = [value.lower() for value in config.get("collaboration", {}).get("focusAuthors", [])]
    commits = []
    for record in raw.split("\x1e"):
        fields = record.strip().split("\x1f")
        if len(fields) != 5:
            continue
        sha, author, email, committed_at, subject = fields
        files = [item for item in run_git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", sha, check=False).splitlines() if item]
        branches = [line.strip().removeprefix("origin/") for line in run_git(root, "branch", "-r", "--contains", sha, check=False).splitlines() if line.strip() and "HEAD" not in line]
        commits.append({
            "sha": sha, "shortSha": sha[:12], "author": author, "email": email,
            "committedAt": committed_at, "subject": subject, "branches": sorted(branches),
            "files": files, "riskFiles": sorted({item for item in files if any(pattern.search(item) for pattern in patterns)}),
            "focusAuthor": author.lower() in focus or any(item in email.lower() for item in focus),
        })
    commits.sort(key=lambda item: item["committedAt"])
    base = root / ".xds" / "reports" / "updates" / date.isoformat()
    payload = {"schemaVersion": 1, "date": date.isoformat(), "timezone": "Asia/Shanghai", "repository": config["repository"], "commitCount": len(commits), "commits": commits}
    write_json(base.with_suffix(".json"), payload)
    lines = [f"# Collaboration update ledger - {date}", "", f"- Commits: {len(commits)}", "- Source: remote branch heads; no branch code was executed.", ""]
    for item in commits:
        lines += [f"## {item['shortSha']} {item['subject']}{' [focus]' if item['focusAuthor'] else ''}", f"- Author: {item['author']} <{item['email']}>", f"- Branches: {', '.join(item['branches']) or 'unmapped'}", f"- Files: {len(item['files'])}", f"- Risk files: {', '.join(item['riskFiles']) or 'none'}", ""]
    if not commits:
        lines.append("No remote commits were found in this Asia/Shanghai date window.")
    base.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(base.with_suffix(".md"))


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def runtime_prepare(args: argparse.Namespace) -> None:
    root = project(args.project)
    config = load(root)
    runtime = config["runtime"]
    if runtime.get("manager") != "uv":
        die("only the uv managed runtime is supported for isolated previews")
    if not shutil.which("uv"):
        die("uv is required; install it first with the documented user-level installer")
    name = args.name or "default"
    python = runtime_python(root, config, name)
    venv = python.parent.parent
    subprocess.run(["uv", "venv", "--python", str(runtime["python"]), str(venv)], cwd=root, check=True)
    for requirement in runtime.get("requirements", []):
        requirement_path = root / requirement
        if not requirement_path.is_file():
            die(f"missing requirements file: {requirement_path}")
        subprocess.run(["uv", "pip", "install", "--python", str(python), "-r", str(requirement_path)], cwd=root, check=True)
    print(python)


def workspace_create(args: argparse.Namespace) -> None:
    root = project(args.project)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", args.branch).strip("-")
    target = root / ".xds" / "worktrees" / safe
    if target.exists():
        die(f"worktree already exists: {target}")
    run_git(root, "fetch", "origin", "--prune")
    run_git(root, "worktree", "add", "-b", args.branch, str(target), args.base)
    print(target)


def preview_start(args: argparse.Namespace) -> None:
    root = project(args.project)
    config = load(root)
    name = args.name or "default"
    state_path = root / ".xds" / "runtime" / f"{name}.json"
    if state_path.exists():
        die(f"preview already recorded: {state_path}")
    command = args.command or config["runtime"].get("startCommand")
    if not command:
        die("missing runtime.startCommand")
    port = free_port()
    namespace = args.data_namespace or f"xds-{config['projectName'].lower().replace(' ', '-')}-{name}"
    python = runtime_python(root, config, name)
    if not args.command and not python.is_file():
        die(f"isolated runtime is not prepared: {python}; run runtime prepare first")
    command = expand(command, python=python, namespace=namespace)
    env = os.environ.copy()
    env[config["runtime"].get("portEnvironment", "PORT")] = str(port)
    env[config["runtime"].get("dataNamespaceEnvironment", "XDS_DATA_NAMESPACE")] = namespace
    for key, value in config.get("data", {}).get("environment", {}).items():
        path_value = expand(value, python=python, namespace=namespace)
        data_path = Path(path_value)
        if not data_path.is_absolute():
            data_path = root / data_path
        data_path.parent.mkdir(parents=True, exist_ok=True)
        env[key] = str(data_path)
    log_path = root / ".xds" / "runtime" / f"{name}.log"
    with log_path.open("w", encoding="utf-8") as log:
        cwd = root / config["runtime"].get("workingDirectory", ".")
        process = subprocess.Popen(command, shell=True, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    state = {"pid": process.pid, "url": f"http://127.0.0.1:{port}", "port": port, "dataNamespace": namespace, "command": command, "log": str(log_path)}
    write_json(state_path, state)
    print(json.dumps(state, ensure_ascii=False, indent=2))


def preview_stop(args: argparse.Namespace) -> None:
    root = project(args.project)
    state_path = root / ".xds" / "runtime" / f"{args.name or 'default'}.json"
    if not state_path.exists():
        die(f"no preview state: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    try:
        os.killpg(int(state["pid"]), signal.SIGTERM)
    except ProcessLookupError:
        pass
    state_path.unlink()
    print(f"Stopped {state['url']}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="xixi-dev-system")
    sub = parser.add_subparsers(dest="command", required=True)
    onboard_parser = sub.add_parser("onboard")
    for flag, required, default in (("--project", True, None), ("--name", True, None), ("--repo", True, None), ("--default-branch", False, "main"), ("--manager", False, "uv"), ("--python", False, "3.11"), ("--start-command", False, ""), ("--doctor-command", False, "")):
        onboard_parser.add_argument(flag, required=required, default=default)
    onboard_parser.add_argument("--focus-author", action="append", default=[])
    onboard_parser.add_argument("--risk-path", action="append", default=["auth", "payment", "migration", "deploy", "secret"])
    onboard_parser.set_defaults(func=onboard)
    doctor_parser = sub.add_parser("doctor"); doctor_parser.add_argument("--project", required=True); doctor_parser.set_defaults(func=doctor)
    updates_parser = sub.add_parser("updates"); updates_parser.add_argument("--project", required=True); updates_parser.add_argument("--date", default=dt.date.today().isoformat()); updates_parser.set_defaults(func=updates)
    runtime_parser = sub.add_parser("runtime"); runtime_sub = runtime_parser.add_subparsers(required=True)
    prepare_parser = runtime_sub.add_parser("prepare"); prepare_parser.add_argument("--project", required=True); prepare_parser.add_argument("--name"); prepare_parser.set_defaults(func=runtime_prepare)
    workspace_parser = sub.add_parser("workspace"); workspace_sub = workspace_parser.add_subparsers(required=True)
    create_parser = workspace_sub.add_parser("create"); create_parser.add_argument("--project", required=True); create_parser.add_argument("--branch", required=True); create_parser.add_argument("--base", default="origin/main"); create_parser.set_defaults(func=workspace_create)
    preview_parser = sub.add_parser("preview"); preview_sub = preview_parser.add_subparsers(required=True)
    start_parser = preview_sub.add_parser("start"); start_parser.add_argument("--project", required=True); start_parser.add_argument("--name"); start_parser.add_argument("--command"); start_parser.add_argument("--data-namespace"); start_parser.set_defaults(func=preview_start)
    stop_parser = preview_sub.add_parser("stop"); stop_parser.add_argument("--project", required=True); stop_parser.add_argument("--name"); stop_parser.set_defaults(func=preview_stop)
    args = parser.parse_args(); args.func(args)


if __name__ == "__main__":
    main()
