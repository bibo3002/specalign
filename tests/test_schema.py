import _path  # noqa: F401  (puts tools/ on sys.path)

import json
import unittest

from fixture import Repo, card
from specalign import schema
from specalign.common import SpecAlignError

ROWS = [
    {"kind": "column", "tbl": "things", "name": "id", "detail": "uuid not null default gen_random_uuid() "},
    {"kind": "column", "tbl": "things", "name": "title", "detail": "text   not null"},
    {"kind": "constraint", "tbl": "things", "name": "things_pkey", "detail": "PRIMARY KEY (id)"},
    {"kind": "index", "tbl": "things", "name": "uq_title", "detail": "CREATE UNIQUE INDEX uq_title ON things (lower(title))"},
]


class FingerprintTests(unittest.TestCase):
    def test_stable_under_order_and_whitespace(self):
        shuffled = [dict(r, detail=r["detail"].replace(" ", "  ")) for r in reversed(ROWS)]
        self.assertEqual(schema.fingerprint(ROWS), schema.fingerprint(shuffled))
        self.assertRegex(schema.fingerprint(ROWS), r"^sha256:[0-9a-f]{16}$")

    def test_any_change_alters_it(self):
        changed = [dict(r) for r in ROWS]
        changed[1]["detail"] = "text null"
        self.assertNotEqual(schema.fingerprint(ROWS), schema.fingerprint(changed))
        self.assertNotEqual(schema.fingerprint(ROWS), schema.fingerprint(ROWS[:-1]))

    def test_bad_input(self):
        with self.assertRaises(SpecAlignError):
            schema.canonical([{"kind": "column"}])
        with self.assertRaises(SpecAlignError):
            schema.canonical(ROWS + [ROWS[0]])

    def test_describe_lists_tables(self):
        self.assertIn("4 objects; tables: things", schema.describe(ROWS))

    def test_diff(self):
        new = [dict(r) for r in ROWS if r["name"] != "uq_title"] + [
            {"kind": "column", "tbl": "things", "name": "extra", "detail": "int null"}]
        new[1]["detail"] = "text null"
        d = schema.diff(ROWS, new)
        self.assertEqual(len(d["added"]), 1)
        self.assertEqual(len(d["removed"]), 1)
        self.assertEqual(len(d["changed"]), 1)
        self.assertIn("things.title", d["changed"][0])


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.cleanup)
        self.p = self.repo.path

    def spec(self, fingerprint_cell):
        text = card("F1", "T", "Approved", "1.0.0", "spec/F1-t-v1.0.0", "src/a.ts")
        text = text.replace("| Sources |", f"| Schema fingerprint | {fingerprint_cell} |\n| Sources |")
        self.repo.write("docs/specs/SPEC-F1-t.md", text)

    def test_unrecorded_match_and_mismatch(self):
        self.spec("n/a")
        self.assertEqual(schema.check(self.p, "docs/specs", "F1", ROWS)["status"], "unrecorded")
        self.spec(schema.fingerprint(ROWS) + " (4 objects)")
        self.assertEqual(schema.check(self.p, "docs/specs", "F1", ROWS)["status"], "match")
        changed = [dict(r) for r in ROWS]
        changed[1]["detail"] = "text null"
        res = schema.check(self.p, "docs/specs", "F1", changed)
        self.assertEqual((res["status"], res["changes"]), ("mismatch", None))

    def test_snapshot_gives_a_diff_on_mismatch(self):
        self.spec(schema.fingerprint(ROWS))
        path = schema.snapshot(self.p, "docs/specs", "F1", ROWS)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))[0]["tbl"], "things")
        changed = [dict(r) for r in ROWS]
        changed[1]["detail"] = "text null"
        res = schema.check(self.p, "docs/specs", "F1", changed)
        self.assertEqual(len(res["changes"]["changed"]), 1)

    def test_unknown_feature(self):
        with self.assertRaises(SpecAlignError):
            schema.check(self.p, "docs/specs", "F9", ROWS)


if __name__ == "__main__":
    unittest.main()
