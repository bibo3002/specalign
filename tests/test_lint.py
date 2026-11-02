import _path  # noqa: F401  (puts tools/ on sys.path)

import tempfile
import unittest
from pathlib import Path

from specalign import lint
from specalign.common import SpecAlignError

BLOCK_NAMES = ["0 Card", "1 Purpose", "2 Users", "3 UI", "4 Flows", "5 Data", "6 API", "7 Frontend", "8 Validation",
               "9 Data Flow", "10 Errors", "11 Acceptance Criteria", "12 Dependencies", "13A Questions",
               "13B Verification", "13C Evolution", "13D Approval", "14 Self-Check"]


def make_spec(status="Approved", version="1.0.0", skill_version=True, df_status="Resolved(abc) — AC-01",
              overall="**Overall: PASS**", extra="", ac_row="| AC-01 | F1-1 | Given x, then y | V-1 · unit |",
              ac_header="| AC ID | Flow | Given/When/Then | Evidence |", v_label="unit", d_ref="§13B D-1",
              history_version=None, tag=None):
    tag = tag or f"spec/F1-demo-v{version}"
    card = [
        "| Field | Value |", "|---|---|", "| Feature | F1 — Demo |", "| Tier | Core |", f"| Status | {status} |",
        f"| Version | v{version} |", f"| Tag | {tag} |", "| Sources | `src/a.ts`, `src/b/*` |",
    ]
    if skill_version:
        card.insert(5, "| Skill version | SpecAlign 1.0.0 |")
    bodies = {
        "0": card,
        "4": ["F1-1 the user opens the page."],
        "11": [ac_header, "|---|---|---|---|", ac_row],
        "13A": ["| ID | Type | Item | Status |", "|---|---|---|---|", f"| DF-1 | DF high | thing | {df_status} |"],
        "13B": ["| ID | Date | What | Label | Result |", "|---|---|---|---|---|",
                f"| V-1 | 2026-01-01 | tests | {v_label} | pass |", "| D-1 | 2026-01-01 | decided | decision | ok |"],
        "13C": ["| Version | Date | Change type | Description |", "|---|---|---|---|",
                f"| v{history_version or version} | 2026-01-01 | Created | first |"],
        "13D": ["| Version | Gate | Approved by | Date | Evidence ref | Statement |", "|---|---|---|---|---|---|",
                f"| v{version} | G1 | me | 2026-01-01 | {d_ref} | «yes» |"],
        "14": ["| # | Check | ✓/✗ | Comment |", "|---|---|---|---|", "| 1 | rebuildable | ✓ | |", "", overall],
    }
    out = ["# SPEC-F1 — Demo", ""]
    for name in BLOCK_NAMES:
        code = name.split()[0]
        out += [f"## §{name}", ""] + bodies.get(code, ["text."]) + [""]
    return "\n".join(out) + extra


def rules(text, name="SPEC-F1-demo.md"):
    return [(f.rule, f.severity) for f in lint.lint_text(text, name)]


class LintTests(unittest.TestCase):
    def test_clean_v1_spec_has_no_findings(self):
        self.assertEqual(lint.lint_text(make_spec(), "SPEC-F1-demo.md"), [])

    def test_missing_and_duplicate_blocks(self):
        text = make_spec().replace("## §9 Data Flow", "## §8 Validation")
        got = rules(text)
        self.assertIn(("L01-blocks", "error"), got)
        self.assertGreaterEqual(got.count(("L01-blocks", "error")), 2)    # §9 missing + §8 duplicated

    def test_card_fields_and_status(self):
        self.assertIn(("L02-card", "error"), rules(make_spec().replace("| Status | Approved |", "| Status | Done |")))
        self.assertIn(("L02-card", "error"), rules(make_spec(), "SPEC-F2-demo.md"))      # filename ≠ card id

    def test_released_spec_tag_must_match_version(self):
        self.assertIn(("L02-card", "error"), rules(make_spec(tag="spec/F1-demo-v0.9.0")))
        self.assertNotIn(("L02-card", "error"), rules(make_spec(status="Draft", tag="spec/F1-demo-v0.9.0")))

    def test_open_df_blocks_only_released_specs(self):
        self.assertIn(("L04-df-state", "error"), rules(make_spec(df_status="Open")))
        self.assertIn(("L04-df-state", "warn"), rules(make_spec(status="Draft", df_status="Open")))

    def test_resolved_df_needs_an_existing_ac(self):
        self.assertIn(("L05-df-ac", "error"), rules(make_spec(df_status="Resolved(abc)")))          # strict
        self.assertIn(("L05-df-ac", "error"), rules(make_spec(df_status="Resolved(abc) — AC-77")))  # absent AC

    def test_legacy_format_downgrades_traceability_to_warnings(self):
        got = rules(make_spec(skill_version=False, df_status="Resolved(abc)"))
        self.assertIn(("L05-df-ac", "warn"), got)
        self.assertNotIn(("L05-df-ac", "error"), got)

    def test_ac_must_name_a_flow_and_cite_existing_evidence(self):
        self.assertIn(("L06-ac-flow", "error"), rules(make_spec(ac_row="| AC-01 | — | Given x | V-1 · unit |")))
        self.assertIn(("L06-ac-flow", "error"), rules(make_spec(ac_row="| AC-01 | F1-1 | Given x | V-9 · unit |")))
        self.assertIn(("L06-ac-flow", "error"), rules(make_spec(ac_header="| AC ID | Flow | Given/When/Then |",
                                                              ac_row="| AC-01 | F1-1 | Given x |")))

    def test_unknown_evidence_label(self):
        self.assertIn(("L07-evidence", "error"), rules(make_spec(v_label="vibes")))
        self.assertNotIn(("L07-evidence", "error"), rules(make_spec(v_label="`runtime-js-click`")))
        self.assertNotIn(("L07-evidence", "error"), rules(make_spec(skill_version=False, v_label="inject")))

    def test_approval_must_reference_an_existing_decision(self):
        self.assertIn(("L08-approval", "error"), rules(make_spec(d_ref="§13B D-9")))
        self.assertNotIn(("L08-approval", "error"), rules(make_spec(d_ref="SPEC-F6 §13B D-9")))

    def test_leftover_markers_outside_code_fences(self):
        self.assertIn(("L09-markers", "error"), rules(make_spec(extra="\nTODO fix this\n")))
        self.assertNotIn(("L09-markers", "error"), rules(make_spec(extra="\n```\nTODO in a code sample\n```\n")))

    def test_self_check_must_pass_on_released_specs(self):
        self.assertIn(("L10-selfcheck", "error"), rules(make_spec(overall="**Overall: FAIL**")))
        self.assertIn(("L10-selfcheck", "error"), rules(make_spec(overall="")))

    def test_history_must_contain_the_card_version_in_either_order(self):
        self.assertIn(("L11-history", "error"), rules(make_spec(version="1.1.0", history_version="1.0.0",
                                                              tag="spec/F1-demo-v1.1.0")))
        text = make_spec().replace("| v1.0.0 | 2026-01-01 | Created | first |",
                                   "| v1.0.1 | 2026-01-02 | Fixed | b |\n| v1.0.0 | 2026-01-01 | Created | first |")
        self.assertIn(("L11-history", "error"), rules(text))      # newer row than the card

    def test_crlf_and_arabic_content(self):
        text = make_spec(extra="\nنص عربي «حفظ»\n").replace("\n", "\r\n")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "SPEC-F1-demo.md"
            p.write_bytes(text.encode("utf-8"))
            rep = lint.lint_file(p)
        self.assertEqual(rep["errors"], 0)
        self.assertEqual(rep["format"], "v1.0")

    def test_truncated_file_is_caught(self):
        """A scripted edit that leaves a spec empty or cut off must fail lint (a typecheck would stay green)."""
        for broken in ("", "# SPEC-F1 — Demo\n", make_spec()[: len(make_spec()) // 2]):
            found = {(f.rule, f.severity) for f in lint.lint_text(broken, "SPEC-F1-demo.md")}
            self.assertIn(("L01-blocks", "error"), found)          # missing blocks, whatever survived
            if "Card" not in broken:
                self.assertIn(("L02-card", "error"), found)

    def test_run_lint_on_missing_feature_is_an_error(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / ".git").mkdir()
            (Path(td) / "docs" / "specs").mkdir(parents=True)
            with self.assertRaises(SpecAlignError):
                lint.run_lint(Path(td), features=["F9"])

    def test_the_shipped_template_lints_as_a_skeleton(self):
        tpl = Path(__file__).resolve().parents[1] / "templates" / "specification-template.md"
        found = {f.rule for f in lint.lint_text(tpl.read_text(encoding="utf-8").replace("\r\n", "\n"), "SPEC-F1-x.md")}
        self.assertNotIn("L01-blocks", found)      # all 18 blocks are in the template


if __name__ == "__main__":
    unittest.main()
