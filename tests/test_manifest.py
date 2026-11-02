import _path  # noqa: F401  (puts tools/ on sys.path)

import json
import unittest

from fixture import Repo
from specalign import manifest
from specalign.common import SpecAlignError

STMT_T1 = "I classify this run as Core per the agent's recommendation; discussion, citation discipline and final approval remain mandatory."


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.cleanup)
        self.p = self.repo.path
        self.rel = manifest.init(self.p, "docs/specs", "F1", "sync", "Core", "remediating", "1.0.0", "2026-01-02")

    def data(self):
        return manifest.active(self.p)[1]

    def test_init_creates_record_and_state_pointer(self):
        self.assertEqual(self.rel, "docs/specs/runs/2026-01-02-F1-sync.json")
        state = json.loads((self.p / ".specalign" / "run-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["run"], self.rel)
        self.assertEqual(self.data()["stage"], 0)

    def test_init_refuses_to_overwrite_and_validates_input(self):
        with self.assertRaises(SpecAlignError):
            manifest.init(self.p, "docs/specs", "F1", "sync", "Core", date="2026-01-02")
        with self.assertRaises(SpecAlignError):
            manifest.init(self.p, "docs/specs", "one", "sync")
        with self.assertRaises(SpecAlignError):
            manifest.init(self.p, "docs/specs", "F2", "weird")

    def test_stage_needs_the_tier_approval_and_runs_in_order(self):
        manifest.set_stage(self.p, 1)
        with self.assertRaises(SpecAlignError) as cm:
            manifest.set_stage(self.p, 2)
        self.assertIn("T1", str(cm.exception))
        manifest.approve(self.p, "T1", STMT_T1, "Core, 1.0.0, tag as proposed")
        self.assertEqual(manifest.set_stage(self.p, 2)["stage"], 2)
        with self.assertRaises(SpecAlignError):
            manifest.set_stage(self.p, 7)                    # jump

    def test_remediating_run_needs_r1_before_the_remediation_stage(self):
        manifest.set_stage(self.p, 1)
        manifest.approve(self.p, "T1", STMT_T1, "yes")
        for n in (2, 3, 4):
            manifest.set_stage(self.p, n)
        with self.assertRaises(SpecAlignError) as cm:
            manifest.set_stage(self.p, 5)
        self.assertIn("R1", str(cm.exception))
        manifest.approve(self.p, "R1", "I authorize a remediating run for F1: dispositions as in the table above, "
                         "changes limited to a.ts.", "fix all")
        self.assertEqual(manifest.set_stage(self.p, 5)["stage"], 5)

    def test_documentation_only_run_skips_r1(self):
        rel = manifest.init(self.p, "docs/specs", "F2", "genesis", "Standard", "documentation-only", date="2026-01-03")
        manifest.set_stage(self.p, 1, rel)
        manifest.approve(self.p, "T1", STMT_T1, "ok", rel)
        for n in (2, 3, 4, 5, 6):
            manifest.set_stage(self.p, n, rel)

    def test_force_records_an_override(self):
        manifest.set_stage(self.p, 1)
        manifest.set_stage(self.p, 2, force="user said skip the tier gate")
        d = self.data()
        self.assertEqual(d["overrides"][0]["reason"], "user said skip the tier gate")
        res = manifest.verify(self.p)
        self.assertFalse(res["ok"])                          # still missing T1 at stage 2
        self.assertTrue(any("override" in n or "missing gates" in n for n in res["notes"]))

    def test_approval_rejects_placeholders_empty_reply_and_unknown_gate(self):
        with self.assertRaises(SpecAlignError):
            manifest.approve(self.p, "T1", "I classify this run as <Micro|Standard|Core>", "yes")
        with self.assertRaises(SpecAlignError):
            manifest.approve(self.p, "T1", STMT_T1, "  ")
        with self.assertRaises(SpecAlignError):
            manifest.approve(self.p, "Z9", STMT_T1, "yes")

    def test_reply_is_stored_verbatim_with_arabic(self):
        reply = "قبول التوصيات، approve the write, tags and push"
        rec = manifest.approve(self.p, "C1", "I approve the write, the tags spec/F1-a-v1.0.0 and the push as listed.", reply)
        self.assertEqual(self.data()["approvals"][-1]["reply"], reply)
        self.assertRegex(rec["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_dispositions_are_validated_and_replaced(self):
        manifest.add(self.p, "disposition", {"id": "DF-1", "disposition": "Fix", "files": ["a.ts"]})
        manifest.add(self.p, "disposition", {"id": "DF-1", "disposition": "Accept"})
        self.assertEqual(self.data()["dispositions"], [{"id": "DF-1", "disposition": "Accept"}])
        with self.assertRaises(SpecAlignError):
            manifest.add(self.p, "disposition", {"id": "DF-1", "disposition": "fix-all"})
        with self.assertRaises(SpecAlignError):
            manifest.add(self.p, "disposition", {"id": "1", "disposition": "Fix"})

    def test_file_hash_detects_later_change(self):
        (self.p / "docs" / "specs" / "SPEC-F1-x.md").write_text("one\n", encoding="utf-8")
        manifest.add(self.p, "file", {"path": "docs/specs/SPEC-F1-x.md"})
        self.assertTrue(manifest.verify(self.p)["ok"])
        (self.p / "docs" / "specs" / "SPEC-F1-x.md").write_text("two\n", encoding="utf-8")
        res = manifest.verify(self.p)
        self.assertTrue(res["ok"])                            # changed ≠ broken, but it is noted
        self.assertTrue(any("changed after it was recorded" in n for n in res["notes"]))
        with self.assertRaises(SpecAlignError):
            manifest.add(self.p, "file", {"path": "nope.md"})

    def test_hash_ignores_crlf(self):
        f = self.p / "a.txt"
        f.write_bytes(b"x\r\ny\r\n")
        h1 = manifest.sha256_of(f)
        f.write_bytes(b"x\ny\n")
        self.assertEqual(h1, manifest.sha256_of(f))

    def test_applied_migration_needs_a_named_d1(self):
        mig = {"file": "server/migrations/012_x.sql", "pre_check": "select 1 → 0", "rollback": "drop ...",
               "verification": "select ...", "applied_at": "2026-01-02T10:00:00Z"}
        with self.assertRaises(SpecAlignError):
            manifest.add(self.p, "migration", mig)
        manifest.approve(self.p, "D1", "I approve applying server/migrations/012_x.sql to the dev database: "
                         "pre-check select 1 → 0, rollback drop, verification select.", "yes")
        manifest.add(self.p, "migration", mig)
        self.assertTrue(manifest.verify(self.p)["ok"])
        bad = dict(mig, file="server/migrations/013_y.sql", rollback="")
        # a migration that is recorded but not yet applied is allowed; once applied it needs everything
        manifest.add(self.p, "migration", dict(bad, applied_at=""))

    def test_tags_need_approval_naming_them(self):
        manifest.add(self.p, "tag", {"name": "spec/F1-a-v1.0.0"})
        self.assertFalse(manifest.verify(self.p)["ok"])
        manifest.approve(self.p, "G1", "I approve creating the tag(s) spec/F1-a-v1.0.0.", "yes")
        self.assertTrue(manifest.verify(self.p)["ok"])

    def test_show_reports_what_blocks_the_next_stage(self):
        info = manifest.show(self.p)
        self.assertEqual((info["stage"], info["next_stage"]), (0, 1))
        manifest.set_stage(self.p, 1)
        self.assertIn("T1 (tier decision)", manifest.show(self.p)["blocked_by"])

    def test_no_active_run_is_an_error(self):
        other = Repo()
        self.addCleanup(other.cleanup)
        with self.assertRaises(SpecAlignError):
            manifest.show(other.path)


if __name__ == "__main__":
    unittest.main()
