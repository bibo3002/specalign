import _path  # noqa: F401

import json
import subprocess
import sys
import unittest
from pathlib import Path

from fixture import Repo
from specalign import drift
from specalign.drift import brace_expand, parse_sources, source_matches

TOOLS = Path(__file__).resolve().parents[1] / "tools"


class SourcesGrammarTests(unittest.TestCase):
    """Token shapes taken from the real Sanad corpus (docs/specs/SPEC-F*.md §0 Sources)."""

    def test_brace_groups(self):
        self.assertEqual(sorted(brace_expand("a/{b,c}.vue")), ["a/b.vue", "a/c.vue"])
        self.assertEqual(sorted(brace_expand("x/{a,b/{c,d}}.ts")), ["x/a.ts", "x/b/c.ts", "x/b/d.ts"])
        self.assertEqual(brace_expand("a/{b,c"), ["a/{b,c"])   # unbalanced stays literal

    def test_f2_style_line_is_fully_parsed(self):
        raw = ("`src/pages/tabs/TabParties.vue`, `src/components/parties/{PartiesTable,PartyFormModal}.vue`, "
               "`src/composables/{usePartyMutations,useLawyerTags}.ts`, `src/utils/date-utils.ts` (date converters), "
               "tests `tests/api/parties.contract.test.ts`, `tests/unit/{party-form,parties-schemas}.test.ts`")
        s = parse_sources(raw)
        self.assertIn("src/components/parties/PartyFormModal.vue", s.patterns)
        self.assertIn("src/composables/useLawyerTags.ts", s.patterns)
        self.assertIn("tests/api/parties.contract.test.ts", s.patterns)
        self.assertIn("tests/unit/parties-schemas.test.ts", s.patterns)
        self.assertEqual(len(s.patterns), 9)
        self.assertEqual(s.notes, [])

    def test_parenthetical_annotations_with_commas_are_dropped(self):
        s = parse_sources("`server/index.ts` (:709,:861,:1245), `src/api/auth.ts` (`login`, `logout`)")
        self.assertEqual(s.patterns, ["server/index.ts", "src/api/auth.ts"])

    def test_line_references_are_stripped(self):
        self.assertEqual(parse_sources("server/app.ts:709,src/b.ts:10-20").patterns, ["server/app.ts", "src/b.ts"])

    def test_globs_and_directories(self):
        s = parse_sources("`src/components/files-list/*`, `src/components/sessions-dashboard/*.vue` (11), docs/")
        self.assertEqual(s.patterns, ["src/components/files-list/*", "src/components/sessions-dashboard/*.vue", "docs/"])

    def test_table_names_are_collected_not_failed(self):
        s = parse_sources("`src/a.ts`, tables `office_settings`, `app_settings`, `lawyers`")
        self.assertEqual(s.patterns, ["src/a.ts"])
        self.assertEqual(s.db_objects, ["office_settings", "app_settings", "lawyers"])
        self.assertEqual(s.notes, [])

    def test_prefix_label_and_semicolon(self):
        s = parse_sources("`src/a.ts`; host (contract only): `src/b.ts`, `src/c/{d,e}.vue`")
        self.assertEqual(s.patterns, ["src/a.ts", "src/b.ts", "src/c/d.vue", "src/c/e.vue"])

    def test_one_bad_token_does_not_void_the_rest(self):
        s = parse_sources("src/a.ts, stuff, src/b.ts")
        self.assertEqual(s.patterns, ["src/a.ts", "src/b.ts"])
        self.assertTrue(any("stuff" in n for n in s.notes))

    def test_matching_rules(self):
        self.assertTrue(source_matches("src/a.ts", "src/a.ts"))
        self.assertFalse(source_matches("src/a.ts", "src/a.tsx"))
        self.assertTrue(source_matches("src/dir/*", "src/dir/sub/x.vue"))
        self.assertTrue(source_matches("src/dir/", "src/dir/x.vue"))
        self.assertTrue(source_matches("src/dir", "src/dir/x.vue"))
        self.assertFalse(source_matches("src/dir", "src/directory/x.vue"))
        self.assertTrue(source_matches("src/*.vue", "src/A.vue"))


class DriftTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.cleanup)

    def report(self, *only):
        return {f["id"]: f for f in drift.run_drift(self.repo.path, only=list(only) or None)["features"]}

    def touch(self, rel, msg="change", same_second=False):
        self.repo.write(rel, f"// {msg}\n")
        return self.repo.commit(msg, same_second=same_second)

    def test_clean_when_nothing_changed_after_the_tag(self):
        self.repo.add_feature("F1", sources="src/a.ts")
        f = self.report()["F1"]
        self.assertEqual((f["status"], f["base_kind"]), ("clean", "index-tag"))

    def test_drift_in_a_brace_expanded_source(self):
        self.repo.write("src/x/A.vue", "a")
        self.repo.write("src/x/B.vue", "b")
        self.repo.add_feature("F2", sources="`src/x/{A,B}.vue`")
        self.touch("src/x/B.vue", "edit B")
        f = self.report()["F2"]
        self.assertEqual(f["status"], "drifted")
        self.assertEqual(f["offending_commits"][0]["files"], ["src/x/B.vue"])

    def test_unrelated_commit_is_not_drift(self):
        self.repo.add_feature("F1", sources="src/a.ts")
        self.touch("src/other.ts")
        self.assertEqual(self.report()["F1"]["status"], "clean")

    def test_commit_in_the_same_second_as_the_tag_is_still_drift(self):
        """The old +1 s watermark hid commits made in the same second as the tag commit."""
        self.repo.add_feature("F1", sources="src/a.ts")
        self.touch("src/a.ts", "immediately after", same_second=True)
        self.assertEqual(self.report()["F1"]["status"], "drifted")

    def test_the_tagged_commit_itself_is_not_drift(self):
        self.repo.write("src/a.ts", "x")
        self.repo.add_feature("F1", sources="src/a.ts")
        self.assertEqual(self.report()["F1"]["status"], "clean")

    def test_renamed_source_counts_as_a_change(self):
        self.repo.add_feature("F1", sources="src/old.ts")
        self.repo.git("mv", "src/old.ts", "src/new.ts")
        self.repo.commit("rename")
        f = self.report()["F1"]
        self.assertEqual(f["status"], "drifted")
        self.assertIn("src/old.ts", f["offending_commits"][0]["files"])

    def test_index_tag_beats_a_newer_tag_on_another_version(self):
        self.repo.add_feature("F4", slug="e", version="1.0.0", sources="src/d.ts")
        self.touch("src/d.ts", "between")
        self.repo.tag("spec/F4-e-v1.1.0")
        self.touch("src/d.ts", "after 1.1.0")
        # INDEX still points at v1.0.0 → both commits are drift against the registered release
        f = self.report()["F4"]
        self.assertEqual((f["base"], len(f["offending_commits"])), ("spec/F4-e-v1.0.0", 2))

    def test_latest_tag_is_used_when_the_index_tag_is_missing(self):
        self.repo.add_feature("F4", slug="e", version="1.0.0", sources="src/d.ts")
        self.touch("src/d.ts", "between")
        self.repo.tag("spec/F4-e-v1.1.0")
        self.touch("src/d.ts", "after 1.1.0")
        self.repo.write_index_row("F4", "e", "Approved", "1.2.0", "spec/F4-e-v1.2.0")
        self.repo.commit("index points to a tag that is not there")
        f = self.report()["F4"]
        self.assertEqual((f["base_kind"], f["base"]), ("latest-tag", "spec/F4-e-v1.1.0"))
        self.assertEqual([c["subject"] for c in f["offending_commits"]], ["after 1.1.0"])

    def test_date_fallback_without_any_tag(self):
        self.repo.add_feature("F5", sources="src/e.ts", tag=None, status="Verifying", version="0.1.0",
                              last_verified="2026-01-01")
        self.touch("src/e.ts", "after")
        f = self.report()["F5"]
        self.assertEqual(f["base_kind"], "last-verified-date")

    def test_unverifiable_when_there_are_no_path_tokens(self):
        self.repo.add_feature("F3", sources="stuff", tag="auto")
        f = self.report()["F3"]
        self.assertEqual(f["status"], "unverifiable")
        self.assertIn("no file-path tokens", f["reason"])

    def test_unverifiable_without_a_sources_row(self):
        self.repo.write("docs/specs/SPEC-F6-bare.md", "# bare\n")
        self.repo.write_index_row("F6", "bare", "Approved", "1.0.0", "spec/F6-bare-v1.0.0")
        self.repo.commit("bare")
        self.assertEqual(self.report()["F6"]["status"], "unverifiable")

    def test_dead_patterns_are_reported(self):
        self.repo.add_feature("F1", sources="src/a.ts, src/none/*.ts")
        f = self.report()["F1"]
        self.assertEqual(f["dead_patterns"], ["src/none/*.ts"])
        self.assertEqual(f["status"], "clean")

    def test_subset_filter(self):
        self.repo.add_feature("F1", sources="src/a.ts")
        self.repo.add_feature("F2", sources="src/b.ts")
        self.touch("src/b.ts")
        self.assertEqual(list(self.report("F1")), ["F1"])

    def test_features_are_sorted_numerically(self):
        for n in (10, 2, 1):
            self.repo.add_feature(f"F{n}", sources=f"src/f{n}.ts")
        self.assertEqual(list(self.report()), ["F1", "F2", "F10"])

    def test_f1_tag_does_not_leak_into_f10(self):
        self.repo.add_feature("F1", slug="a", sources="src/a.ts")
        self.repo.add_feature("F10", slug="b", sources="src/b.ts")
        self.assertEqual(self.report()["F10"]["base"], "spec/F10-b-v1.0.0")

    def test_arabic_paths_are_not_quoted_away(self):
        self.repo.add_feature("F1", sources="src/ملف.ts")
        self.touch("src/ملف.ts", "edit")
        self.assertEqual(self.report()["F1"]["status"], "drifted")

    # ---------------------------------------------------------------- CLI contract
    def cli(self, *extra):
        return subprocess.run([sys.executable, "-m", "specalign", "drift", str(self.repo.path), *extra],
                              cwd=TOOLS, capture_output=True, text=True, encoding="utf-8")

    def test_exit_codes(self):
        self.repo.add_feature("F1", sources="src/a.ts")
        self.assertEqual(self.cli().returncode, 0)
        self.touch("src/a.ts")
        self.assertEqual(self.cli().returncode, 1)
        self.assertEqual(self.cli("--exit-zero").returncode, 0)
        self.assertEqual(json.loads(self.cli("--json", "--exit-zero").stdout)["schema"], "specalign.drift/1")

    def test_strict_flags_unverifiable_only(self):
        self.repo.add_feature("F3", sources="stuff")
        self.assertEqual(self.cli().returncode, 0)
        self.assertEqual(self.cli("--strict").returncode, 3)

    def test_not_a_repo_is_exit_2(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run([sys.executable, "-m", "specalign", "drift", d], cwd=TOOLS,
                               capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 2)


class DriftClassTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.cleanup)
        self.repo.write("src/shared.ts", "s\n")
        self.repo.write("src/a.ts", "a\n")
        self.repo.write("src/b.ts", "b\n")
        self.repo.add_feature("F1", "one", sources="src/shared.ts, src/a.ts")
        self.repo.add_feature("F2", "two", sources="src/shared.ts, src/b.ts")

    def report(self, only=None):
        return {f["id"]: f for f in drift.run_drift(self.repo.path, only=only)["features"]}

    def test_change_to_a_shared_file_is_ripple_and_covered_when_the_other_tag_contains_it(self):
        self.repo.write("src/shared.ts", "s2\n")
        self.repo.commit("touch shared")
        self.repo.add_feature("F2", "two", version="1.1.0", sources="src/shared.ts, src/b.ts")   # F2 re-released after
        r = self.report()
        self.assertEqual(r["F1"]["drift_class"], "ripple")
        c = r["F1"]["offending_commits"][0]
        self.assertEqual((c["class"], c["shared_with"], c["covered_by"]), ("ripple", ["F2"], ["F2"]))
        self.assertEqual(r["F2"]["status"], "clean")

    def test_change_to_an_owned_file_is_own_drift(self):
        self.repo.write("src/a.ts", "a2\n")
        self.repo.commit("touch a")
        r = self.report()
        self.assertEqual((r["F1"]["status"], r["F1"]["drift_class"]), ("drifted", "own"))
        self.assertEqual(r["F2"]["status"], "clean")

    def test_mixed_commit_counts_as_own(self):
        self.repo.write("src/shared.ts", "s3\n")
        self.repo.write("src/a.ts", "a3\n")
        self.repo.commit("both")
        self.assertEqual(self.report()["F1"]["drift_class"], "own")

    def test_cli_own_only_ignores_ripple(self):
        self.repo.write("src/shared.ts", "s2\n")
        self.repo.commit("touch shared")
        cmd = [sys.executable, "-m", "specalign", "drift", str(self.repo.path)]
        env = {"PYTHONPATH": str(TOOLS), "PATH": __import__("os").environ["PATH"], "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}
        full = subprocess.run(cmd, capture_output=True, env=env)
        own = subprocess.run(cmd + ["--own-only"], capture_output=True, env=env)
        self.assertEqual((full.returncode, own.returncode), (1, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
