import json
import http.client
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import dashboard_server as dashboard


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.base = Path(self.directory.name)
        self.root = self.base / "project"
        self.root.mkdir()
        subprocess.run(["git", "init", "-b", "main", self.root], check=True, capture_output=True)
        subprocess.run(["git", "-C", self.root, "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", self.root, "config", "user.name", "Test"], check=True)
        (self.root / "index.html").write_text("<h1>preview</h1>", encoding="utf-8")
        self.adapter = {
            "schemaVersion": 1,
            "projectName": "demo",
            "runtime": {
                "startCommand": 'python3 -m http.server "$PORT" --bind 127.0.0.1',
                "portEnvironment": "PORT",
                "dataNamespaceEnvironment": "XDS_DATA_NAMESPACE",
                "additionalPortEnvironments": ["API_PORT"],
                "updateStrategy": "live-reload",
                "workingDirectory": ".",
            },
        }
        (self.root / ".xixi-dev-system.json").write_text(json.dumps(self.adapter), encoding="utf-8")
        subprocess.run(["git", "-C", self.root, "add", "."], check=True)
        subprocess.run(["git", "-C", self.root, "commit", "-m", "initial"], check=True, capture_output=True)
        subprocess.run(["git", "-C", self.root, "branch", "feature/demo"], check=True)
        self.registry = self.base / "registry.json"
        self.runtime = self.base / "runtime"

    def tearDown(self):
        if self.runtime.is_dir():
            for state_path in self.runtime.glob("*.json"):
                state = json.loads(state_path.read_text(encoding="utf-8"))
                entry = {"id": state["projectId"]}
                dashboard.stop_preview(entry, state["branch"], self.runtime)
        self.directory.cleanup()

    def test_register_and_report_branch_facts(self):
        entry = dashboard.register_project(
            self.root,
            "演示项目",
            project_id="demo",
            description="测试分支预览",
            registry_path=self.registry,
        )
        summary = dashboard.project_summary(entry, self.runtime)

        self.assertEqual(summary["name"], "演示项目")
        self.assertEqual(summary["currentBranch"]["name"], "main")
        self.assertEqual({item["name"] for item in summary["branches"]}, {"main", "feature/demo"})
        self.assertFalse(summary["dirty"])
        self.assertEqual(summary["currentBranch"]["previewMode"], "live")
        self.assertEqual(next(item for item in summary["branches"] if item["name"] == "feature/demo")["previewMode"], "snapshot")

    def test_preview_uses_unique_port_and_namespace_per_branch(self):
        entry = dashboard.register_project(self.root, "演示项目", project_id="demo", registry_path=self.registry)
        main = dashboard.start_preview(entry, "main", self.runtime)
        feature = dashboard.start_preview(entry, "feature/demo", self.runtime)

        self.assertNotEqual(main["port"], feature["port"])
        self.assertNotEqual(main["dataNamespace"], feature["dataNamespace"])
        self.assertNotEqual(main["servicePorts"]["API_PORT"], feature["servicePorts"]["API_PORT"])
        self.assertEqual(main["previewMode"], "live")
        self.assertEqual(feature["previewMode"], "snapshot")
        self.assertEqual(main["updateStrategy"], "live-reload")
        self.assertEqual(Path(main["worktree"]), self.root.resolve())
        self.assertTrue(feature["detachedWorktree"])
        self.assertTrue(Path(feature["worktree"]).is_dir())
        self.assertEqual(dashboard.preview_state("demo", "main", self.runtime)["url"], main["url"])

    def test_register_updates_existing_project_without_duplicates(self):
        dashboard.register_project(self.root, "旧名称", project_id="demo", registry_path=self.registry)
        dashboard.register_project(self.root, "新名称", project_id="demo", registry_path=self.registry)

        registry = dashboard.load_registry(self.registry)
        self.assertEqual(len(registry["projects"]), 1)
        self.assertEqual(registry["projects"][0]["name"], "新名称")

    def test_dependency_reuse_requires_matching_lockfile(self):
        source_modules = self.root / "node_modules"
        source_modules.mkdir()
        (self.root / "package.json").write_text("{}", encoding="utf-8")
        (self.root / "package-lock.json").write_text('{"lockfileVersion": 3}', encoding="utf-8")
        branch_root = self.base / "branch"
        branch_root.mkdir()
        (branch_root / "package.json").write_text("{}", encoding="utf-8")
        (branch_root / "package-lock.json").write_text('{"lockfileVersion": 3}', encoding="utf-8")

        dashboard.prepare_dependencies(self.root, branch_root)

        self.assertTrue((branch_root / "node_modules").is_symlink())
        self.assertEqual((branch_root / "node_modules").resolve(), source_modules.resolve())

    def test_bundled_node_runtime_is_discovered_without_hardcoding_user_path(self):
        home = self.base / "home"
        node = home / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
        node.parent.mkdir(parents=True)
        node.touch()

        self.assertEqual(dashboard.bundled_node_bin(home), node.parent)
        self.assertIsNone(dashboard.bundled_node_bin(self.base / "missing"))

    def test_python_placeholder_requires_prepared_isolated_runtime(self):
        entry = dashboard.register_project(self.root, "演示项目", project_id="python-demo", registry_path=self.registry)
        self.adapter["runtime"]["startCommand"] = "{python} -m http.server $PORT"
        (self.root / ".xixi-dev-system.json").write_text(json.dumps(self.adapter), encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "隔离 Python 尚未准备"):
            dashboard.command_for(entry, self.root)

        python = self.root / ".xds/venvs/default/bin/python"
        python.parent.mkdir(parents=True)
        python.touch()
        command, _ = dashboard.command_for(entry, self.root)
        self.assertIn(str(python), command)

    def test_dashboard_rejects_non_loopback_bind_and_host_headers(self):
        self.assertTrue(dashboard.is_loopback_host_header("127.0.0.1:8080"))
        self.assertTrue(dashboard.is_loopback_host_header("localhost:8080"))
        self.assertFalse(dashboard.is_loopback_host_header("evil.example:8080"))
        with self.assertRaisesRegex(RuntimeError, "bind only"):
            dashboard.validate_bind_host("0.0.0.0")

    def test_dashboard_http_control_requires_local_marker(self):
        handler = type(
            "TestDashboardHandler",
            (dashboard.DashboardHandler,),
            {"registry_path": self.registry, "runtime_path": self.runtime},
        )
        server = dashboard.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/api/projects/demo/branches/main/start"
        try:
            with self.assertRaises(urllib.error.HTTPError) as missing_marker:
                urllib.request.urlopen(urllib.request.Request(url, method="POST"), timeout=2)
            self.assertEqual(missing_marker.exception.code, 403)

            marked = urllib.request.Request(
                url,
                method="POST",
                headers={dashboard.DASHBOARD_REQUEST_HEADER: "1"},
            )
            with self.assertRaises(urllib.error.HTTPError) as unknown_project:
                urllib.request.urlopen(marked, timeout=2)
            self.assertEqual(unknown_project.exception.code, 400)

            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
            connection.request("GET", "/api/projects", headers={"Host": "evil.example"})
            rejected_host = connection.getresponse()
            self.assertEqual(rejected_host.status, 403)
            rejected_host.read()
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
