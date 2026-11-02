import _path  # noqa: F401  (puts tools/ on sys.path)

import json
import tempfile
import unittest
from pathlib import Path

from fixture import Repo
from specalign import finalize, manifest
from specalign.common import SpecAlignError
from test_lint import make_spec

TAG = "spec/F1-demo-v1.0.0"
SPEC = "docs/specs/SPEC-F1-demo.md"
INDEX = "docs/specs/INDEX.md"


class FinalizeTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.cleanup)
        self.p = self.repo.path
        self.repo.write(SPEC, make_spec(status="Draft", tag=TAG))
        self.repo.write_index_row("F1", "demo", "Draft", "1.0.0", "—")
        self.repo.commit("draft F1")
        self.plan = {
            "schema": finalize.SCHEMA,
            "edits": [
                {"file": SPEC, "op": "set-card", "field": "Status", "value": "Approved"},
                {"file": SPEC, "op": "append-row", "section": "13D",
                 "cells": ["v1.0.0", "G1", "me", "2026-01-02", "§13B D-1", "«approve the write, tags and push»"]},
                {"file": INDEX, "op": "patch-row", "match": {"ID": "F1"}, "set": {"Status": "Approved", "Tag": TAG}},
            ],
            "expect_files": [SPEC, INDEX],
            "tags": [TAG],
        }
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.plan_path = Path(tmp.name) / "plan.json"      # outside the repo: editing it must not dirty the tree
        self.write_plan()
        manifest.init(self.p, "docs/specs", "F1", "sync", "Core", date="2026-01-02")

    def write_plan(self):
        self.plan_path.write_text(json.dumps(self.plan, ensure_ascii=False), encoding="utf-8")

    def approve(self, gate, statement, reply="yes"):
        manifest.approve(self.p, gate, statement, reply)

    # ----------------------------------------------------------------------------- plan
    def test_plan_is_a_dry_run(self):
        before = (self.p / SPEC).read_bytes()
        rep = finalize.plan_report(self.p, self.plan_path)
        self.assertTrue(rep["ok"], rep["problems"])
        self.assertEqual(rep["changed"], sorted([SPEC, INDEX]))
        self.assertIn("+| Status | Approved |", rep["diffs"][SPEC])
        self.assertEqual((self.p / SPEC).read_bytes(), before)

    def test_edits_outside_expect_files_are_a_problem(self):
        self.plan["expect_files"] = [SPEC]
        self.write_plan()
        rep = finalize.plan_report(self.p, self.plan_path)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("not in expect_files" in x for x in rep["problems"]))

    def test_result_that_fails_lint_blocks_the_plan(self):
        self.repo.write(SPEC, make_spec(status="Draft", tag=TAG, df_status="Open"))
        rep = finalize.plan_report(self.p, self.plan_path)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("would fail lint" in x and "L04" in x for x in rep["problems"]))

    def test_tag_must_use_the_prefix_and_not_exist(self):
        self.plan["tags"] = ["F1-demo-v1.0.0"]
        self.write_plan()
        self.assertFalse(finalize.plan_report(self.p, self.plan_path)["ok"])
        self.repo.tag(TAG)
        self.plan["tags"] = [TAG]
        self.write_plan()
        self.assertTrue(any("already exists" in x for x in finalize.plan_report(self.p, self.plan_path)["problems"]))

    def test_bad_plan_files(self):
        self.plan_path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(SpecAlignError):
            finalize.load_plan(self.plan_path)
        self.plan_path.write_text(json.dumps({"schema": "x"}), encoding="utf-8")
        with self.assertRaises(SpecAlignError):
            finalize.load_plan(self.plan_path)
        self.plan["edits"][0]["file"] = "docs/specs/SPEC-F9-none.md"
        self.write_plan()
        with self.assertRaises(SpecAlignError):
            finalize.plan_report(self.p, self.plan_path)

    # ----------------------------------------------------------------------------- apply
    def test_apply_needs_a_closed_write_gate_naming_every_file(self):
        with self.assertRaises(SpecAlignError) as cm:
            finalize.apply_plan(self.p, self.plan_path)
        self.assertIn("W1/C1", str(cm.exception))
        self.approve("W1", f"I approve writing/editing {SPEC} for F1 v1.0.0, including the finalization commit.")
        with self.assertRaises(SpecAlignError) as cm:
            finalize.apply_plan(self.p, self.plan_path)
        self.assertIn("INDEX.md", str(cm.exception))
        self.assertIn("Draft", (self.p / SPEC).read_text(encoding="utf-8"))          # nothing written

    def test_apply_writes_records_files_and_defers_tag_checks(self):
        self.approve("W1", f"I approve writing/editing {SPEC}, {INDEX} for F1 v1.0.0, including the finalization commit.")
        rep = finalize.apply_plan(self.p, self.plan_path)
        self.assertTrue(rep["ok"], rep.get("registry_blocking"))
        self.assertIn("| Status | Approved |", (self.p / SPEC).read_text(encoding="utf-8"))
        self.assertEqual({f["path"] for f in manifest.active(self.p)[1]["files"]}, {SPEC, INDEX})
        self.assertIn("tag_exists", rep["registry_tag_checks_pending"])

    def test_apply_is_idempotent(self):
        self.approve("C1", f"I approve the write of {SPEC}, {INDEX}, the tag {TAG} and the push to origin.")
        finalize.apply_plan(self.p, self.plan_path)
        snap = {r: (self.p / r).read_bytes() for r in (SPEC, INDEX)}
        rep = finalize.apply_plan(self.p, self.plan_path)
        self.assertEqual(rep["changed"], [])
        self.assertEqual({r: (self.p / r).read_bytes() for r in (SPEC, INDEX)}, snap)

    # ----------------------------------------------------------------------------- staged
    def test_staged_files_must_equal_the_plan(self):
        self.approve("W1", f"I approve writing {SPEC}, {INDEX} for F1.")
        finalize.apply_plan(self.p, self.plan_path)
        self.repo.git("add", SPEC)
        res = finalize.staged_check(self.p, self.plan_path)
        self.assertFalse(res["ok"])
        self.assertEqual(res["missing"], [INDEX])
        self.repo.git("add", INDEX)
        self.assertTrue(finalize.staged_check(self.p, self.plan_path)["ok"])
        self.repo.write("extra.txt", "x\n")
        self.repo.git("add", "extra.txt")
        self.assertEqual(finalize.staged_check(self.p, self.plan_path)["extra"], ["extra.txt"])

    # ----------------------------------------------------------------------------- tag / push
    def finalized_commit(self):
        self.approve("W1", f"I approve writing {SPEC}, {INDEX} for F1.")
        finalize.apply_plan(self.p, self.plan_path)
        self.repo.commit("finalize F1")
        self.repo.git("update-index", "--refresh")

    def test_tag_refuses_without_a_g1_naming_it(self):
        self.finalized_commit()
        with self.assertRaises(SpecAlignError) as cm:
            finalize.create_tags(self.p, self.plan_path)
        self.assertIn("G1/C1", str(cm.exception))
        self.assertEqual(self.repo.git("tag", "--list"), "")

    def test_tag_refuses_a_dirty_tree_and_a_wrong_spec_version(self):
        self.finalized_commit()
        self.approve("G1", f"I approve creating the tag(s) {TAG}.")
        (self.p / SPEC).write_text("changed\n", encoding="utf-8")
        with self.assertRaises(SpecAlignError):
            finalize.create_tags(self.p, self.plan_path)
        self.repo.git("checkout", "--", SPEC)
        self.plan["tags"] = ["spec/F1-demo-v2.0.0"]
        self.write_plan()
        self.approve("G1", "I approve creating the tag(s) spec/F1-demo-v2.0.0.")
        with self.assertRaises(SpecAlignError) as cm:
            finalize.create_tags(self.p, self.plan_path)
        self.assertIn("v1.0.0", str(cm.exception))

    def test_tag_created_once_and_recorded(self):
        self.finalized_commit()
        self.approve("G1", f"I approve creating the tag(s) {TAG}.")
        self.assertEqual(finalize.create_tags(self.p, self.plan_path), [TAG])
        self.assertEqual(self.repo.git("tag", "--list").strip(), TAG)
        self.assertEqual(manifest.active(self.p)[1]["tags"][0]["name"], TAG)
        with self.assertRaises(SpecAlignError):
            finalize.create_tags(self.p, self.plan_path)
        self.assertTrue(manifest.verify(self.p)["ok"])

    def test_push_needs_p1_naming_remote_and_tag(self):
        with self.assertRaises(SpecAlignError):
            finalize.push_command(self.p, self.plan_path, "origin")
        self.approve("P1", f"I approve pushing main and {TAG} to origin.")
        self.assertEqual(finalize.push_command(self.p, self.plan_path, "origin", "main"),
                         ["git", "push", "origin", "main", TAG])
        with self.assertRaises(SpecAlignError):
            finalize.push_command(self.p, self.plan_path, "upstream", "main")


if __name__ == "__main__":
    unittest.main()
