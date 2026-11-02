import _path  # noqa: F401  (puts tools/ on sys.path)

import tempfile
import unittest
from pathlib import Path

from specalign import docedit
from specalign.common import SpecAlignError

SPEC = """# SPEC-F1 — Demo

## §0 Card

| Field | Value |
|---|---|
| Feature | F1 — Demo |
| Status | Draft |
| Version | v1.0.0 |

## §13C Evolution History

| Version | Date | Change type | Description |
|---|---|---|---|
| v1.0.0 | 2026-01-01 | Created | first |

## §13D Approval History

| Version | Gate | Approved by | Date | Evidence ref | Statement |
|---|---|---|---|---|---|

## §14 Self-Check

text
"""


class DoceditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "SPEC-F1-demo.md"

    def write(self, text, eol="\n", bom=False):
        data = text.replace("\n", eol).encode("utf-8")
        self.path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)

    def edit(self, fn):
        doc = docedit.Doc(self.path)
        result = fn(doc)
        saved = doc.save()
        return result, saved

    def test_append_row_to_a_named_block_and_keep_the_other_tables(self):
        self.write(SPEC)
        res, saved = self.edit(lambda d: d.append_row(["v1.1.0", "2026-02-01", "Modified", "second"], "13C"))
        self.assertEqual((res, saved), ("added", True))
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("| v1.1.0 | 2026-02-01 | Modified | second |", text)
        self.assertLess(text.index("v1.0.0 | 2026-01-01"), text.index("v1.1.0 | 2026-02-01"))
        self.assertLess(text.index("v1.1.0 | 2026-02-01"), text.index("§13D"))

    def test_append_row_is_idempotent(self):
        self.write(SPEC)
        self.edit(lambda d: d.append_row(["v1.1.0", "2026-02-01", "Modified", "second"], "13C"))
        before = self.path.read_bytes()
        res, saved = self.edit(lambda d: d.append_row(["v1.1.0", "2026-02-01", "Modified", "second"], "13C"))
        self.assertEqual((res, saved), ("unchanged", False))
        self.assertEqual(self.path.read_bytes(), before)

    def test_append_row_into_an_empty_table_and_pads_short_rows(self):
        self.write(SPEC)
        self.edit(lambda d: d.append_row(["v1.0.0", "G1", "me"], "13D"))
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("| v1.0.0 | G1 | me |  |  |  |", text)

    def test_key_replaces_a_row_with_the_same_key(self):
        self.write(SPEC)
        res, _ = self.edit(lambda d: d.append_row(["v1.0.0", "2026-01-01", "Created", "rewritten"], "13C", key="Version"))
        self.assertEqual(res, "updated")
        text = self.path.read_text(encoding="utf-8")
        self.assertEqual(text.count("| v1.0.0 | 2026"), 1)
        self.assertIn("rewritten", text)
        self.assertNotIn("| first |", text)

    def test_too_many_cells_is_an_error(self):
        self.write(SPEC)
        with self.assertRaises(SpecAlignError):
            self.edit(lambda d: d.append_row(["1", "2", "3", "4", "5"], "13C"))

    def test_patch_row_and_set_card(self):
        self.write(SPEC)
        res, _ = self.edit(lambda d: d.patch_row("Version", "v1.0.0", {"Description": "reworded"}, "13C"))
        self.assertEqual(res, "updated")
        res, _ = self.edit(lambda d: d.set_card("Status", "Approved"))
        self.assertEqual(res, "updated")
        res, saved = self.edit(lambda d: d.set_card("Status", "Approved"))
        self.assertEqual((res, saved), ("unchanged", False))
        res, _ = self.edit(lambda d: d.set_card("Tag", "spec/F1-demo-v1.0.0"))
        self.assertEqual(res, "added")
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("| Status | Approved |", text)
        self.assertIn("| Tag | spec/F1-demo-v1.0.0 |", text)
        self.assertIn("reworded", text)

    def test_patch_row_requires_exactly_one_match(self):
        self.write(SPEC)
        with self.assertRaises(SpecAlignError):
            self.edit(lambda d: d.patch_row("Version", "v9.9.9", {"Description": "x"}, "13C"))
        self.edit(lambda d: d.append_row(["v1.0.0", "2026-03-01", "Fixed", "dup"], "13C"))
        with self.assertRaises(SpecAlignError):
            self.edit(lambda d: d.patch_row("Version", "v1.0.0", {"Description": "x"}, "13C"))

    def test_missing_block_and_column_are_errors(self):
        self.write(SPEC)
        with self.assertRaises(SpecAlignError):
            self.edit(lambda d: d.append_row(["x"], "99"))
        with self.assertRaises(SpecAlignError):
            self.edit(lambda d: d.patch_row("Nope", "x", {"Description": "y"}, "13C"))

    def test_crlf_bom_and_arabic_survive_a_round_trip(self):
        self.write(SPEC.replace("first", "الأول «حفظ»"), eol="\r\n", bom=True)
        self.edit(lambda d: d.append_row(["v1.1.0", "2026-02-01", "Modified", "الثاني | مع شريط"], "13C"))
        raw = self.path.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        body = raw[3:].decode("utf-8")
        self.assertEqual(body.count("\r\n"), body.count("\n"))     # no bare LF introduced
        self.assertIn("الأول «حفظ»", body)
        self.assertIn("الثاني \\| مع شريط", body)

    def test_pipe_in_a_cell_is_escaped_and_not_split(self):
        self.write(SPEC)
        self.edit(lambda d: d.append_row(["v1.1.0", "2026-02-01", "Modified", "a | b"], "13C"))
        doc = docedit.Doc(self.path)
        t = doc.pick_table("13C")
        self.assertEqual(doc.cells_at(t.rows[-1])[3], "a | b")

    def test_no_trailing_newline_is_preserved(self):
        self.write(SPEC.rstrip("\n"))
        self.edit(lambda d: d.set_card("Status", "Approved"))
        self.assertFalse(self.path.read_bytes().endswith(b"\n"))

    def test_replace_block_body(self):
        self.write(SPEC)
        res, _ = self.edit(lambda d: d.replace_block("14", ["new text", "", "**Overall: PASS**"]))
        self.assertEqual(res, "updated")
        self.assertTrue(self.path.read_text(encoding="utf-8").rstrip().endswith("**Overall: PASS**"))
        res, saved = self.edit(lambda d: d.replace_block("14", ["new text", "", "**Overall: PASS**"]))
        self.assertEqual((res, saved), ("unchanged", False))

    def test_dry_run_diff_does_not_write(self):
        self.write(SPEC)
        before = self.path.read_bytes()
        doc = docedit.Doc(self.path)
        doc.set_card("Status", "Approved")
        self.assertIn("+| Status | Approved |", doc.diff())
        self.assertEqual(self.path.read_bytes(), before)

    def test_table_inside_code_fence_is_ignored(self):
        self.write(SPEC.replace("text\n", "```\n| Version | X |\n|---|---|\n| a | b |\n```\n"))
        doc = docedit.Doc(self.path)
        self.assertEqual(len(doc.tables("14")), 0)

    def test_aligned_tables_stay_aligned(self):
        text = ("| ID  | Title      | Status   |\n|-----|------------|----------|\n"
                "| F1  | First      | Draft    |\n| F2  | Second     | Approved |\n")
        self.path.write_bytes(text.encode("utf-8"))
        self.edit(lambda d: d.patch_row("ID", "F1", {"Status": "Approved"}))
        self.edit(lambda d: d.append_row(["F3", "Third", "Draft"]))
        lines = self.path.read_text(encoding="utf-8").split("\n")
        self.assertEqual(lines[2], "| F1  | First      | Approved |")
        self.assertEqual(lines[4], "| F3  | Third      | Draft    |")
        self.assertEqual(len({len(l) for l in lines[:5]}), 1)       # every row has the same width

    def test_insert_missing_block_after_another_is_idempotent_and_never_touches_an_existing_one(self):
        legacy = SPEC.replace("## §13D Approval History\n\n| Version | Gate | Approved by | Date | Evidence ref | Statement |\n|---|---|---|---|---|---|\n\n", "")
        self.write(legacy)
        body = ["| Version | Gate | Approved by | Date | Evidence ref | Statement |", "|---|---|---|---|---|---|",
                "| v1.0.0 | G1 | me | 2026-01-01 | §13B D-1 | «yes» |"]
        res, saved = self.edit(lambda d: d.insert_block("13D", "Approval History", body, after="13C"))
        self.assertEqual((res, saved), ("added", True))
        text = self.path.read_text(encoding="utf-8")
        self.assertLess(text.index("## §13C"), text.index("## §13D"))
        self.assertLess(text.index("## §13D"), text.index("## §14"))
        self.assertIn("\n\n## §13D Approval History\n\n| Version", text)
        self.assertIn("«yes» |\n\n## §14", text)                       # one blank line before the next heading
        res, saved = self.edit(lambda d: d.insert_block("13D", "Approval History", ["other"], after="13C"))
        self.assertEqual((res, saved), ("unchanged", False))            # an existing block is left alone
        self.assertEqual(len(docedit.Doc(self.path).tables("13D")[0].rows), 1)

    def test_registry_style_table_without_blocks(self):
        self.path.write_bytes("| ID | Status |\n|---|---|\n| F1 | Draft |\n".encode("utf-8"))
        res, _ = self.edit(lambda d: d.patch_row("ID", "F1", {"Status": "Approved"}))
        self.assertEqual(res, "updated")
        self.assertIn("| F1 | Approved |", self.path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
