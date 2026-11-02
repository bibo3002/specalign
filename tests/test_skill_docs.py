"""Conformance tests for the skill's own documents: size budgets, no dangling references, no phantom commands."""
import _path  # noqa: F401

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_DIRS = ["stages", "modes", "gates"]
REF_RE = re.compile(r"`((?:stages|modes|gates|templates|references|adapters|scripts|tools)/[A-Za-z0-9_./*<>{}-]+?)`")
PLANNED = ()


def docs():
    files = [ROOT / "SKILL.md"]
    for d in DOC_DIRS:
        files += sorted((ROOT / d).glob("*.md"))
    return files


class SkillDocTests(unittest.TestCase):
    def test_router_stays_short(self):
        n = len((ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(n, 150, f"SKILL.md has {n} lines; move detail into stages/modes/gates")

    def test_stage_and_gate_files_stay_small(self):
        for d in DOC_DIRS:
            for f in (ROOT / d).glob("*.md"):
                n = len(f.read_text(encoding="utf-8").splitlines())
                self.assertLessEqual(n, 80, f"{f.relative_to(ROOT)} has {n} lines")

    def test_every_referenced_file_exists(self):
        missing = []
        for f in docs():
            for ref in REF_RE.findall(f.read_text(encoding="utf-8")):
                if any(c in ref for c in "<>{}*"):
                    continue
                target = ROOT / ref
                if not (target.exists() or ref.endswith("/") and (ROOT / ref.rstrip("/")).exists()):
                    missing.append(f"{f.relative_to(ROOT)} → {ref}")
        self.assertEqual(missing, [])

    def test_stage_files_are_numbered_without_gaps_and_match_the_router(self):
        names = sorted(p.name for p in (ROOT / "stages").glob("*.md"))
        self.assertEqual([n[:2] for n in names], [f"{i:02d}" for i in range(len(names))])
        router = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for n in names:
            self.assertIn(f"stages/{n}", router, f"{n} is not in the router's pipeline table")

    def test_no_instruction_calls_a_command_that_is_not_shipped(self):
        bad = []
        for f in docs():
            for m in re.finditer(r"python -m specalign (\w+)", f.read_text(encoding="utf-8")):
                if m.group(1) in PLANNED:
                    bad.append(f"{f.relative_to(ROOT)}: {m.group(0)}")
        self.assertEqual(bad, [])

    def test_every_shipped_command_mentioned_exists_in_the_cli(self):
        from specalign.cli import build_parser
        parser = build_parser()
        known = set(parser._subparsers._group_actions[0].choices)
        for f in docs():
            for m in re.finditer(r"python -m specalign (\w+)", f.read_text(encoding="utf-8")):
                self.assertIn(m.group(1), known, f"{f.relative_to(ROOT)}: unknown command {m.group(1)!r}")

    def test_router_tools_table_lists_every_cli_command(self):
        from specalign.cli import build_parser
        known = set(build_parser()._subparsers._group_actions[0].choices)
        router = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for cmd in sorted(known):
            self.assertRegex(router, rf"\|\s*`{cmd}\b", f"SKILL.md tools table lacks a row for `{cmd}`")

    def test_legacy_stage_numbers_do_not_leak_into_new_documents(self):
        """The old numbering (12.5, 4.5, 13.5) survives only in the router's legacy column."""
        for f in docs():
            if f.name == "SKILL.md":
                continue
            self.assertFalse(re.search(r"\bStage (4\.5|12\.5|13\.5|11\.5)\b", f.read_text(encoding="utf-8")), f.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
