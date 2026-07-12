#!/usr/bin/env python3
"""Verify the portable Xixi development system contract."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    parser.add_argument("--skip-github", action="store_true")
    args = parser.parse_args()
    codex_home = Path(args.codex_home).expanduser().resolve()
    manifest = json.loads((ROOT / "system/system-manifest.json").read_text(encoding="utf-8"))
    checks: list[tuple[str, bool]] = []
    for skill in manifest["installedSkills"]:
        checks.append((f"skill:{skill}", (codex_home / "skills" / skill / "SKILL.md").is_file()))
    weekly_automations = [
        path for path in (codex_home / "automations").glob("*/automation.toml")
        if 'name = "每周个人开发系统回顾"' in path.read_text(encoding="utf-8")
        and 'status = "ACTIVE"' in path.read_text(encoding="utf-8")
    ]
    checks.extend([
        ("command:xixi-dev-system", (codex_home / "bin/xixi-dev-system").exists()),
        ("profile", (codex_home / "xixi-dev-system/profile/.git").is_dir()),
        ("weekly-automation", len(weekly_automations) == 1),
    ])
    if not args.skip_github:
        for repo in manifest["repositories"]:
            result = subprocess.run(["gh", "repo", "view", repo["repository"], "--json", "name"], capture_output=True)
            checks.append((f"github:{repo['name']}", result.returncode == 0))
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    passed = all(value for _, value in checks)
    print("VERDICT: " + ("pass" if passed else "fail"))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
