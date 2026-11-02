import _path  # noqa: F401  (puts tools/ on sys.path)

import unittest

from fixture import Repo
from specalign import manifest, preflight

BINDING = """# Project binding

PROJECT_MAP: AGENTS.md
SPEC_DIR: docs/specs
REGISTRY: docs/specs/INDEX.md
DB_TOOL: postgres MCP
UI_TOOL: none
TAG_PREFIX: spec/
TEST_DATA_PREFIX: __TEST_
BASELINE_DATE: 2026-01-01

TEST_ACCOUNTS:
  - lawyer: a@example.invalid

CONVENTIONS:
  English prose, Arabic strings verbatim.

PROJECT_PITFALLS:
  - none known
"""


def codes(rep, severity=None):
    return [(f["code"], f["severity"]) for f in rep["findings"] if severity in (None, f["severity"])]


class PreflightTests(unittest.TestCase):
    def make(self, binding=BINDING):
        repo = Repo(binding=binding)
        self.addCleanup(repo.cleanup)
        repo.write_index_row("F1", "demo", "Draft", "1.0.0", "—")
        repo.commit("index")
        return repo

    def test_complete_binding_passes_with_only_recommendation_warnings(self):
        repo = self.make()
        rep = preflight.run_preflight(repo.path)
        self.assertTrue(rep["ok"], rep["findings"])
        self.assertEqual({c for c, s in codes(rep, "warn")}, {"BINDING_INCOMPLETE"})

    def test_missing_binding_and_missing_index(self):
        repo = Repo()
        self.addCleanup(repo.cleanup)
        (repo.path / "docs" / "specs" / "INDEX.md").unlink()
        rep = preflight.run_preflight(repo.path)
        self.assertFalse(rep["ok"])
        self.assertIn(("BINDING_MISSING", "error"), codes(rep))
        self.assertIn(("INDEX_MISSING", "error"), codes(rep))

    def test_empty_and_placeholder_values_are_incomplete(self):
        text = BINDING.replace("DB_TOOL: postgres MCP", "DB_TOOL: <postgres MCP | none>") \
                      .replace("BASELINE_DATE: 2026-01-01", "BASELINE_DATE:") \
                      .replace("  English prose, Arabic strings verbatim.\n", "")
        rep = preflight.run_preflight(self.make(text).path)
        msgs = " ".join(f["message"] for f in rep["findings"] if f["severity"] == "error")
        self.assertIn("DB_TOOL", msgs)
        self.assertIn("BASELINE_DATE", msgs)
        self.assertIn("CONVENTIONS", msgs)

    def test_dirty_tracked_file_blocks_but_untracked_is_only_noted(self):
        repo = self.make()
        repo.write("docs/specs/NEW.md", "x\n")
        rep = preflight.run_preflight(repo.path)
        self.assertTrue(rep["ok"])
        self.assertIn(("UNTRACKED_NOTED", "info"), codes(rep))
        repo.write("docs/specs/INDEX.md", (repo.path / "docs/specs/INDEX.md").read_text(encoding="utf-8") + "\n")
        rep = preflight.run_preflight(repo.path)
        self.assertFalse(rep["ok"])
        self.assertIn(("DIRTY_TRACKED_FILES", "error"), codes(rep))

    def test_extra_path_scope(self):
        repo = self.make()
        repo.write("src/a.ts", "a\n")
        repo.commit("a")
        repo.write("src/a.ts", "b\n")
        self.assertTrue(preflight.run_preflight(repo.path)["ok"])
        self.assertFalse(preflight.run_preflight(repo.path, paths=["src"])["ok"])

    def test_tag_namespace_warnings(self):
        repo = self.make()
        repo.tag("F1-demo-v1.0.0")                 # outside the prefix
        repo.tag("spec/random-notes")              # under the prefix, wrong shape
        rep = preflight.run_preflight(repo.path)
        self.assertEqual(len([c for c in codes(rep, "warn") if c[0] == "TAG_NAMESPACE"]), 2)

    def test_mixed_line_endings_warn_and_bad_utf8_errors(self):
        repo = self.make()
        (repo.path / "docs/specs/SPEC-F1-demo.md").write_bytes(b"a\r\nb\nc\n")
        (repo.path / "docs/specs/SPEC-F2-bad.md").write_bytes(b"\xff\xfe broken\n")
        rep = preflight.run_preflight(repo.path)
        self.assertIn(("ENCODING", "warn"), codes(rep))
        self.assertIn(("ENCODING", "error"), codes(rep))

    def test_active_run_is_reported(self):
        repo = self.make()
        manifest.init(repo.path, "docs/specs", "F1", "sync", date="2026-01-02")
        rep = preflight.run_preflight(repo.path)
        self.assertTrue(any(c == "RUN_ACTIVE" for c, _ in codes(rep)))

    def test_binding_block_parsing(self):
        entries = preflight.binding_entries(BINDING)
        self.assertEqual(entries["SPEC_DIR"][0], "docs/specs")
        self.assertIn("lawyer", entries["TEST_ACCOUNTS"][1])


if __name__ == "__main__":
    unittest.main()
