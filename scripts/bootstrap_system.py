#!/usr/bin/env python3
"""Restore the complete Xixi development system on a Codex machine."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*command: str, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def run_output(*command: str, cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)
    return result.stdout


def automation_path_from_output(output: str) -> Path:
    try:
        payload = json.loads(output)
        automation = Path(payload["automation"]).expanduser().resolve()
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise SystemExit("ERROR: automation ensure returned invalid output") from error
    if not automation.is_file():
        raise SystemExit(f"ERROR: ensured automation does not exist: {automation}")
    return automation


def sync_repo(repository: str, target: Path) -> None:
    if (target / ".git").is_dir():
        run("git", "-C", str(target), "fetch", "origin", "--prune")
        run("git", "-C", str(target), "merge", "--ff-only", "@{u}")
        return
    if target.exists():
        raise SystemExit(f"ERROR: target exists and is not a Git repository: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    run("git", "clone", f"https://github.com/{repository}.git", str(target))


def replace_tree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    args = parser.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    codex_home = Path(args.codex_home).expanduser().resolve()
    if not workspace.is_dir():
        raise SystemExit(f"ERROR: workspace does not exist: {workspace}")

    os.environ["CODEX_HOME"] = str(codex_home)
    installer = ROOT / "bin/install-local.sh"
    installed = codex_home / "skills/xixi-dev-system"
    command = [str(installer), "--upgrade"] if installed.exists() else [str(installer)]
    run(*command, cwd=ROOT)

    repos = codex_home / "xixi-dev-system" / "repos"
    profile = codex_home / "xixi-dev-system" / "profile"
    sync_repo("xixinikl/xixi-agent-profile", profile)
    workflow = repos / "standard-project-workflow"
    factory = repos / "codex-acceptance-factory"
    sync_repo("xixinikl/standard-project-workflow", workflow)
    sync_repo("xixinikl/codex-acceptance-factory", factory)
    replace_tree(workflow / "skills/standard-project-workflow", codex_home / "skills/standard-project-workflow")
    replace_tree(factory / "skills/daily-acceptance-factory", codex_home / "skills/daily-acceptance-factory")
    command_runner = codex_home / "bin" / "xixi-dev-system"
    automation_output = run_output(
        str(command_runner), "automation", "ensure-learning",
        "--workspace", str(workspace), "--codex-home", str(codex_home),
    )
    automation = automation_path_from_output(automation_output)
    print(f"Restored Xixi development system in {codex_home}")
    print(f"Weekly automation: {automation}")


if __name__ == "__main__":
    main()
