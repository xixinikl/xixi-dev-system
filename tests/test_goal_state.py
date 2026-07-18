import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import xds


class GoalStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.spec = self.root / "goal.json"
        self.spec.write_text(json.dumps({
            "id": "demo-goal",
            "title": "Demo goal",
            "objective": "Prove the goal state lifecycle.",
            "tasks": [
                {"id": "T1", "title": "First", "acceptance": "First is verified."},
                {"id": "T2", "title": "Second", "acceptance": "Second is verified.", "dependsOn": ["T1"]},
            ],
        }), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            xds.goal_create(argparse.Namespace(project=str(self.root), spec=str(self.spec)))

    def tearDown(self):
        self.temp.cleanup()

    def args(self, **overrides):
        values = {"project": str(self.root), "goal": "demo-goal", "task": "T1"}
        values.update(overrides)
        return argparse.Namespace(**values)

    def state(self):
        return json.loads((self.root / ".xds/goals/demo-goal.json").read_text(encoding="utf-8"))

    def test_progress_is_derived_only_from_verified_tasks(self):
        with contextlib.redirect_stdout(io.StringIO()):
            xds.goal_task_start(self.args())
        self.assertEqual(self.state()["progress"], {"verified": 0, "total": 2, "percent": 0})

        with contextlib.redirect_stdout(io.StringIO()):
            xds.goal_task_verify(self.args(evidence_type="test", evidence="2 tests passed"))
        state = self.state()
        self.assertEqual(state["progress"], {"verified": 1, "total": 2, "percent": 50})
        self.assertEqual(state["nextTaskId"], "T2")
        self.assertEqual(state["tasks"][0]["evidence"][0]["type"], "test")

    def test_dependency_and_single_running_task_are_enforced(self):
        with self.assertRaises(SystemExit):
            xds.goal_task_start(self.args(task="T2"))
        with contextlib.redirect_stdout(io.StringIO()):
            xds.goal_task_start(self.args(task="T1"))
        with self.assertRaises(SystemExit):
            xds.goal_task_start(self.args(task="T2"))

    def test_verify_requires_running_task_and_evidence(self):
        with self.assertRaises(SystemExit):
            xds.goal_task_verify(self.args(evidence_type="test", evidence="pass"))
        with contextlib.redirect_stdout(io.StringIO()):
            xds.goal_task_start(self.args())
        with self.assertRaises(SystemExit):
            xds.goal_task_verify(self.args(evidence_type="test", evidence=" "))

    def test_blocked_task_records_reason_and_stops_progress(self):
        with contextlib.redirect_stdout(io.StringIO()):
            xds.goal_task_start(self.args())
            xds.goal_task_stop(self.args(status="blocked", reason="Missing API access"))
        state = self.state()
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["blockers"][0]["taskId"], "T1")
        self.assertEqual(state["progress"]["percent"], 0)

    def test_goal_becomes_verified_when_every_task_has_evidence(self):
        with contextlib.redirect_stdout(io.StringIO()):
            xds.goal_task_start(self.args(task="T1"))
            xds.goal_task_verify(self.args(task="T1", evidence_type="test", evidence="first passed"))
            xds.goal_task_start(self.args(task="T2"))
            xds.goal_task_verify(self.args(task="T2", evidence_type="url", evidence="https://example.test"))
        state = self.state()
        self.assertEqual(state["status"], "verified")
        self.assertEqual(state["progress"]["percent"], 100)
        self.assertIsNone(state["nextTaskId"])

    def test_cycle_is_rejected(self):
        bad = {
            "id": "cycle", "title": "Cycle", "objective": "Reject cycles.",
            "tasks": [
                {"id": "A", "title": "A", "acceptance": "A", "dependsOn": ["B"]},
                {"id": "B", "title": "B", "acceptance": "B", "dependsOn": ["A"]},
            ],
        }
        with self.assertRaises(SystemExit):
            xds.validate_goal_spec(bad)


if __name__ == "__main__":
    unittest.main()
