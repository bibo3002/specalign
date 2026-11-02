import _path  # noqa: F401  (puts tools/ on sys.path)

import re
import unittest
from pathlib import Path

from specalign import evals

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "evals" / "examples"


class ScenarioFileTests(unittest.TestCase):
    def setUp(self):
        self.scenarios = evals.load_scenarios(ROOT)

    def test_every_matrix_row_has_exactly_one_scenario(self):
        playbook = (ROOT / "references" / "verification-playbook.md").read_text(encoding="utf-8")
        rows = {int(m.group(1)) for m in re.finditer(r"(?m)^\| (\d+) \|", playbook)}
        ids = [s["id"] for s in self.scenarios]
        self.assertEqual(sorted(ids), sorted(set(ids)), "duplicate scenario ids")
        self.assertEqual(set(ids), rows)

    def test_every_referenced_test_exists(self):
        import importlib
        import sys
        sys.path.insert(0, str(ROOT / "tests"))
        loader = unittest.defaultTestLoader
        for sc in self.scenarios:
            for name in sc.get("tests", []):
                suite = loader.loadTestsFromName(name)
                self.assertEqual(suite.countTestCases(), 1, f"scenario {sc['id']}: no such test {name}")

    def test_tool_scenarios_name_tests_and_transcript_scenarios_name_rules(self):
        for sc in self.scenarios:
            if sc["kind"] == "tool":
                self.assertTrue(sc["tests"], sc["id"])
            else:
                self.assertTrue(sc["must"] or sc["must_not"], sc["id"])

    def test_every_regex_compiles(self):
        for sc in self.scenarios:
            for pat in sc.get("must", []) + sc.get("must_not", []) + [p for pair in sc.get("order", []) for p in pair]:
                re.compile(pat)


class GraderTests(unittest.TestCase):
    """The example transcripts are not evidence about any model; they prove the graders tell good from bad."""

    def setUp(self):
        self.by_id = {s["id"]: s for s in evals.load_scenarios(ROOT)}

    def test_good_examples_pass_and_bad_examples_fail(self):
        goods = sorted(EXAMPLES.glob("*-good.txt"))
        self.assertGreaterEqual(len(goods), 3)
        for good in goods:
            sid = int(good.name.split("-")[0])
            ok, problems = evals.grade(self.by_id[sid], good.read_text(encoding="utf-8"))
            self.assertTrue(ok, f"{good.name}: {problems}")
        bads = sorted(EXAMPLES.glob("*-bad.txt"))
        self.assertGreaterEqual(len(bads), 9)
        for bad in bads:
            ok, _ = evals.grade(self.by_id[int(bad.name.split("-")[0])], bad.read_text(encoding="utf-8"))
            self.assertFalse(ok, f"{bad.name} should fail the grader")

    def test_every_revised_rule_still_rejects_wrong_behaviour(self):
        revised = {s["id"] for s in self.by_id.values() if "rule_revision" in s}
        rejected = {int(p.name.split("-")[0]) for p in EXAMPLES.glob("*-bad.txt")}
        self.assertEqual(revised - rejected, set(), "each revised rule needs a bad example that it rejects")

    def test_recorded_runs_pass_their_rules(self):
        run = ROOT / "evals" / "runs" / "2026-11-02"
        files = sorted(run.glob("*.txt"))
        self.assertEqual(len(files), 17)
        for f in files:
            ok, problems = evals.grade(self.by_id[int(f.stem)], f.read_text(encoding="utf-8"))
            self.assertTrue(ok, f"{f.name}: {problems}")

    def test_order_rule(self):
        sc = {"must": [], "must_not": [], "order": [["APPROVED", "DROP TABLE"]]}
        self.assertTrue(evals.grade(sc, "APPROVED\nDROP TABLE x")[0])
        self.assertFalse(evals.grade(sc, "DROP TABLE x\nAPPROVED")[0])
        self.assertTrue(evals.grade(sc, "nothing risky")[0])

    def test_runner_reports_not_exercised_without_transcripts_and_runs_tool_scenarios(self):
        results = evals.run(ROOT, None, only=[18, 21])
        self.assertEqual(results[0].status, "pass")                 # 18 is a tool scenario
        self.assertEqual(results[1].status, "not-exercised")        # 21 has a mechanical guard but no transcript
        self.assertIn("mechanical guard passes", results[1].detail)

    def test_runner_grades_a_transcript_directory(self):
        results = evals.run(ROOT, EXAMPLES.parent / "examples", only=[26])
        self.assertEqual(results[0].status, "not-exercised")        # files there are named 26-good.txt, not 26.txt


if __name__ == "__main__":
    unittest.main()
