import _path  # noqa: F401  (puts tools/ on sys.path)

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fixture import Repo, card
from specalign import registry
from specalign.common import SpecAlignError, norm_tag, norm_version, parse_card, parse_index, status_word

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def failed(report):
    return {c["check"]: c["errors"] for c in report["checks"] if not c["passed"]}


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.cleanup)

    def run_checks(self, **kw):
        return registry.run_checks(self.repo.path, **kw)

    # ---------------------------------------------------------------- happy path
    def test_consistent_registry_passes_every_check(self):
        self.repo.add_feature("F1", "auth")
        self.repo.add_feature("F2", "parties", version="1.3.0")
        rep = self.run_checks()
        self.assertEqual(failed(rep), {})
        self.assertEqual(rep["summary"]["checks"], 9)
        self.assertEqual(rep["summary"]["rows"], 2)

    def test_arabic_and_crlf_specs_do_not_crash(self):
        self.repo.add_feature("F1", "auth", newline="\r\n")
        self.assertEqual(failed(self.run_checks()), {})

    # ---------------------------------------------------------------- the bug this tool exists to catch
    def test_another_version_tag_does_not_satisfy_an_approved_row(self):
        """The old script accepted ANY tag with the F-prefix; the INDEX version needs its own tag."""
        self.repo.add_feature("F6", "basic", version="1.0.1")
        self.repo.write_index_row("F6", "basic", "Approved", "1.1.0", "spec/F6-basic-v1.1.0")
        self.repo.commit("index bump without tag")
        errs = failed(self.run_checks())
        self.assertIn("tag_exists", errs)
        self.assertIn("spec/F6-basic-v1.1.0", errs["tag_exists"][0])

    def test_tag_must_match_the_index_version(self):
        self.repo.add_feature("F6", "basic", version="1.0.0")
        self.repo.write_index_row("F6", "basic", "Approved", "1.1.0", "spec/F6-basic-v1.0.0")
        self.repo.commit("index says 1.1.0 but keeps the old tag")
        self.assertIn("approved_tag_matches_version", failed(self.run_checks()))

    def test_tag_must_contain_the_spec_version(self):
        """Tag created on a commit whose spec is still the previous version."""
        self.repo.add_feature("F6", "basic", version="1.0.0")
        self.repo.write("docs/specs/SPEC-F6-basic.md",
                        card("F6", "basic", "Approved", "1.1.0", "spec/F6-basic-v1.1.0", "src/a.ts"))
        self.repo.write_index_row("F6", "basic", "Approved", "1.1.0", "spec/F6-basic-v1.1.0")
        self.repo.git("tag", "spec/F6-basic-v1.1.0")        # tag the OLD commit
        self.repo.commit("version bump lands after the tag")
        errs = failed(self.run_checks())
        self.assertIn("tag_contains_spec_version", errs)
        self.assertIn("says version 1.0.0", errs["tag_contains_spec_version"][0])

    def test_tagged_commit_without_the_spec_file_fails(self):
        self.repo.git("tag", "spec/F3-s-v1.0.0")             # tag on a commit that has no spec yet
        self.repo.add_feature("F3", "s", make_tag=False)
        self.assertIn("tag_contains_spec_version", failed(self.run_checks()))

    # ---------------------------------------------------------------- INDEX ↔ spec card
    def test_index_version_must_equal_the_card_version(self):
        self.repo.add_feature("F2", "p", version="1.3.0", card_version="1.2.0")
        self.assertIn("index_matches_spec_card", failed(self.run_checks()))

    def test_index_status_must_equal_the_card_status(self):
        self.repo.add_feature("F2", "p", card_status="Verifying")
        self.assertIn("index_matches_spec_card", failed(self.run_checks()))

    def test_index_tag_must_equal_the_card_tag(self):
        self.repo.add_feature("F2", "p")
        self.repo.write_index_row("F2", "p", "Approved", "1.0.0", "spec/F2-other-v1.0.0")
        self.repo.commit("index tag differs")
        self.assertIn("index_matches_spec_card", failed(self.run_checks()))

    def test_legacy_spec_without_card_is_only_a_warning(self):
        self.repo.add_feature("F4", "legacy")
        self.repo.write("docs/specs/SPEC-F4-legacy.md", "# Legacy spec without a card\n")
        self.repo.commit("legacy")
        self.repo.git("tag", "-f", "spec/F4-legacy-v1.0.0")
        rep = self.run_checks()
        chk = next(c for c in rep["checks"] if c["check"] == "index_matches_spec_card")
        self.assertTrue(chk["warnings"])
        self.assertFalse(chk["errors"])

    def test_strict_mode_turns_warnings_into_failure(self):
        self.repo.add_feature("F4", "legacy")
        self.repo.write("docs/specs/SPEC-F4-legacy.md", "# no card\n")
        self.repo.commit("legacy")
        self.repo.git("tag", "-f", "spec/F4-legacy-v1.0.0")
        self.assertEqual(self._cli("--strict").returncode, 1)
        self.assertEqual(self._cli().returncode, 0)

    # ---------------------------------------------------------------- file / row relationships
    def test_approved_row_without_a_spec_file(self):
        self.repo.write_index_row("F9", "x", "Approved", "1.0.0", "spec/F9-x-v1.0.0")
        self.repo.commit("row only")
        self.assertIn("approved_has_spec_file", failed(self.run_checks()))

    def test_spec_file_without_an_index_row(self):
        self.repo.write("docs/specs/SPEC-F5-orphan.md", card("F5", "o", "Draft", "0.1.0", "—", "src/o.ts"))
        self.repo.commit("orphan")
        self.assertIn("spec_file_has_index_row", failed(self.run_checks()))

    def test_undocumented_row_with_a_spec_file(self):
        self.repo.add_feature("F7", "u", status="Undocumented", tag=None, version="—")
        self.assertIn("undocumented_no_spec_file", failed(self.run_checks()))

    def test_duplicate_ids(self):
        self.repo.add_feature("F1", "a")
        self.repo.index_rows.append(self.repo.index_rows[0])
        self.repo.write_index()
        self.repo.commit("dup row")
        self.assertIn("no_duplicate_ids", failed(self.run_checks()))

    def test_card_feature_must_match_the_file_name(self):
        self.repo.add_feature("F1", "a")
        text = (self.repo.path / "docs/specs/SPEC-F1-a.md").read_text(encoding="utf-8").replace("| Feature | F1", "| Feature | F2")
        self.repo.write("docs/specs/SPEC-F1-a.md", text)
        self.repo.commit("wrong card id")
        self.assertIn("spec_section0_fid_matches", failed(self.run_checks()))

    def test_merged_and_draft_rows_need_nothing(self):
        self.repo.write_index_row("F14", "merged", "Merged → F6", "—", "—")
        self.repo.write_index_row("F19", "draft", "Draft", "—", "—")
        self.repo.commit("rows")
        self.assertEqual(failed(self.run_checks()), {})

    # ---------------------------------------------------------------- binding / errors
    def test_tag_prefix_comes_from_the_binding(self):
        repo = Repo(binding="# Binding\nTAG_PREFIX: specs/\n")
        self.addCleanup(repo.cleanup)
        repo.add_feature("F1", "a", tag="specs/F1-a-v1.0.0")
        rep = registry.run_checks(repo.path)
        self.assertEqual(rep["tag_prefix"], "specs/")
        self.assertEqual(failed(rep), {})

    def test_default_prefix_rejects_foreign_prefix_tag(self):
        self.repo.add_feature("F1", "a", tag="docs/F1-a-v1.0.0")
        self.assertIn("approved_tag_matches_version", failed(self.run_checks()))

    def test_missing_index_is_a_hard_error(self):
        (self.repo.path / "docs/specs/INDEX.md").unlink()
        with self.assertRaises(SpecAlignError):
            self.run_checks()

    def test_not_a_git_repo_is_a_hard_error(self):
        with tempfile.TemporaryDirectory() as plain, self.assertRaises(SpecAlignError):
            registry.run_checks(Path(plain))

    # ---------------------------------------------------------------- CLI contract
    def _cli(self, *extra):
        return subprocess.run([sys.executable, "-m", "specalign", "registry", "check", str(self.repo.path), *extra],
                              cwd=TOOLS, capture_output=True, text=True, encoding="utf-8")

    def test_cli_exit_codes_and_json(self):
        self.repo.add_feature("F1", "a")
        ok = self._cli("--json")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["schema"], "specalign.registry/1")
        self.repo.write_index_row("F1", "a", "Approved", "9.9.9", "spec/F1-a-v9.9.9")
        self.repo.commit("bad")
        self.assertEqual(self._cli().returncode, 1)
        (self.repo.path / "docs/specs/INDEX.md").unlink()
        self.assertEqual(self._cli().returncode, 2)


class ParserTests(unittest.TestCase):
    def test_normalisers(self):
        self.assertEqual(norm_version("v1.2.3"), "1.2.3")
        self.assertEqual(norm_version("1.0.0 (draft)"), "1.0.0")
        self.assertEqual(norm_version("—"), "")
        self.assertEqual(norm_tag("`spec/F6-x-v1.1.0` (earlier: spec/F6-x-v1.0.1)"), "spec/F6-x-v1.1.0")
        self.assertEqual(norm_tag("—"), "")
        self.assertEqual(status_word("Merged → F6"), "Merged")

    def test_index_columns_are_read_by_header_name(self):
        text = "| Status | ID | Title | Version | Tag |\n|---|---|---|---|---|\n| Approved | F3 | x | 1.0.0 | spec/F3-x-v1.0.0 |\n"
        rows = parse_index(text)
        self.assertEqual((rows[0].fid, rows[0].status, rows[0].version), ("F3", "Approved", "1.0.0"))

    def test_card_is_read_only_inside_section_zero(self):
        text = "## §0 Card\n\n| Field | Value |\n|---|---|\n| Status | Approved |\n\n## §1\n\n| Status | Draft |\n"
        self.assertEqual(parse_card(text)["status"], "Approved")


if __name__ == "__main__":
    unittest.main(verbosity=2)
