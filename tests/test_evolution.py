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
import bootstrap_system


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

    def test_retrospective_harvest_is_structured_idempotent_and_change_aware(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "owned"
            init_repo(root, "https://github.com/xixinikl/owned.git")
            retrospective = root / "错误复盘.md"
            retrospective.write_text("""# 错误复盘

## 2026-07-13 · 不能把检查通过说成全部完成

- 场景：一个窄测试通过。
- 我做错了什么：把窄测试说成全链路完成。
- 用户如何纠正：用户要求直接证据。
- 根因：验证范围和声明范围不一致。
- 以后必须这样做：完成声明必须匹配证据范围。
- 可验证的防复发动作：completion audit逐条映射证据。
""", encoding="utf-8")
            registry = Path(directory) / "registry.json"
            args = argparse.Namespace(owner="xixinikl", project=[str(root)], registry=str(registry), excerpt_chars=500)

            with contextlib.redirect_stdout(io.StringIO()):
                xds.learning_harvest(args)
                xds.learning_harvest(args)
            payload = json.loads(registry.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["candidates"]), 1)
            self.assertEqual(payload["candidates"][0]["status"], "ready_for_review")
            self.assertEqual(payload["runs"][-1]["unchanged"], 1)

            retrospective.write_text(retrospective.read_text(encoding="utf-8").replace("逐条映射证据", "逐条映射同范围证据"), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                xds.learning_harvest(args)
            payload = json.loads(registry.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["candidates"]), 1)
            self.assertEqual(payload["candidates"][0]["status"], "needs_re_review")
            self.assertEqual(payload["runs"][-1]["updated"], 1)

    def test_harvest_marks_incomplete_and_accepts_zero_state(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            incomplete = base / "incomplete"
            empty = base / "empty"
            init_repo(incomplete, "https://github.com/xixinikl/incomplete.git")
            init_repo(empty, "https://github.com/xixinikl/empty.git")
            (incomplete / "错误复盘.md").write_text("# 错误复盘\n\n## 一条残缺记录\n\n- 场景：发生了错误。\n", encoding="utf-8")
            registry = base / "registry.json"
            with contextlib.redirect_stdout(io.StringIO()):
                xds.learning_harvest(argparse.Namespace(owner="xixinikl", project=[str(incomplete), str(empty)], registry=str(registry), excerpt_chars=200))
            payload = json.loads(registry.read_text(encoding="utf-8"))
            self.assertEqual(payload["candidates"][0]["status"], "needs_completion")
            self.assertEqual(set(payload["candidates"][0]["missingFields"]), {"root_cause", "rule", "verification"})
            self.assertEqual(payload["runs"][-1]["sourceSections"], 1)

    def test_harvest_blocks_and_redacts_sensitive_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "owned"
            init_repo(root, "https://github.com/xixinikl/owned.git")
            secret = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
            (root / "错误复盘.md").write_text(f"""# 错误复盘
## 密钥不应进入经验库
- 场景：日志包含 {secret}。
- 根因：没有脱敏。
- 以后必须这样做：发现敏感信息立即阻断。
- 可验证的防复发动作：registry不包含原始密钥。
""", encoding="utf-8")
            registry = Path(directory) / "registry.json"
            with contextlib.redirect_stdout(io.StringIO()):
                xds.learning_harvest(argparse.Namespace(owner="xixinikl", project=[str(root)], registry=str(registry), excerpt_chars=500))
            raw = registry.read_text(encoding="utf-8")
            candidate = json.loads(raw)["candidates"][0]
            self.assertEqual(candidate["status"], "blocked_sensitive")
            self.assertTrue(candidate["sensitiveEvidenceDetected"])
            self.assertNotIn(secret, raw)
            self.assertIn("[REDACTED]", candidate["sourceExcerpt"])

    def test_promotion_requires_review_gate_and_publish_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "owned"
            profile = base / "profile"
            init_repo(root, "https://github.com/xixinikl/owned.git")
            profile.mkdir()
            (profile / "LEARNINGS.md").write_text("# 已验证经验\n", encoding="utf-8")
            (root / "错误复盘.md").write_text("""# 错误复盘
## 高影响纠正
- 场景：错误答案可能给用户使用。
- 用户如何纠正：用户明确要求答案必须回原始证据确认。
- 根因：把派生结果当成事实。
- 以后必须这样做：高风险答案必须核验原始证据。
- 可验证的防复发动作：发布门禁检查原始证据引用。
""", encoding="utf-8")
            registry = base / "registry.json"
            with contextlib.redirect_stdout(io.StringIO()):
                xds.learning_harvest(argparse.Namespace(owner="xixinikl", project=[str(root)], registry=str(registry), excerpt_chars=500))
            candidate_id = json.loads(registry.read_text(encoding="utf-8"))["candidates"][0]["id"]
            values = dict(owner="xixinikl", registry=str(registry), candidate_id=candidate_id, supporting_id=[], decision="promote", reviewer="owner", reason="High impact correction", impact="high", scope="high-risk extraction", rule="Verify original evidence before publication.", verification="Publication gate checks source evidence.", owner_corrected=False)
            with self.assertRaises(SystemExit):
                xds.learning_review(argparse.Namespace(**values))
            values["owner_corrected"] = True
            with contextlib.redirect_stdout(io.StringIO()):
                xds.learning_review(argparse.Namespace(**values))
                xds.learning_publish(argparse.Namespace(owner="xixinikl", registry=str(registry), candidate_id=candidate_id, profile=str(profile)))
                xds.learning_publish(argparse.Namespace(owner="xixinikl", registry=str(registry), candidate_id=candidate_id, profile=str(profile)))
            text = (profile / "LEARNINGS.md").read_text(encoding="utf-8")
            self.assertEqual(text.count(f"xds-learning:{candidate_id}"), 1)
            self.assertEqual(json.loads(registry.read_text(encoding="utf-8"))["candidates"][0]["status"], "published")

    def test_learning_automation_ensure_is_idempotent_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = base / "workspace"
            codex_home = base / "codex"
            workspace.mkdir()
            args = argparse.Namespace(workspace=str(workspace), codex_home=str(codex_home))
            with contextlib.redirect_stdout(io.StringIO()):
                xds.automation_learning_ensure(args)
            target = codex_home / "automations/weekly-personal-dev-system/automation.toml"
            first = target.read_text(encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                xds.automation_learning_ensure(args)
            second = target.read_text(encoding="utf-8")
            self.assertIn('id = "weekly-personal-dev-system"', second)
            self.assertEqual(first.split("created_at = ")[1].splitlines()[0], second.split("created_at = ")[1].splitlines()[0])
            duplicate = codex_home / "automations/duplicate/automation.toml"
            duplicate.parent.mkdir(parents=True)
            duplicate.write_text('name = "每周个人开发系统回顾"\n', encoding="utf-8")
            with self.assertRaises(SystemExit):
                xds.automation_learning_ensure(args)

    def test_bootstrap_uses_the_actual_migrated_automation_path(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = base / "workspace"
            codex_home = base / "codex"
            legacy = codex_home / "automations/legacy-id/automation.toml"
            workspace.mkdir()
            legacy.parent.mkdir(parents=True)
            legacy.write_text('name = "每周个人开发系统回顾"\n', encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                xds.automation_learning_ensure(
                    argparse.Namespace(workspace=str(workspace), codex_home=str(codex_home))
                )

            self.assertEqual(bootstrap_system.automation_path_from_output(output.getvalue()), legacy.resolve())


if __name__ == "__main__":
    unittest.main()
