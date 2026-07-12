#!/usr/bin/env python3
"""Restore the complete Xixi development system on a Codex machine."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*command: str, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


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


def write_automation(codex_home: Path, workspace: Path) -> Path:
    prompt = (ROOT / "automations/weekly-personal-dev-system.prompt.md").read_text(encoding="utf-8")
    target = codex_home / "automations" / "weekly-personal-dev-system" / "automation.toml"
    for existing in (codex_home / "automations").glob("*/automation.toml"):
        if 'name = "每周个人开发系统回顾"' in existing.read_text(encoding="utf-8"):
            target = existing
            break
    target.parent.mkdir(parents=True, exist_ok=True)
    automation_id = target.parent.name
    now = int(time.time() * 1000)
    quoted_prompt = json.dumps(prompt, ensure_ascii=False)
    quoted_workspace = json.dumps(str(workspace), ensure_ascii=False)
    target.write_text(
        "\n".join([
            "version = 1",
            f"id = {json.dumps(automation_id)}",
            'kind = "cron"',
            'name = "每周个人开发系统回顾"',
            f"prompt = {quoted_prompt}",
            'status = "ACTIVE"',
            'rrule = "FREQ=WEEKLY;BYDAY=MO;BYHOUR=8;BYMINUTE=0"',
            'model = "gpt-5.6-terra"',
            'reasoning_effort = "high"',
            'execution_environment = "local"',
            f"target = {{ type = \"project\", project_id = {quoted_workspace} }}",
            f"cwds = [{quoted_workspace}]",
            f"created_at = {now}",
            f"updated_at = {now}",
            "",
        ]),
        encoding="utf-8",
    )
    return target


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
    automation = write_automation(codex_home, workspace)
    print(f"Restored Xixi development system in {codex_home}")
    print(f"Weekly automation: {automation}")


if __name__ == "__main__":
    main()
