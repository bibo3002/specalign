import _path  # noqa: F401

import tempfile
import unittest
from pathlib import Path

from specalign import installer


def make_source(root: Path, skill_md: str = "# skill\n") -> None:
    (root / "SKILL.md").write_bytes(skill_md.replace("\n", "\r\n").encode("utf-8"))   # CRLF on purpose
    (root / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    (root / "stages").mkdir()
    (root / "stages" / "00.md").write_text("stage 0 — صفر\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "t.py").write_text("not part of the payload\n")
    (root / "tools" / "specalign" / "__pycache__").mkdir(parents=True)
    (root / "tools" / "specalign" / "__pycache__" / "x.pyc").write_bytes(b"\0")
    (root / "tools" / "specalign" / "mod.py").write_text("x = 1\n")


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.src, self.target = base / "src", base / "home" / ".claude" / "skills" / "specalign"
        self.src.mkdir()
        make_source(self.src)

    def test_payload_excludes_tests_and_caches_and_normalises_line_endings(self):
        files = installer.payload_files(self.src)
        self.assertEqual(sorted(files), ["SKILL.md", "VERSION", "stages/00.md", "tools/specalign/mod.py"])
        self.assertNotIn(b"\r", files["SKILL.md"])

    def test_install_then_check_is_clean(self):
        r = installer.install(self.target, self.src)
        self.assertTrue(r["installed"])
        self.assertEqual(sorted(r["written"]), ["SKILL.md", "VERSION", "stages/00.md", "tools/specalign/mod.py"])
        chk = installer.check(self.target, self.src)
        self.assertTrue(chk["ok"], chk)
        self.assertEqual(chk["version"], "1.2.3")
        self.assertEqual((self.target / "stages" / "00.md").read_text(encoding="utf-8"), "stage 0 — صفر\n")

    def test_second_install_writes_nothing(self):
        installer.install(self.target, self.src)
        self.assertEqual(installer.install(self.target, self.src)["written"], [])

    def test_hand_edit_is_detected_and_blocks_update(self):
        installer.install(self.target, self.src)
        (self.target / "SKILL.md").write_text("edited by hand\n")
        chk = installer.check(self.target, self.src)
        self.assertFalse(chk["ok"])
        self.assertEqual(chk["hand_edited"], ["SKILL.md"])
        (self.src / "VERSION").write_text("1.2.4\n")
        refused = installer.install(self.target, self.src)
        self.assertTrue(refused["refused"])
        self.assertEqual((self.target / "SKILL.md").read_text(), "edited by hand\n")   # untouched
        forced = installer.install(self.target, self.src, force=True)
        self.assertTrue(forced["installed"])
        self.assertTrue(installer.check(self.target, self.src)["ok"])

    def test_source_change_makes_target_out_of_date_until_synced(self):
        installer.install(self.target, self.src)
        (self.src / "stages" / "00.md").write_text("changed\n", encoding="utf-8")
        self.assertEqual(installer.check(self.target, self.src)["out_of_date"], ["stages/00.md"])
        installer.install(self.target, self.src)
        self.assertTrue(installer.check(self.target, self.src)["ok"])

    def test_missing_file_is_detected(self):
        installer.install(self.target, self.src)
        (self.target / "VERSION").unlink()
        self.assertEqual(installer.check(self.target, self.src)["missing"], ["VERSION"])

    def test_files_dropped_from_source_are_removed_but_unknown_files_are_kept(self):
        installer.install(self.target, self.src)
        (self.target / "my-notes.md").write_text("mine\n")
        (self.src / "stages" / "00.md").unlink()
        r = installer.install(self.target, self.src)
        self.assertEqual(r["removed"], ["stages/00.md"])
        self.assertTrue((self.target / "my-notes.md").exists())
        self.assertEqual(installer.check(self.target, self.src)["unexpected"], ["my-notes.md"])

    def test_dry_run_changes_nothing(self):
        r = installer.install(self.target, self.src, dry_run=True)
        self.assertTrue(r["written"])
        self.assertFalse(self.target.exists())

    def test_cli_installs_global_and_project_copies(self):
        home, proj = Path(self._tmp.name) / "h2", Path(self._tmp.name) / "proj"
        proj.mkdir()
        # source_root() is the real repo; install it for real into the temp locations
        code = installer.main(["--home", str(home), "--project", str(proj)])
        self.assertEqual(code, 0)
        self.assertTrue((home / ".claude" / "skills" / "specalign" / installer.MANIFEST).exists())
        self.assertTrue((proj / ".opencode" / "skills" / "specalign" / "SKILL.md").exists())
        self.assertEqual(installer.main(["--home", str(home), "--project", str(proj), "--check"]), 0)
        (proj / ".opencode" / "skills" / "specalign" / "SKILL.md").write_text("tampered\n")
        self.assertEqual(installer.main(["--home", str(home), "--project", str(proj), "--check"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
