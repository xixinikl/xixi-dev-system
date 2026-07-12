import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import xds


class OnboardTests(unittest.TestCase):
    def args(self, root: Path, **overrides):
        values = {
            "project": str(root), "name": None, "repo": None,
            "default_branch": None, "manager": None, "python": None,
            "start_command": None, "doctor_command": None,
            "focus_author": [], "risk_path": ["auth", "payment"],
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_static_project_is_detected_without_required_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fresh-site"
            root.mkdir()
            (root / "index.html").write_text("hello", encoding="utf-8")
            subprocess.run(["git", "init", "-b", "main", root], check=True, capture_output=True)
            subprocess.run(["git", "-C", root, "remote", "add", "origin", "https://github.com/xixinikl/fresh-site.git"], check=True)

            xds.onboard(self.args(root))
            config = json.loads((root / xds.CONFIG).read_text(encoding="utf-8"))

            self.assertEqual(config["projectName"], "fresh-site")
            self.assertEqual(config["repository"], "https://github.com/xixinikl/fresh-site.git")
            self.assertIn("http.server", config["runtime"]["startCommand"])
            self.assertEqual(config["runtime"]["doctorCommand"], "git diff --check")
            self.assertEqual(config["quality"]["acceptanceCommand"], "git diff --check")

    def test_node_scripts_and_package_manager_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"scripts": {"dev": "vite", "verify": "node verify.mjs"}}), encoding="utf-8")
            (root / "pnpm-lock.yaml").touch()

            detected = xds.detect_adapter(root)

            self.assertEqual(detected["manager"], "uv")
            self.assertEqual(detected["startCommand"], "pnpm run dev")
            self.assertEqual(detected["doctorCommand"], "pnpm run verify")

    def test_profile_sync_clones_and_fast_forwards(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            remote = base / "profile.git"
            seed = base / "seed"
            target = base / "cache"
            subprocess.run(["git", "init", "--bare", remote], check=True, capture_output=True)
            subprocess.run(["git", "init", "-b", "main", seed], check=True, capture_output=True)
            subprocess.run(["git", "-C", seed, "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", seed, "config", "user.name", "Test"], check=True)
            (seed / "PREFERENCES.md").write_text("fresh", encoding="utf-8")
            subprocess.run(["git", "-C", seed, "add", "PREFERENCES.md"], check=True)
            subprocess.run(["git", "-C", seed, "commit", "-m", "seed"], check=True, capture_output=True)
            subprocess.run(["git", "-C", seed, "remote", "add", "origin", str(remote)], check=True)
            subprocess.run(["git", "-C", seed, "push", "-u", "origin", "main"], check=True, capture_output=True)
            subprocess.run(["git", "-C", remote, "symbolic-ref", "HEAD", "refs/heads/main"], check=True)

            args = argparse.Namespace(target=str(target), repo=str(remote))
            xds.profile_sync(args)
            (seed / "PREFERENCES.md").write_text("fresh and clear", encoding="utf-8")
            subprocess.run(["git", "-C", seed, "commit", "-am", "update"], check=True, capture_output=True)
            subprocess.run(["git", "-C", seed, "push"], check=True, capture_output=True)
            xds.profile_sync(args)

            self.assertEqual((target / "PREFERENCES.md").read_text(encoding="utf-8"), "fresh and clear")


if __name__ == "__main__":
    unittest.main()
