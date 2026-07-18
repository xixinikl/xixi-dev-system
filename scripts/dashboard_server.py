#!/usr/bin/env python3
"""Local project and branch preview dashboard for Xixi Dev System."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


SCHEMA_VERSION = 1
DEFAULT_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "xixi-dev-system"
REGISTRY_PATH = DEFAULT_HOME / "dashboard-projects.json"
RUNTIME_PATH = DEFAULT_HOME / "dashboard-runtime"
ASSET_PATH = Path(__file__).resolve().parents[1] / "web" / "dashboard"
PROCESS_HANDLES: dict[str, subprocess.Popen] = {}
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
DASHBOARD_REQUEST_HEADER = "X-XDS-Dashboard"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path, default: object) -> object:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def is_loopback_host_header(value: str) -> bool:
    try:
        hostname = urlparse(f"//{value.strip()}").hostname
    except ValueError:
        return False
    return bool(hostname and hostname.lower().rstrip(".") in LOOPBACK_HOSTS)


def validate_bind_host(host: str) -> None:
    if host.lower().rstrip(".") not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("dashboard may bind only to 127.0.0.1 or localhost")


def run(*command: str, cwd: Path | None = None, check: bool = True) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result.stdout.strip()


def git(root: Path, *arguments: str, check: bool = True) -> str:
    return run("git", "-C", str(root), *arguments, check=check)


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-.").lower()
    return cleaned or hashlib.sha256(value.encode()).hexdigest()[:10]


def is_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def free_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


def wait_for_port(process: subprocess.Popen, port: int, attempts: int = 100) -> bool:
    for _ in range(attempts):
        if process.poll() is not None:
            return False
        with socket.socket() as client:
            client.settimeout(0.1)
            if client.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.1)
    return False


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    payload = read_json(path, {"schemaVersion": SCHEMA_VERSION, "projects": []})
    if not isinstance(payload, dict) or not isinstance(payload.get("projects"), list):
        raise RuntimeError(f"invalid dashboard registry: {path}")
    return payload


def register_project(
    root: Path,
    name: str,
    project_id: str | None = None,
    description: str = "",
    preview_path: str = "/",
    preview_command: str = "",
    isolation: str = "namespace",
    registry_path: Path = REGISTRY_PATH,
) -> dict:
    root = root.expanduser().resolve()
    if not (root / ".git").exists():
        raise RuntimeError(f"not a Git working copy: {root}")
    if not (root / ".xixi-dev-system.json").is_file():
        raise RuntimeError(f"missing .xixi-dev-system.json: {root}")
    registry = load_registry(registry_path)
    entry = {
        "id": project_id or safe_id(root.name),
        "name": name,
        "description": description,
        "path": str(root),
        "previewPath": preview_path if preview_path.startswith("/") else f"/{preview_path}",
        "previewCommand": preview_command,
        "isolation": isolation,
    }
    registry["projects"] = [item for item in registry["projects"] if item.get("id") != entry["id"]]
    registry["projects"].append(entry)
    write_json(registry_path, registry)
    return entry


def parse_worktrees(root: Path) -> dict[str, Path]:
    lines = git(root, "worktree", "list", "--porcelain").splitlines()
    mapping: dict[str, Path] = {}
    current_path: Path | None = None
    for line in lines + [""]:
        if line.startswith("worktree "):
            current_path = Path(line[9:])
        elif line.startswith("branch refs/heads/") and current_path:
            mapping[line.removeprefix("branch refs/heads/")] = current_path
        elif not line:
            current_path = None
    return mapping


def branches(root: Path, limit: int = 12) -> list[dict]:
    template = "%(refname)|%(objectname:short)|%(committerdate:iso8601-strict)|%(subject)"
    output = git(root, "for-each-ref", "--sort=-committerdate", f"--format={template}", "refs/heads", "refs/remotes/origin")
    current = git(root, "branch", "--show-current", check=False)
    worktrees = parse_worktrees(root)
    seen: set[str] = set()
    values = []
    for line in output.splitlines():
        ref, sha, committed_at, subject = (line.split("|", 3) + ["", "", "", ""])[:4]
        if ref.endswith("/HEAD"):
            continue
        name = ref.removeprefix("refs/heads/").removeprefix("refs/remotes/origin/")
        if name in seen:
            continue
        seen.add(name)
        values.append({
            "name": name,
            "sha": sha,
            "subject": subject,
            "committedAt": committed_at,
            "current": name == current,
            "checkedOut": str(worktrees[name]) if name in worktrees else "",
        })
        if len(values) >= limit:
            break
    return values


def preview_key(project_id: str, branch: str) -> str:
    digest = hashlib.sha256(branch.encode()).hexdigest()[:8]
    return f"{safe_id(project_id)}-{safe_id(branch)[:36]}-{digest}"


def preview_state(project_id: str, branch: str, runtime_path: Path = RUNTIME_PATH) -> dict | None:
    path = runtime_path / f"{preview_key(project_id, branch)}.json"
    state = read_json(path, None)
    if not isinstance(state, dict):
        return None
    if not is_alive(state.get("pid")):
        path.unlink(missing_ok=True)
        return None
    return state


def project_summary(entry: dict, runtime_path: Path = RUNTIME_PATH) -> dict:
    root = Path(entry["path"])
    if not root.is_dir():
        return {**entry, "available": False, "error": "本机项目目录不存在", "branches": []}
    branch_values = branches(root)
    for item in branch_values:
        item["preview"] = preview_state(entry["id"], item["name"], runtime_path)
    current = next((item for item in branch_values if item["current"]), branch_values[0] if branch_values else None)
    return {
        **entry,
        "available": True,
        "dirty": bool(git(root, "status", "--porcelain", check=False)),
        "currentBranch": current,
        "branches": branch_values,
    }


def resolve_branch_root(root: Path, branch: str) -> tuple[Path, bool]:
    worktrees = parse_worktrees(root)
    if branch in worktrees:
        return worktrees[branch], False
    local_ref = git(root, "show-ref", "--verify", f"refs/heads/{branch}", check=False)
    remote_ref = git(root, "show-ref", "--verify", f"refs/remotes/origin/{branch}", check=False)
    if not local_ref and not remote_ref:
        raise RuntimeError(f"branch not found: {branch}")
    target = root / ".xds" / "worktrees" / f"preview-{safe_id(branch)}-{hashlib.sha256(branch.encode()).hexdigest()[:8]}"
    if target.exists():
        return target, True
    ref = branch if local_ref else f"origin/{branch}"
    target.parent.mkdir(parents=True, exist_ok=True)
    git(root, "worktree", "add", "--detach", str(target), ref)
    return target, True


def command_for(entry: dict, root: Path) -> tuple[str, dict]:
    adapter = json.loads((Path(entry["path"]) / ".xixi-dev-system.json").read_text(encoding="utf-8"))
    runtime = adapter.get("runtime", {})
    command = entry.get("previewCommand") or runtime.get("previewCommand") or runtime.get("startCommand")
    if not command:
        raise RuntimeError("项目尚未配置预览命令")
    return command, adapter


def same_file(left: Path, right: Path) -> bool:
    return left.is_file() and right.is_file() and hashlib.sha256(left.read_bytes()).digest() == hashlib.sha256(right.read_bytes()).digest()


def prepare_dependencies(source: Path, branch_root: Path) -> None:
    if not (branch_root / "package.json").is_file() or (branch_root / "node_modules").exists():
        return
    source_modules = source / "node_modules"
    lock_names = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock")
    matching_lock = any(same_file(source / name, branch_root / name) for name in lock_names)
    if source_modules.is_dir() and matching_lock:
        (branch_root / "node_modules").symlink_to(source_modules, target_is_directory=True)
        return
    if (branch_root / "pnpm-lock.yaml").is_file():
        command = ["pnpm", "install", "--frozen-lockfile"]
    elif (branch_root / "yarn.lock").is_file():
        command = ["yarn", "install", "--frozen-lockfile"]
    elif (branch_root / "package-lock.json").is_file():
        command = ["npm", "ci", "--no-audit", "--no-fund"]
    else:
        command = ["npm", "install", "--no-audit", "--no-fund"]
    result = subprocess.run(command, cwd=branch_root, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"依赖准备失败：{result.stderr.strip() or result.stdout.strip()}")


def start_preview(entry: dict, branch: str, runtime_path: Path = RUNTIME_PATH) -> dict:
    existing = preview_state(entry["id"], branch, runtime_path)
    if existing:
        return existing
    source = Path(entry["path"])
    branch_root, detached = resolve_branch_root(source, branch)
    prepare_dependencies(source, branch_root)
    command, adapter = command_for(entry, branch_root)
    port = free_port()
    namespace = f"xds-{safe_id(entry['id'])}-{safe_id(branch)}-{hashlib.sha256(branch.encode()).hexdigest()[:6]}"
    env = os.environ.copy()
    runtime = adapter.get("runtime", {})
    env[runtime.get("portEnvironment", "PORT")] = str(port)
    env[runtime.get("dataNamespaceEnvironment", "XDS_DATA_NAMESPACE")] = namespace
    for key, value in adapter.get("data", {}).get("environment", {}).items():
        expanded = str(value).replace("{namespace}", namespace)
        data_path = Path(expanded)
        if not data_path.is_absolute():
            data_path = branch_root / data_path
        data_path.parent.mkdir(parents=True, exist_ok=True)
        env[key] = str(data_path)
    key = preview_key(entry["id"], branch)
    runtime_path.mkdir(parents=True, exist_ok=True)
    log_path = runtime_path / f"{key}.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=branch_root / runtime.get("workingDirectory", "."),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    if not wait_for_port(process, port):
        detail = log_path.read_text(encoding="utf-8", errors="replace")[-1200:]
        raise RuntimeError(f"预览没有在分配端口启动。\n{detail}".strip())
    preview_path = entry.get("previewPath", "/")
    state = {
        "pid": process.pid,
        "url": f"http://127.0.0.1:{port}{preview_path}",
        "port": port,
        "projectId": entry["id"],
        "branch": branch,
        "worktree": str(branch_root),
        "detachedWorktree": detached,
        "dataNamespace": namespace,
        "isolation": entry.get("isolation", "namespace"),
        "log": str(log_path),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    PROCESS_HANDLES[key] = process
    write_json(runtime_path / f"{key}.json", state)
    return state


def stop_preview(entry: dict, branch: str, runtime_path: Path = RUNTIME_PATH) -> None:
    key = preview_key(entry["id"], branch)
    path = runtime_path / f"{key}.json"
    state = read_json(path, None)
    if not isinstance(state, dict):
        return
    try:
        os.killpg(int(state["pid"]), signal.SIGTERM)
    except ProcessLookupError:
        pass
    process = PROCESS_HANDLES.pop(key, None)
    if process:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
    path.unlink(missing_ok=True)


class DashboardHandler(BaseHTTPRequestHandler):
    registry_path = REGISTRY_PATH
    runtime_path = RUNTIME_PATH

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"dashboard: {fmt % args}\n")

    def json_response(self, value: object, status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def allow_local_request(self) -> bool:
        if is_loopback_host_header(self.headers.get("Host", "")):
            return True
        self.json_response({"error": "仅允许从本机回环地址访问"}, HTTPStatus.FORBIDDEN)
        return False

    def registry_entry(self, project_id: str) -> dict:
        registry = load_registry(self.registry_path)
        entry = next((item for item in registry["projects"] if item.get("id") == project_id), None)
        if not entry:
            raise RuntimeError("项目未注册")
        return entry

    def do_GET(self) -> None:
        if not self.allow_local_request():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/projects":
            registry = load_registry(self.registry_path)
            projects = [project_summary(item, self.runtime_path) for item in registry["projects"]]
            self.json_response({"projects": projects})
            return
        asset_name = "index.html" if parsed.path == "/" else unquote(parsed.path.lstrip("/"))
        asset = (ASSET_PATH / asset_name).resolve()
        if ASSET_PATH not in asset.parents and asset != ASSET_PATH:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not asset.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        mime = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}.get(asset.suffix, "application/octet-stream")
        body = asset.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{mime}; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if not self.allow_local_request():
            return
        if self.headers.get(DASHBOARD_REQUEST_HEADER) != "1":
            self.json_response({"error": "缺少本地控制请求标记"}, HTTPStatus.FORBIDDEN)
            return
        match = re.fullmatch(r"/api/projects/([^/]+)/branches/(.+)/(start|stop)", urlparse(self.path).path)
        if not match:
            self.json_response({"error": "接口不存在"}, 404)
            return
        project_id, encoded_branch, action = match.groups()
        branch = unquote(encoded_branch)
        try:
            entry = self.registry_entry(project_id)
            if action == "start":
                state = start_preview(entry, branch, self.runtime_path)
                self.json_response({"preview": state})
            else:
                stop_preview(entry, branch, self.runtime_path)
                self.json_response({"stopped": True})
        except Exception as error:
            self.json_response({"error": str(error)}, 400)


def serve(host: str, port: int, registry: Path = REGISTRY_PATH, runtime: Path = RUNTIME_PATH) -> None:
    validate_bind_host(host)
    handler = type("ConfiguredDashboardHandler", (DashboardHandler,), {"registry_path": registry, "runtime_path": runtime})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Xixi project preview center: http://{host}:{port}", flush=True)
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--runtime", type=Path, default=RUNTIME_PATH)
    args = parser.parse_args()
    serve(args.host, args.port, args.registry.expanduser().resolve(), args.runtime.expanduser().resolve())


if __name__ == "__main__":
    main()
