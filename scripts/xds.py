#!/usr/bin/env python3
"""Deterministic runtime for the Xixi development system."""

from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


CONFIG = ".xixi-dev-system.json"
PROFILE_REPOSITORY = "https://github.com/xixinikl/xixi-agent-profile.git"
GOAL_STATUSES = {"active", "blocked", "verified"}
TASK_STATUSES = {"pending", "running", "blocked", "failed", "verified"}
EVIDENCE_TYPES = {"command", "file", "url", "test", "screenshot", "note"}
EVIDENCE_NAMES = {
    "AGENTS.md", "CURRENT_STATUS.md", "TASKS.md", "HANDOFF.md", "PR_PLAN.md",
    "错误复盘.md", "README.md", "SYSTEM.md", "STATE.md",
}
EVIDENCE_NAME_MARKERS = ("HANDOFF", "AUDIT", "METHOD", "WORKFLOW", "GOAL")
DISCOVERY_SKIPS = {
    ".git", ".xds", ".xds-system", "node_modules", "venv", ".venv", "Library",
    ".cache", ".npm", ".nvm", ".codex", "dist", "build", "output",
}
RETROSPECTIVE_NAMES = {"错误复盘.md", "RETROSPECTIVE.md"}
RETROSPECTIVE_LABELS = {
    "scenario": ("场景", "已证实事实", "observed problem", "scenario"),
    "mistake": ("我做错了什么", "错误", "mistake"),
    "owner_correction": ("用户如何纠正", "用户纠正", "owner correction"),
    "root_cause": ("根因", "root cause"),
    "rule": ("以后必须这样做", "规则", "预防动作", "proposed rule", "prevention action"),
    "verification": ("可验证的防复发动作", "验证", "verification"),
    "impact": ("影响", "impact"),
}
REQUIRED_RETROSPECTIVE_FIELDS = ("scenario", "root_cause", "rule", "verification")
SENSITIVE_EVIDENCE_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{16,}|BEGIN\s+(?:RSA|OPENSSH|EC)\s+PRIVATE\s+KEY|(?:api[_ -]?key|token|password|cookie)\s*[:=]\s*\S+)",
    re.I,
)


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


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def github_origin_owner(origin: str) -> str | None:
    match = re.search(r"github\.com[/:]([^/]+)/[^/]+(?:\.git)?$", origin.strip(), re.I)
    return match.group(1) if match else None


def discover_local_repositories(roots: list[Path], owner: str, max_depth: int = 6) -> list[dict]:
    repositories: dict[str, dict] = {}
    for search_root in roots:
        if not search_root.is_dir():
            continue
        base_depth = len(search_root.parts)
        for current, directories, files in os.walk(search_root):
            current_path = Path(current)
            depth = len(current_path.parts) - base_depth
            directories[:] = [
                name for name in directories
                if name not in DISCOVERY_SKIPS and not (name.startswith(".") and name != ".git")
            ]
            git_marker = current_path / ".git"
            if git_marker.is_dir() or git_marker.is_file():
                origin = run_git(current_path, "remote", "get-url", "origin", check=False)
                if github_origin_owner(origin or "") == owner:
                    key = str(current_path.resolve())
                    repositories[key] = {
                        "name": current_path.name,
                        "path": key,
                        "origin": origin,
                        "owner": owner,
                        "branch": run_git(current_path, "branch", "--show-current", check=False),
                    }
                directories[:] = []
                continue
            if depth >= max_depth:
                directories[:] = []
    return sorted(repositories.values(), key=lambda item: item["path"])


def projects_discover(args: argparse.Namespace) -> None:
    roots = [project(value) for value in args.root]
    repositories = discover_local_repositories(roots, args.owner, args.max_depth)
    payload = {
        "schemaVersion": 1,
        "owner": args.owner,
        "scopePolicy": "local_git_origin_only",
        "remoteContentRead": False,
        "roots": [str(item) for item in roots],
        "repositoryCount": len(repositories),
        "repositories": repositories,
    }
    if args.output:
        target = Path(args.output).expanduser().resolve()
        write_json(target, payload)
        print(target)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def is_evidence_file(path: Path) -> bool:
    upper_name = path.name.upper()
    return path.name in EVIDENCE_NAMES or any(marker in upper_name for marker in EVIDENCE_NAME_MARKERS)


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def learning_portfolio(args: argparse.Namespace) -> None:
    projects = [project(value) for value in args.project]
    entries = []
    for root in projects:
        origin = run_git(root, "remote", "get-url", "origin", check=False)
        if github_origin_owner(origin or "") != args.owner:
            die(f"project origin is not owned by {args.owner}: {root}")
        evidence = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or any(part in DISCOVERY_SKIPS for part in path.relative_to(root).parts):
                continue
            if not is_evidence_file(path):
                continue
            relative = path.relative_to(root).as_posix()
            headings = []
            if path.suffix.lower() == ".md":
                headings = [line.lstrip("# ").strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("#")][:40]
            evidence.append({"path": relative, "sha256": file_digest(path), "headings": headings})
        entries.append({"name": root.name, "path": str(root), "origin": origin, "evidence": evidence})
    payload = {
        "schemaVersion": 1,
        "owner": args.owner,
        "readOnly": True,
        "remoteContentRead": False,
        "projects": entries,
    }
    target = Path(args.output).expanduser().resolve()
    write_json(target, payload)
    print(target)


def retrospective_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if any(part in DISCOVERY_SKIPS for part in relative.parts):
            continue
        if path.name in RETROSPECTIVE_NAMES or "retrospective" in relative.as_posix().lower():
            files.append(path)
    return sorted(set(files))


def parse_labeled_bullets(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current: str | None = None
    for line in body.splitlines():
        stripped = line.strip()
        bullet = re.match(r"^[-*]\s*(?:\*\*)?([^：:]+)(?:\*\*)?[：:]\s*(.*)$", stripped)
        if bullet:
            label = bullet.group(1).strip().lower()
            current = next((key for key, aliases in RETROSPECTIVE_LABELS.items() if label in aliases), None)
            if current:
                fields[current] = bullet.group(2).strip()
            continue
        if current and stripped and not stripped.startswith("#"):
            fields[current] = (fields[current] + " " + stripped).strip()
    return fields


def retrospective_sections(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.M))
    sections = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        if title.lower() in {"已证实事实", "影响", "预防动作", "是否升级为全局经验"}:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((title, text[match.end():end].strip()))
    if sections:
        return sections
    title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), "Untitled retrospective")
    return [(title, text)] if parse_labeled_bullets(text) else []


def normalized_fingerprint(value: str) -> str:
    compact = re.sub(r"[^\w\u4e00-\u9fff]+", "", value.lower())
    return hashlib.sha256(compact.encode("utf-8")).hexdigest()


def redact_sensitive_evidence(value: str) -> tuple[str, bool]:
    detected = bool(SENSITIVE_EVIDENCE_PATTERN.search(value))
    return SENSITIVE_EVIDENCE_PATTERN.sub("[REDACTED]", value), detected


def load_learning_registry(path: Path, owner: str) -> dict:
    if not path.exists():
        return {"schemaVersion": 1, "owner": owner, "candidates": [], "runs": []}
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schemaVersion") != 1 or registry.get("owner") != owner:
        die("learning registry schema or owner mismatch")
    if not isinstance(registry.get("candidates"), list) or not isinstance(registry.get("runs"), list):
        die("invalid learning registry structure")
    return registry


def learning_harvest(args: argparse.Namespace) -> None:
    roots = [project(value) for value in args.project]
    registry_path = Path(args.registry).expanduser().resolve()
    registry = load_learning_registry(registry_path, args.owner)
    existing = {item["sourceFingerprint"]: item for item in registry["candidates"]}
    seen: set[str] = set()
    added = updated = 0
    source_files = source_sections = 0
    for root in roots:
        origin = run_git(root, "remote", "get-url", "origin", check=False)
        if github_origin_owner(origin or "") != args.owner:
            die(f"project origin is not owned by {args.owner}: {root}")
        for source in retrospective_files(root):
            source_files += 1
            relative = source.relative_to(root).as_posix()
            source_text = source.read_text(encoding="utf-8", errors="replace")
            for title, body in retrospective_sections(source_text):
                source_sections += 1
                fields = parse_labeled_bullets(body)
                safe_excerpt, sensitive = redact_sensitive_evidence(body[: args.excerpt_chars])
                safe_fields = {key: redact_sensitive_evidence(value)[0] for key, value in fields.items()}
                source_key = f"{origin}\n{relative}\n{title}"
                source_fingerprint = hashlib.sha256(source_key.encode("utf-8")).hexdigest()
                content_fingerprint = hashlib.sha256((title + "\n" + body).encode("utf-8")).hexdigest()
                missing = [name for name in REQUIRED_RETROSPECTIVE_FIELDS if not fields.get(name)]
                candidate = {
                    "id": "lrn-" + source_fingerprint[:16],
                    "title": title,
                    "project": root.name,
                    "projectPath": str(root),
                    "origin": origin,
                    "sourcePath": relative,
                    "sourceFingerprint": source_fingerprint,
                    "contentFingerprint": content_fingerprint,
                    "ruleFingerprint": normalized_fingerprint(safe_fields.get("rule") or title),
                    "fields": safe_fields,
                    "missingFields": missing,
                    "ownerCorrectionPresent": bool(safe_fields.get("owner_correction")),
                    "status": "blocked_sensitive" if sensitive else "needs_completion" if missing else "ready_for_review",
                    "sensitiveEvidenceDetected": sensitive,
                    "sourceExcerpt": safe_excerpt,
                }
                previous = existing.get(source_fingerprint)
                if previous:
                    if previous.get("contentFingerprint") == content_fingerprint:
                        candidate = previous
                    else:
                        candidate["reviewHistory"] = previous.get("reviewHistory", [])
                        candidate["status"] = "blocked_sensitive" if sensitive else "needs_re_review" if not missing else "needs_completion"
                        updated += 1
                else:
                    added += 1
                existing[source_fingerprint] = candidate
                seen.add(source_fingerprint)
    registry["candidates"] = sorted(existing.values(), key=lambda item: (item["origin"], item["sourcePath"], item["title"]))
    counts = Counter(item["status"] for item in registry["candidates"])
    run = {
        "recordedAt": timestamp(), "projects": [str(item) for item in roots],
        "sourceFiles": source_files, "sourceSections": source_sections,
        "added": added, "updated": updated, "unchanged": source_sections - added - updated,
        "statusCounts": dict(counts),
    }
    registry["runs"].append(run)
    registry["updatedAt"] = run["recordedAt"]
    write_json(registry_path, registry)
    print(json.dumps(run, ensure_ascii=False, indent=2))


def registry_candidate(registry: dict, candidate_id: str) -> dict:
    candidate = next((item for item in registry["candidates"] if item["id"] == candidate_id), None)
    if not candidate:
        die(f"unknown learning candidate: {candidate_id}")
    return candidate


def learning_review(args: argparse.Namespace) -> None:
    registry_path = Path(args.registry).expanduser().resolve()
    registry = load_learning_registry(registry_path, args.owner)
    candidate = registry_candidate(registry, args.candidate_id)
    if candidate["status"] not in {"ready_for_review", "needs_re_review"}:
        die(f"candidate is not reviewable: {candidate['status']}")
    supporting = [candidate]
    for candidate_id in args.supporting_id:
        supporting.append(registry_candidate(registry, candidate_id))
    unique_origins = {item["origin"] for item in supporting}
    high_impact_owner_correction = args.owner_corrected and args.impact == "high" and candidate.get("ownerCorrectionPresent")
    if args.decision == "promote" and len(unique_origins) < 2 and not high_impact_owner_correction:
        die("promotion requires two source origins, or an explicit high-impact owner correction present in source evidence")
    if args.decision == "promote" and (not args.rule.strip() or not args.verification.strip() or not args.scope.strip()):
        die("promotion requires rule, scope, and verification")
    now = timestamp()
    review = {
        "reviewedAt": now, "reviewer": args.reviewer, "decision": args.decision,
        "reason": args.reason, "impact": args.impact, "scope": args.scope,
        "rule": args.rule, "verification": args.verification,
        "supportingCandidateIds": [item["id"] for item in supporting],
        "sourceOrigins": sorted(unique_origins),
        "ownerCorrected": bool(args.owner_corrected),
    }
    candidate.setdefault("reviewHistory", []).append(review)
    candidate["review"] = review
    candidate["status"] = {"promote": "approved_for_profile", "keep-project": "project_only", "reject": "rejected"}[args.decision]
    registry["updatedAt"] = now
    write_json(registry_path, registry)
    print(json.dumps({"id": candidate["id"], "status": candidate["status"], "review": review}, ensure_ascii=False, indent=2))


def learning_publish(args: argparse.Namespace) -> None:
    registry_path = Path(args.registry).expanduser().resolve()
    registry = load_learning_registry(registry_path, args.owner)
    candidate = registry_candidate(registry, args.candidate_id)
    profile = project(args.profile)
    target = profile / "LEARNINGS.md"
    if not target.is_file():
        die(f"missing shared learning file: {target}")
    marker = f"<!-- xds-learning:{candidate['id']} -->"
    current = target.read_text(encoding="utf-8")
    if candidate.get("status") == "published" and marker in current:
        print(f"Already published: {candidate['id']}")
        return
    if candidate.get("status") != "approved_for_profile" or not candidate.get("review"):
        die("only reviewed approved_for_profile candidates can be published")
    if marker in current:
        die("Profile contains the candidate marker but registry is not published; reconcile state manually")
    review = candidate["review"]
    evidence = ", ".join(f"{item['origin']}:{item['sourcePath']}" for item in [registry_candidate(registry, value) for value in review["supportingCandidateIds"]])
    entry = f"""\n{marker}\n### {candidate['title']}\n\n- 分类：工程 / 协作\n- 规则：{review['rule']}\n- 证据：{evidence}\n- 适用范围：{review['scope']}\n- 验证：{review['verification']}\n- 最后验证：{review['reviewedAt'][:10]}\n"""
    target.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")
    candidate["status"] = "published"
    candidate["publishedAt"] = timestamp()
    candidate["publishedTarget"] = str(target)
    registry["updatedAt"] = candidate["publishedAt"]
    write_json(registry_path, registry)
    print(target)


def goal_lint(args: argparse.Namespace) -> None:
    document = Path(args.document).expanduser().resolve()
    spec_path = Path(args.spec).expanduser().resolve()
    if not document.is_file() or not spec_path.is_file():
        die("goal lint requires an existing document and spec")
    text = document.read_text(encoding="utf-8")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    validate_goal_spec(spec)
    requirements = {
        "authoritative_entry": r"唯一权威|authoritative entry|authoritative document",
        "current_facts": r"当前事实|current facts",
        "scope": r"范围|scope",
        "non_scope": r"不包含|非范围|out of scope|non-scope",
        "phases": r"阶段|phase|阶段计划",
        "evidence": r"证据|evidence",
        "stop_conditions": r"停止条件|stop conditions?",
        "completion_audit": r"completion audit|完成审计",
        "launch_prompt": r"开 Goal|goal prompt|目标文本",
    }
    missing = [name for name, pattern in requirements.items() if not re.search(pattern, text, re.I)]
    missing_task_ids = [task["id"] for task in spec["tasks"] if not re.search(rf"\b{re.escape(task['id'])}\b", text)]
    payload = {
        "schemaVersion": 1,
        "document": str(document),
        "spec": str(spec_path),
        "taskCount": len(spec["tasks"]),
        "missingSections": missing,
        "missingTaskIds": missing_task_ids,
        "verdict": "pass" if not missing and not missing_task_ids else "fail",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload["verdict"] != "pass":
        raise SystemExit(1)


def goal_directory(root: Path) -> Path:
    return root / ".xds" / "goals"


def goal_path(root: Path, goal_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", goal_id):
        die("goal id may contain only letters, numbers, dot, underscore, and dash")
    return goal_directory(root) / f"{goal_id}.json"


def validate_goal_spec(spec: dict) -> None:
    required = ("id", "title", "objective", "tasks")
    missing = [key for key in required if not spec.get(key)]
    if missing:
        die("goal spec missing: " + ", ".join(missing))
    tasks = spec["tasks"]
    if not isinstance(tasks, list) or not tasks:
        die("goal spec requires at least one task")
    ids = [task.get("id") for task in tasks]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        die("task ids must be present and unique")
    known = set(ids)
    for task in tasks:
        if not task.get("title") or not task.get("acceptance"):
            die(f"task {task.get('id', '?')} requires title and acceptance")
        unknown = set(task.get("dependsOn", [])) - known
        if unknown:
            die(f"task {task['id']} has unknown dependencies: {', '.join(sorted(unknown))}")

    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {task["id"]: task for task in tasks}

    def visit(task_id: str) -> None:
        if task_id in visiting:
            die(f"goal task dependency cycle includes {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in by_id[task_id].get("dependsOn", []):
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in ids:
        visit(task_id)


def load_goal(root: Path, goal_id: str | None = None) -> tuple[Path, dict]:
    if goal_id:
        path = goal_path(root, goal_id)
    else:
        paths = sorted(goal_directory(root).glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not paths:
            die("no goal found; run goal create first")
        path = paths[0]
    if not path.is_file():
        die(f"goal does not exist: {path}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def derive_goal(goal: dict) -> dict:
    tasks = goal["tasks"]
    verified = sum(task["status"] == "verified" for task in tasks)
    running = next((task for task in tasks if task["status"] == "running"), None)
    blocked = [task for task in tasks if task["status"] == "blocked"]
    eligible = next((
        task for task in tasks
        if task["status"] == "pending"
        and all(next(item for item in tasks if item["id"] == dependency)["status"] == "verified" for dependency in task.get("dependsOn", []))
    ), None)
    goal["progress"] = {"verified": verified, "total": len(tasks), "percent": round(verified * 100 / len(tasks))}
    goal["currentTaskId"] = running["id"] if running else None
    goal["nextTaskId"] = eligible["id"] if eligible else None
    goal["status"] = "verified" if verified == len(tasks) else "blocked" if blocked and not running and not eligible else "active"
    goal["updatedAt"] = timestamp()
    return goal


def goal_create(args: argparse.Namespace) -> None:
    root = project(args.project)
    spec_path = Path(args.spec).expanduser().resolve()
    if not spec_path.is_file():
        die(f"goal spec does not exist: {spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    validate_goal_spec(spec)
    target = goal_path(root, spec["id"])
    if target.exists():
        die(f"goal already exists: {target}")
    now = timestamp()
    goal = {
        "schemaVersion": 1,
        "id": spec["id"],
        "title": spec["title"],
        "objective": spec["objective"],
        "status": "active",
        "createdAt": now,
        "updatedAt": now,
        "tasks": [{
            "id": task["id"], "title": task["title"], "acceptance": task["acceptance"],
            "dependsOn": task.get("dependsOn", []), "status": "pending", "evidence": []
        } for task in spec["tasks"]],
        "runs": [],
        "blockers": [],
    }
    derive_goal(goal)
    write_json(target, goal)
    print(target)
    goal_show_value(goal)


def progress_bar(percent: int, width: int = 20) -> str:
    filled = round(width * percent / 100)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def goal_show_value(goal: dict) -> None:
    derive_goal(goal)
    progress = goal["progress"]
    print(f"Goal: {goal['title']} ({goal['id']})")
    print(f"Status: {goal['status']}")
    print(f"Progress: {progress_bar(progress['percent'])} {progress['percent']}% ({progress['verified']}/{progress['total']})")
    print(f"Current: {goal.get('currentTaskId') or 'none'}")
    print(f"Next: {goal.get('nextTaskId') or 'none'}")
    blockers = [task["id"] for task in goal["tasks"] if task["status"] == "blocked"]
    print(f"Blocked: {', '.join(blockers) or 'none'}")
    for task in goal["tasks"]:
        marker = {"verified": "x", "running": ">", "blocked": "!", "failed": "!", "pending": " "}[task["status"]]
        print(f"  [{marker}] {task['id']} {task['title']} - {task['status']}")


def goal_show(args: argparse.Namespace) -> None:
    root = project(args.project)
    _, goal = load_goal(root, args.goal)
    goal_show_value(goal)


def find_task(goal: dict, task_id: str) -> dict:
    task = next((item for item in goal["tasks"] if item["id"] == task_id), None)
    if not task:
        die(f"unknown task: {task_id}")
    return task


def latest_run(goal: dict, task_id: str) -> dict:
    run = next((item for item in reversed(goal["runs"]) if item["taskId"] == task_id and item["status"] == "running"), None)
    if not run:
        die(f"task {task_id} has no running execution")
    return run


def save_goal(path: Path, goal: dict) -> None:
    derive_goal(goal)
    write_json(path, goal)


def goal_task_start(args: argparse.Namespace) -> None:
    root = project(args.project)
    path, goal = load_goal(root, args.goal)
    task = find_task(goal, args.task)
    if task["status"] != "pending":
        die(f"task {task['id']} is {task['status']}, expected pending")
    if any(item["status"] == "running" for item in goal["tasks"]):
        die("another task is already running")
    unmet = [dependency for dependency in task.get("dependsOn", []) if find_task(goal, dependency)["status"] != "verified"]
    if unmet:
        die("unverified dependencies: " + ", ".join(unmet))
    now = timestamp()
    task["status"] = "running"
    task["startedAt"] = now
    goal["runs"].append({"id": f"run-{len(goal['runs']) + 1}", "taskId": task["id"], "status": "running", "startedAt": now})
    save_goal(path, goal)
    goal_show_value(goal)


def goal_task_verify(args: argparse.Namespace) -> None:
    root = project(args.project)
    path, goal = load_goal(root, args.goal)
    task = find_task(goal, args.task)
    if task["status"] != "running":
        die(f"task {task['id']} is {task['status']}, expected running")
    if args.evidence_type not in EVIDENCE_TYPES or not args.evidence.strip():
        die("verified tasks require non-empty evidence")
    now = timestamp()
    evidence = {"id": f"evidence-{sum(len(item['evidence']) for item in goal['tasks']) + 1}", "type": args.evidence_type, "value": args.evidence.strip(), "recordedAt": now}
    task["evidence"].append(evidence)
    task["status"] = "verified"
    task["completedAt"] = now
    run = latest_run(goal, task["id"])
    run.update({"status": "verified", "completedAt": now, "evidenceIds": [evidence["id"]]})
    save_goal(path, goal)
    goal_show_value(goal)


def goal_task_stop(args: argparse.Namespace) -> None:
    root = project(args.project)
    path, goal = load_goal(root, args.goal)
    task = find_task(goal, args.task)
    if task["status"] != "running":
        die(f"task {task['id']} is {task['status']}, expected running")
    if not args.reason.strip():
        die(f"{args.status} requires a reason")
    now = timestamp()
    task["status"] = args.status
    task["reason"] = args.reason.strip()
    run = latest_run(goal, task["id"])
    run.update({"status": args.status, "completedAt": now, "reason": args.reason.strip()})
    if args.status == "blocked":
        goal["blockers"].append({"taskId": task["id"], "reason": args.reason.strip(), "recordedAt": now})
    save_goal(path, goal)
    goal_show_value(goal)


def runtime_python(root: Path, config: dict, name: str) -> Path:
    suffix = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    return root / ".xds" / "venvs" / name / suffix


def expand(value: str, *, python: Path, namespace: str) -> str:
    return value.replace("{python}", shlex.quote(str(python))).replace("{namespace}", namespace)


def package_scripts(root: Path) -> dict[str, str]:
    path = root / "package.json"
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    scripts = value.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def detect_adapter(root: Path) -> dict[str, str]:
    scripts = package_scripts(root)
    if scripts:
        runner = "npm"
        if (root / "pnpm-lock.yaml").exists():
            runner = "pnpm"
        elif (root / "yarn.lock").exists():
            runner = "yarn"
        start_script = next((name for name in ("dev", "start", "preview") if name in scripts), "")
        doctor_script = next((name for name in ("doctor", "verify", "test", "check", "lint", "build") if name in scripts), "")
        start = f"{runner} run {start_script}" if start_script else ""
        doctor = f"{runner} run {doctor_script}" if doctor_script else ""
        return {"manager": "uv", "python": "3.11", "startCommand": start, "doctorCommand": doctor}
    if (root / "index.html").exists():
        return {
            "manager": "uv",
            "python": "3.11",
            "startCommand": "{python} -m http.server $PORT --bind 127.0.0.1",
            "doctorCommand": "git diff --check",
        }
    return {"manager": "uv", "python": "3.11", "startCommand": "", "doctorCommand": "git diff --check"}


def detect_git_value(root: Path, *args: str) -> str:
    if run_git(root, "rev-parse", "--is-inside-work-tree", check=False) != "true":
        return ""
    return run_git(root, *args, check=False)


def profile_sync(args: argparse.Namespace) -> None:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    target = Path(args.target).expanduser().resolve() if args.target else codex_home / "xixi-dev-system" / "profile"
    repository = args.repo or PROFILE_REPOSITORY
    if target.exists():
        if not (target / ".git").is_dir():
            die(f"profile target exists but is not a Git repository: {target}")
        run_git(target, "fetch", "origin", "--prune")
        run_git(target, "merge", "--ff-only", "@{u}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(["git", "clone", repository, str(target)], text=True, capture_output=True)
        if result.returncode:
            die(result.stderr.strip() or "profile clone failed")
    print(target)


def onboard(args: argparse.Namespace) -> None:
    root = project(args.project)
    target = root / CONFIG
    if target.exists():
        die(f"refusing to overwrite {target}")
    detected = detect_adapter(root)
    repository = args.repo or detect_git_value(root, "remote", "get-url", "origin")
    branch = (
        args.default_branch
        or detect_git_value(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").removeprefix("origin/")
        or detect_git_value(root, "branch", "--show-current")
        or "main"
    )
    config = {
        "schemaVersion": 1,
        "projectName": args.name or root.name,
        "repository": repository,
        "defaultBranch": branch,
        "runtime": {
            "manager": args.manager or detected["manager"],
            "python": args.python or detected["python"],
            "startCommand": args.start_command or detected["startCommand"],
            "doctorCommand": args.doctor_command or detected["doctorCommand"],
            "portEnvironment": "PORT",
            "dataNamespaceEnvironment": "XDS_DATA_NAMESPACE",
            "workingDirectory": ".",
            "requirements": [],
        },
        "collaboration": {
            "focusAuthors": args.focus_author,
            "riskPathPatterns": args.risk_path,
        },
        "quality": {
            "acceptanceCommand": args.doctor_command or detected["doctorCommand"],
            "autofixCommand": "",
            "autofixPaths": [],
        },
        "learning": {
            "projectRetrospectiveDirectory": "doc/retrospectives",
            "sharedProfileRepository": "https://github.com/xixinikl/xixi-agent-profile",
        },
    }
    write_json(target, config)
    for path in (root / ".xds" / "reports" / "updates", root / ".xds" / "runtime"):
        path.mkdir(parents=True, exist_ok=True)
    if run_git(root, "rev-parse", "--is-inside-work-tree", check=False) == "true":
        exclude_path = Path(run_git(root, "rev-parse", "--git-path", "info/exclude"))
        if not exclude_path.is_absolute():
            exclude_path = root / exclude_path
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
        if ".xds/" not in existing.splitlines():
            exclude_path.write_text(existing.rstrip() + "\n.xds/\n", encoding="utf-8")
    print(f"Created {target}")
    print(f"Detected: {config['projectName']} · {config['runtime']['manager']} · {config['defaultBranch']}")
    if not repository:
        print("Next: add a GitHub origin, then set repository in .xixi-dev-system.json")
    if not config["runtime"]["startCommand"]:
        print("Next: set runtime.startCommand in .xixi-dev-system.json before preview")


def doctor(args: argparse.Namespace) -> None:
    root = project(args.project)
    config = load(root)
    needed = ["schemaVersion", "projectName", "repository", "defaultBranch"]
    runtime = config.get("runtime", {})
    missing = [key for key in needed if not config.get(key)]
    missing.extend(f"runtime.{key}" for key in ("manager", "startCommand", "doctorCommand", "workingDirectory") if not runtime.get(key))
    git_ok = run_git(root, "rev-parse", "--is-inside-work-tree", check=False) == "true"
    reports_path = root / ".xds" / "reports" / "updates"
    report_parents = (root / ".xds", root / ".xds" / "reports", reports_path)
    reports_ok = not any(path.exists() and not path.is_dir() for path in report_parents)
    reports_status = "pass" if reports_path.is_dir() else "ready" if reports_ok else "fail"
    print(f"project: {config.get('projectName', 'unknown')}")
    print(f"git: {'pass' if git_ok else 'fail'}")
    print(f"adapter: {'pass' if not missing else 'fail'}")
    print(f"report-directory: {reports_status}")
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


def wait_for_port(process: subprocess.Popen, port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.2)
    return False


def runtime_prepare(args: argparse.Namespace) -> None:
    root = project(args.project)
    config = load(root)
    (root / ".xds" / "runtime").mkdir(parents=True, exist_ok=True)
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


def automation_install(args: argparse.Namespace) -> None:
    root = project(args.project)
    config = load(root)
    vendor = root / ".xds-system" / "xds.py"
    workflow = root / ".github" / "workflows" / "xds-daily-updates.yml"
    weekly_workflow = root / ".github" / "workflows" / "xds-weekly-review.yml"
    if (vendor.exists() or workflow.exists() or weekly_workflow.exists()) and not args.force:
        die("automation files already exist; use --force only for a deliberate upgrade")
    vendor.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__), vendor)
    workflow.parent.mkdir(parents=True, exist_ok=True)
    autofix_paths = config.get("quality", {}).get("autofixPaths", [])
    autofix_paths_yaml = "\n".join(f"            {path}" for path in autofix_paths) or "            # Configure quality.autofixPaths before enabling repair PRs."
    workflow.write_text("""name: Xixi Daily Update Ledger

on:
  workflow_dispatch:
    inputs:
      target_date:
        description: \"Asia/Shanghai date (YYYY-MM-DD), empty means today\"
        required: false
        default: \"\"
  schedule:
    - cron: \"20 22 * * *\"

permissions:
  contents: write
  pull-requests: write

jobs:
  ledger:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Resolve report date
        id: date
        shell: bash
        run: |
          if [ -n \"${{ github.event.inputs.target_date }}\" ]; then
            echo \"value=${{ github.event.inputs.target_date }}\" >> \"$GITHUB_OUTPUT\"
          else
            echo \"value=$(TZ=Asia/Shanghai date +%F)\" >> \"$GITHUB_OUTPUT\"
          fi
      - name: Collect collaboration updates
        run: python3 .xds-system/xds.py updates --project . --date \"${{ steps.date.outputs.value }}\"
      - name: Run update-aware acceptance
        id: acceptance
        continue-on-error: true
        run: python3 .xds-system/xds.py acceptance --project . --date \"${{ steps.date.outputs.value }}\"
      - name: Write summary
        if: always()
        run: |
          for REPORT in \".xds/reports/updates/${{ steps.date.outputs.value }}.md\" \".xds/reports/acceptance/${{ steps.date.outputs.value }}.md\"; do
            if [ -f \"$REPORT\" ]; then cat \"$REPORT\" >> \"$GITHUB_STEP_SUMMARY\"; fi
          done
      - name: Upload update evidence
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: xds-daily-evidence-${{ steps.date.outputs.value }}
          path: .xds/reports/
          retention-days: 90
      - name: Create verified low-risk repair PR
        if: always() && steps.acceptance.outcome == 'success'
        uses: peter-evans/create-pull-request@v7
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: \"fix: apply verified xds low-risk repair\"
          branch: \"codex/xds-auto-fix-${{ steps.date.outputs.value }}\"
          delete-branch: true
          title: \"fix: verified daily low-risk repair (${{ steps.date.outputs.value }})\"
          body: |
            Generated by xixi-dev-system after a configured low-risk repair passed its verification command.
            The update ledger contained no high-risk paths. Review the Actions artifact before merging.
          add-paths: |
""" + autofix_paths_yaml + """
""", encoding="utf-8")
    weekly_workflow.write_text("""name: Xixi Weekly Collaboration Review

on:
  workflow_dispatch:
  schedule:
    - cron: \"10 23 * * 0\"

permissions:
  contents: read

jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Build weekly evidence review
        run: python3 .xds-system/xds.py weekly-review --project . --date \"$(TZ=Asia/Shanghai date +%F)\"
      - name: Write summary
        if: always()
        run: cat ".xds/reports/weekly/$(TZ=Asia/Shanghai date +%F).md" >> \"$GITHUB_STEP_SUMMARY\"
      - name: Upload weekly review
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: xds-weekly-review
          path: .xds/reports/weekly/
          retention-days: 90
""", encoding="utf-8")
    print(vendor)
    print(workflow)
    print(weekly_workflow)


def personal_learning_automation_path(codex_home: Path) -> tuple[Path, int]:
    automations_root = codex_home / "automations"
    matches = []
    if automations_root.is_dir():
        for path in automations_root.glob("*/automation.toml"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if 'id = "weekly-personal-dev-system"' in text or 'name = "每周个人开发系统回顾"' in text:
                matches.append(path)
    if len(matches) > 1:
        die("multiple personal learning automations exist; review duplicates before ensuring")
    return (matches[0] if matches else automations_root / "weekly-personal-dev-system" / "automation.toml", len(matches))


def automation_learning_ensure(args: argparse.Namespace) -> None:
    workspace = project(args.workspace)
    codex_home = Path(args.codex_home).expanduser().resolve()
    prompt_path = Path(__file__).resolve().parents[1] / "automations" / "weekly-personal-dev-system.prompt.md"
    if not prompt_path.is_file():
        die(f"missing versioned automation prompt: {prompt_path}")
    target, existing_count = personal_learning_automation_path(codex_home)
    previous = target.read_text(encoding="utf-8") if target.exists() else ""
    created_match = re.search(r"^created_at\s*=\s*(\d+)$", previous, re.M)
    now = int(time.time() * 1000)
    created_at = int(created_match.group(1)) if created_match else now
    target.parent.mkdir(parents=True, exist_ok=True)
    prompt = prompt_path.read_text(encoding="utf-8")
    target.write_text("\n".join([
        "version = 1",
        'id = "weekly-personal-dev-system"',
        'kind = "cron"',
        'name = "每周个人开发系统回顾"',
        f"prompt = {json.dumps(prompt, ensure_ascii=False)}",
        'status = "ACTIVE"',
        'rrule = "FREQ=WEEKLY;BYDAY=MO;BYHOUR=8;BYMINUTE=0"',
        'model = "gpt-5.6-terra"',
        'reasoning_effort = "high"',
        'execution_environment = "local"',
        f"target = {{ type = \"project\", project_id = {json.dumps(str(workspace))} }}",
        f"cwds = [{json.dumps(str(workspace))}]",
        f"created_at = {created_at}",
        f"updated_at = {now}",
        "",
    ]), encoding="utf-8")
    print(json.dumps({
        "status": "updated" if existing_count else "created",
        "automation": str(target), "workspace": str(workspace),
        "id": "weekly-personal-dev-system", "duplicateCount": 0,
    }, ensure_ascii=False, indent=2))


def weekly_review(args: argparse.Namespace) -> None:
    root = project(args.project)
    config = load(root)
    end, _, _ = date_window(args.date)
    days = [end - dt.timedelta(days=offset) for offset in range(6, -1, -1)]
    collected = []
    for date in days:
        updates(argparse.Namespace(project=str(root), date=date.isoformat()))
        report = root / ".xds" / "reports" / "updates" / f"{date}.json"
        collected.extend(json.loads(report.read_text(encoding="utf-8")).get("commits", []))
    unique = {item["sha"]: item for item in collected}
    commits = sorted(unique.values(), key=lambda item: item["committedAt"])
    risks = Counter(path for item in commits for path in item.get("riskFiles", []))
    authors = Counter(item["author"] for item in commits)
    output = root / ".xds" / "reports" / "weekly" / end.isoformat()
    payload = {"schemaVersion": 1, "endDate": end.isoformat(), "startDate": days[0].isoformat(), "repository": config["repository"], "commitCount": len(commits), "authors": authors, "riskFiles": risks}
    write_json(output.with_suffix(".json"), payload)
    lines = [f"# Weekly collaboration review - {days[0]} to {end}", "", f"- Remote commits: {len(commits)}", "- This is evidence collection, not automatic global learning promotion.", "", "## Contributors"]
    lines.extend(f"- {author}: {count}" for author, count in authors.most_common() or [("none", 0)])
    lines += ["", "## Risk paths"]
    lines.extend(f"- {path}: {count}" for path, count in risks.most_common() or [("none", 0)])
    lines += ["", "## Promotion gate", "- Promote only repeated or high-impact findings with a concrete test, rule, or prevention action."]
    output.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output.with_suffix(".md"))


def acceptance(args: argparse.Namespace) -> None:
    root = project(args.project)
    config = load(root)
    date = args.date
    updates(argparse.Namespace(project=str(root), date=date))
    ledger = json.loads((root / ".xds" / "reports" / "updates" / f"{date}.json").read_text(encoding="utf-8"))
    risk_files = sorted({path for item in ledger.get("commits", []) for path in item.get("riskFiles", [])})
    quality = config.get("quality", {})
    command = quality.get("acceptanceCommand", "").replace("{date}", date)
    if not command:
        die("missing quality.acceptanceCommand")
    result = subprocess.run(command, shell=True, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    autofix = {"attempted": False, "kept": False}
    fix_command = quality.get("lowRiskAutofixCommand", "").replace("{date}", date)
    if result.returncode and fix_command and not risk_files:
        fix = subprocess.run(fix_command, shell=True, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        verify = subprocess.run(command, shell=True, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        autofix = {"attempted": True, "kept": fix.returncode == 0 and verify.returncode == 0, "fixExitCode": fix.returncode, "verifyExitCode": verify.returncode, "outputTail": (fix.stdout or "")[-4000:]}
        if autofix["kept"]:
            result = verify
    status = "pass" if result.returncode == 0 and not risk_files else "conditional" if result.returncode == 0 else "fail"
    payload = {"schemaVersion": 1, "date": date, "verdict": status, "updates": ledger["commitCount"], "riskFiles": risk_files, "checkExitCode": result.returncode, "checkOutputTail": (result.stdout or "")[-4000:], "autofix": autofix}
    output = root / ".xds" / "reports" / "acceptance" / date
    write_json(output.with_suffix(".json"), payload)
    text = f"""# Acceptance report - {date}

- Verdict: `{status}`
- Collaboration updates: {ledger['commitCount']}
- High-risk changed paths: {', '.join(risk_files) or 'none'}
- Check exit: {result.returncode}
- Low-risk autofix attempted: {autofix['attempted']}
- Low-risk autofix kept: {autofix['kept']}

## Scope boundary

The configured acceptance command ran only in this checked-out worktree. Remote collaboration branches were collected as facts and were not executed.
"""
    output.with_suffix(".md").write_text(text, encoding="utf-8")
    print(output.with_suffix(".md"))
    raise SystemExit(0 if status in ("pass", "conditional") else result.returncode or 1)


def learning_candidate(args: argparse.Namespace) -> None:
    root = project(args.project)
    config = load(root)
    report_path = root / ".xds" / "reports" / "acceptance" / f"{args.date}.json"
    if not report_path.exists():
        die(f"missing acceptance evidence: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    worth_review = report["verdict"] != "pass" or report.get("autofix", {}).get("attempted")
    if not worth_review:
        print("No learning candidate: pass with no autofix.")
        return
    directory = root / config.get("learning", {}).get("projectRetrospectiveDirectory", "doc/retrospectives")
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / f"{args.date}-xds-learning-candidate.md"
    if candidate.exists() and not args.force:
        die(f"candidate exists: {candidate}")
    text = f"""# {args.date} XDS learning candidate

- Source evidence: `.xds/reports/acceptance/{args.date}.json`
- Verdict: `{report['verdict']}`
- High-risk paths: {', '.join(report.get('riskFiles', [])) or 'none'}
- Low-risk autofix attempted: {report.get('autofix', {}).get('attempted', False)}
- Promotion status: pending weekly review

## Verified facts

- The acceptance report and update ledger are the only evidence source for this candidate.

## Prevention action

- Add a concrete test, check, or project rule only after weekly review confirms the root cause.

## Shared-learning decision

- Do not promote a one-off event. Promote only repeated or high-impact rules with an executable prevention action.
"""
    candidate.write_text(text, encoding="utf-8")
    print(candidate)


def learning_promote(args: argparse.Namespace) -> None:
    candidate = Path(args.candidate).expanduser().resolve()
    profile = Path(args.profile).expanduser().resolve()
    if not candidate.is_file():
        die(f"candidate does not exist: {candidate}")
    target = profile / "LEARNINGS.md"
    if not target.is_file():
        die(f"missing shared learning file: {target}")
    evidence = args.evidence
    entry = f"""\n### {args.title}\n\n- Category: {args.category}\n- Rule: {args.rule}\n- Evidence: {evidence}\n- Scope: {args.scope}\n- Last verified: {args.date}\n"""
    target.write_text(target.read_text(encoding="utf-8").rstrip() + "\n" + entry, encoding="utf-8")
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
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        cwd = root / config["runtime"].get("workingDirectory", ".")
        process = subprocess.Popen(command, shell=True, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    if not wait_for_port(process, port):
        die(f"preview did not become ready; inspect {log_path}")
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


def dashboard_register(args: argparse.Namespace) -> None:
    from dashboard_server import REGISTRY_PATH, register_project

    entry = register_project(
        project(args.project),
        args.name,
        project_id=args.id,
        description=args.description,
        preview_path=args.preview_path,
        preview_command=args.preview_command,
        isolation=args.isolation,
        registry_path=Path(args.registry).expanduser().resolve() if args.registry else REGISTRY_PATH,
    )
    print(json.dumps(entry, ensure_ascii=False, indent=2))


def dashboard_show(args: argparse.Namespace) -> None:
    from dashboard_server import REGISTRY_PATH, RUNTIME_PATH, load_registry, project_summary

    registry_path = Path(args.registry).expanduser().resolve() if args.registry else REGISTRY_PATH
    registry = load_registry(registry_path)
    projects = [project_summary(entry, RUNTIME_PATH) for entry in registry["projects"]]
    print(json.dumps({"projects": projects}, ensure_ascii=False, indent=2))


def dashboard_start(args: argparse.Namespace) -> None:
    from dashboard_server import DEFAULT_HOME, REGISTRY_PATH, RUNTIME_PATH, is_alive

    DEFAULT_HOME.mkdir(parents=True, exist_ok=True)
    state_path = DEFAULT_HOME / "dashboard.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if is_alive(state.get("pid")):
            print(json.dumps(state, ensure_ascii=False, indent=2))
            if args.open:
                subprocess.Popen(["open", state["url"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        state_path.unlink()
    port = args.port or free_port()
    registry = Path(args.registry).expanduser().resolve() if args.registry else REGISTRY_PATH
    log_path = DEFAULT_HOME / "dashboard.log"
    command = [
        sys.executable,
        str(Path(__file__).with_name("dashboard_server.py")),
        "--port", str(port),
        "--registry", str(registry),
        "--runtime", str(RUNTIME_PATH),
    ]
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    if not wait_for_port(process, port):
        die(f"dashboard did not become ready; inspect {log_path}")
    state = {"pid": process.pid, "url": f"http://127.0.0.1:{port}", "port": port, "registry": str(registry), "log": str(log_path)}
    write_json(state_path, state)
    if args.open:
        subprocess.Popen(["open", state["url"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(json.dumps(state, ensure_ascii=False, indent=2))


def dashboard_stop(args: argparse.Namespace) -> None:
    from dashboard_server import DEFAULT_HOME

    state_path = DEFAULT_HOME / "dashboard.json"
    if not state_path.is_file():
        print("Dashboard is not running.")
        return
    state = json.loads(state_path.read_text(encoding="utf-8"))
    try:
        os.killpg(int(state["pid"]), signal.SIGTERM)
    except ProcessLookupError:
        pass
    state_path.unlink(missing_ok=True)
    print(f"Stopped {state['url']}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="xixi-dev-system")
    sub = parser.add_subparsers(dest="command", required=True)
    onboard_parser = sub.add_parser("onboard")
    for flag, required, default in (("--project", False, "."), ("--name", False, None), ("--repo", False, None), ("--default-branch", False, None), ("--manager", False, None), ("--python", False, None), ("--start-command", False, None), ("--doctor-command", False, None)):
        onboard_parser.add_argument(flag, required=required, default=default)
    onboard_parser.add_argument("--focus-author", action="append", default=[])
    onboard_parser.add_argument("--risk-path", action="append", default=["auth", "payment", "migration", "deploy", "secret"])
    onboard_parser.set_defaults(func=onboard)
    profile_parser = sub.add_parser("profile"); profile_sub = profile_parser.add_subparsers(required=True)
    sync_parser = profile_sub.add_parser("sync"); sync_parser.add_argument("--target"); sync_parser.add_argument("--repo"); sync_parser.set_defaults(func=profile_sync)
    doctor_parser = sub.add_parser("doctor"); doctor_parser.add_argument("--project", required=True); doctor_parser.set_defaults(func=doctor)
    projects_parser = sub.add_parser("projects"); projects_sub = projects_parser.add_subparsers(required=True)
    discover_parser = projects_sub.add_parser("discover"); discover_parser.add_argument("--owner", required=True); discover_parser.add_argument("--root", action="append", required=True); discover_parser.add_argument("--max-depth", type=int, default=6); discover_parser.add_argument("--output"); discover_parser.set_defaults(func=projects_discover)
    updates_parser = sub.add_parser("updates"); updates_parser.add_argument("--project", required=True); updates_parser.add_argument("--date", default=dt.date.today().isoformat()); updates_parser.set_defaults(func=updates)
    runtime_parser = sub.add_parser("runtime"); runtime_sub = runtime_parser.add_subparsers(required=True)
    prepare_parser = runtime_sub.add_parser("prepare"); prepare_parser.add_argument("--project", required=True); prepare_parser.add_argument("--name"); prepare_parser.set_defaults(func=runtime_prepare)
    workspace_parser = sub.add_parser("workspace"); workspace_sub = workspace_parser.add_subparsers(required=True)
    create_parser = workspace_sub.add_parser("create"); create_parser.add_argument("--project", required=True); create_parser.add_argument("--branch", required=True); create_parser.add_argument("--base", default="origin/main"); create_parser.set_defaults(func=workspace_create)
    automation_parser = sub.add_parser("automation"); automation_sub = automation_parser.add_subparsers(required=True)
    install_parser = automation_sub.add_parser("install"); install_parser.add_argument("--project", required=True); install_parser.add_argument("--force", action="store_true"); install_parser.set_defaults(func=automation_install)
    learning_automation_parser = automation_sub.add_parser("ensure-learning"); learning_automation_parser.add_argument("--workspace", required=True); learning_automation_parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))); learning_automation_parser.set_defaults(func=automation_learning_ensure)
    review_parser = sub.add_parser("weekly-review"); review_parser.add_argument("--project", required=True); review_parser.add_argument("--date", default=dt.date.today().isoformat()); review_parser.set_defaults(func=weekly_review)
    acceptance_parser = sub.add_parser("acceptance"); acceptance_parser.add_argument("--project", required=True); acceptance_parser.add_argument("--date", default=dt.date.today().isoformat()); acceptance_parser.set_defaults(func=acceptance)
    learning_parser = sub.add_parser("learning"); learning_sub = learning_parser.add_subparsers(required=True)
    candidate_parser = learning_sub.add_parser("candidate"); candidate_parser.add_argument("--project", required=True); candidate_parser.add_argument("--date", default=dt.date.today().isoformat()); candidate_parser.add_argument("--force", action="store_true"); candidate_parser.set_defaults(func=learning_candidate)
    portfolio_parser = learning_sub.add_parser("portfolio"); portfolio_parser.add_argument("--owner", required=True); portfolio_parser.add_argument("--project", action="append", required=True); portfolio_parser.add_argument("--output", required=True); portfolio_parser.set_defaults(func=learning_portfolio)
    harvest_parser = learning_sub.add_parser("harvest"); harvest_parser.add_argument("--owner", required=True); harvest_parser.add_argument("--project", action="append", required=True); harvest_parser.add_argument("--registry", required=True); harvest_parser.add_argument("--excerpt-chars", type=int, default=1200); harvest_parser.set_defaults(func=learning_harvest)
    review_learning_parser = learning_sub.add_parser("review"); review_learning_parser.add_argument("--owner", required=True); review_learning_parser.add_argument("--registry", required=True); review_learning_parser.add_argument("--candidate-id", required=True); review_learning_parser.add_argument("--supporting-id", action="append", default=[]); review_learning_parser.add_argument("--decision", choices=["promote", "keep-project", "reject"], required=True); review_learning_parser.add_argument("--reviewer", required=True); review_learning_parser.add_argument("--reason", required=True); review_learning_parser.add_argument("--impact", choices=["low", "medium", "high"], required=True); review_learning_parser.add_argument("--scope", default=""); review_learning_parser.add_argument("--rule", default=""); review_learning_parser.add_argument("--verification", default=""); review_learning_parser.add_argument("--owner-corrected", action="store_true"); review_learning_parser.set_defaults(func=learning_review)
    publish_parser = learning_sub.add_parser("publish"); publish_parser.add_argument("--owner", required=True); publish_parser.add_argument("--registry", required=True); publish_parser.add_argument("--candidate-id", required=True); publish_parser.add_argument("--profile", required=True); publish_parser.set_defaults(func=learning_publish)
    promote_parser = learning_sub.add_parser("promote"); promote_parser.add_argument("--candidate", required=True); promote_parser.add_argument("--profile", required=True); promote_parser.add_argument("--title", required=True); promote_parser.add_argument("--category", required=True); promote_parser.add_argument("--rule", required=True); promote_parser.add_argument("--scope", required=True); promote_parser.add_argument("--evidence", required=True); promote_parser.add_argument("--date", default=dt.date.today().isoformat()); promote_parser.set_defaults(func=learning_promote)
    preview_parser = sub.add_parser("preview"); preview_sub = preview_parser.add_subparsers(required=True)
    start_parser = preview_sub.add_parser("start"); start_parser.add_argument("--project", required=True); start_parser.add_argument("--name"); start_parser.add_argument("--command"); start_parser.add_argument("--data-namespace"); start_parser.set_defaults(func=preview_start)
    stop_parser = preview_sub.add_parser("stop"); stop_parser.add_argument("--project", required=True); stop_parser.add_argument("--name"); stop_parser.set_defaults(func=preview_stop)
    dashboard_parser = sub.add_parser("dashboard"); dashboard_sub = dashboard_parser.add_subparsers(required=True)
    dashboard_register_parser = dashboard_sub.add_parser("register"); dashboard_register_parser.add_argument("--project", required=True); dashboard_register_parser.add_argument("--name", required=True); dashboard_register_parser.add_argument("--id"); dashboard_register_parser.add_argument("--description", default=""); dashboard_register_parser.add_argument("--preview-path", default="/"); dashboard_register_parser.add_argument("--preview-command", default=""); dashboard_register_parser.add_argument("--isolation", choices=["namespace", "shared", "frontend-only"], default="namespace"); dashboard_register_parser.add_argument("--registry"); dashboard_register_parser.set_defaults(func=dashboard_register)
    dashboard_show_parser = dashboard_sub.add_parser("show"); dashboard_show_parser.add_argument("--registry"); dashboard_show_parser.set_defaults(func=dashboard_show)
    dashboard_start_parser = dashboard_sub.add_parser("start"); dashboard_start_parser.add_argument("--port", type=int); dashboard_start_parser.add_argument("--registry"); dashboard_start_parser.add_argument("--open", action="store_true"); dashboard_start_parser.set_defaults(func=dashboard_start)
    dashboard_stop_parser = dashboard_sub.add_parser("stop"); dashboard_stop_parser.set_defaults(func=dashboard_stop)
    goal_parser = sub.add_parser("goal"); goal_sub = goal_parser.add_subparsers(required=True)
    goal_create_parser = goal_sub.add_parser("create"); goal_create_parser.add_argument("--project", default="."); goal_create_parser.add_argument("--spec", required=True); goal_create_parser.set_defaults(func=goal_create)
    goal_show_parser = goal_sub.add_parser("show"); goal_show_parser.add_argument("--project", default="."); goal_show_parser.add_argument("--goal"); goal_show_parser.set_defaults(func=goal_show)
    goal_lint_parser = goal_sub.add_parser("lint"); goal_lint_parser.add_argument("--document", required=True); goal_lint_parser.add_argument("--spec", required=True); goal_lint_parser.set_defaults(func=goal_lint)
    goal_task_parser = goal_sub.add_parser("task"); goal_task_sub = goal_task_parser.add_subparsers(required=True)
    task_start_parser = goal_task_sub.add_parser("start"); task_start_parser.add_argument("--project", default="."); task_start_parser.add_argument("--goal", required=True); task_start_parser.add_argument("--task", required=True); task_start_parser.set_defaults(func=goal_task_start)
    task_verify_parser = goal_task_sub.add_parser("verify"); task_verify_parser.add_argument("--project", default="."); task_verify_parser.add_argument("--goal", required=True); task_verify_parser.add_argument("--task", required=True); task_verify_parser.add_argument("--evidence-type", choices=sorted(EVIDENCE_TYPES), required=True); task_verify_parser.add_argument("--evidence", required=True); task_verify_parser.set_defaults(func=goal_task_verify)
    for action in ("block", "fail"):
        task_stop_parser = goal_task_sub.add_parser(action); task_stop_parser.add_argument("--project", default="."); task_stop_parser.add_argument("--goal", required=True); task_stop_parser.add_argument("--task", required=True); task_stop_parser.add_argument("--reason", required=True); task_stop_parser.set_defaults(func=goal_task_stop, status="blocked" if action == "block" else "failed")
    args = parser.parse_args(); args.func(args)


if __name__ == "__main__":
    main()
