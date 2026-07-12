import argparse
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import xds


def init_repo(path: Path, origin: str) -> None:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main", path], check=True, capture_output=True)
    subprocess.run(["git", "-C", path, "remote", "add", "origin", origin], check=True)


class EvolutionTests(unittest.TestCase):
    def test_owner_discovery_is_local_and_origin_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owned = root / "owned"
            foreign = root / "foreign"
            init_repo(owned, "https://github.com/xixinikl/owned.git")
            init_repo(foreign, "git@github.com:someone/foreign.git")

            result = xds.discover_local_repositories([root], "xixinikl")

            self.assertEqual([item["name"] for item in result], ["owned"])
            self.assertEqual(result[0]["origin"], "https://github.com/xixinikl/owned.git")

    def test_learning_portfolio_indexes_evidence_without_mutating_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "owned"
            init_repo(root, "https://github.com/xixinikl/owned.git")
            (root / "CURRENT_STATUS.md").write_text("# Current\n\n## Verified\n", encoding="utf-8")
            (root / "app.js").write_text("const untouched = true;\n", encoding="utf-8")
            output = Path(directory) / "portfolio.json"
            before = (root / "app.js").read_bytes()

            with contextlib.redirect_stdout(io.StringIO()):
                xds.learning_portfolio(argparse.Namespace(owner="xixinikl", project=[str(root)], output=str(output)))

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["readOnly"])
            self.assertFalse(payload["remoteContentRead"])
            self.assertEqual(payload["projects"][0]["evidence"][0]["path"], "CURRENT_STATUS.md")
            self.assertEqual((root / "app.js").read_bytes(), before)

    def test_goal_lint_accepts_cds_contract_and_rejects_loose_checklist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / "goal.json"
            spec.write_text(json.dumps({
                "id": "demo", "title": "Demo", "objective": "Demo objective",
                "tasks": [{"id": "T1", "title": "Audit", "acceptance": "Evidence exists."}],
            }), encoding="utf-8")
            complete = root / "complete.md"
            complete.write_text("""# Goal\n\n唯一权威入口\n\n## 当前事实\n## 范围\n### 不包含\n## 阶段计划与证据\nT1\n## 停止条件\n## Completion Audit\n## 开 Goal 目标文本\n""", encoding="utf-8")
            loose = root / "loose.md"
            loose.write_text("# Tasks\n- T1 do it\n", encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                xds.goal_lint(argparse.Namespace(document=str(complete), spec=str(spec)))
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stdout(io.StringIO()):
                    xds.goal_lint(argparse.Namespace(document=str(loose), spec=str(spec)))


if __name__ == "__main__":
    unittest.main()
