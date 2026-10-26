"""Tests for scripts/drift_probe.py. Run: python3 -m unittest scripts.test_drift_probe -v

Builds throwaway git repos as fixtures. RED before the script exists.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "drift_probe.py"


def run(args, cwd, env=None, input_bytes=None):
    """Run python3 drift_probe.py with args; return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env={**os.environ, "LC_ALL": "C.UTF-8", **({} if env is None else env)},
        input=input_bytes,
    )
    return proc.returncode, proc.stdout, proc.stderr


def git(args, cwd, **kw):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True, **kw
    )


class FixtureRepo:
    """A minimal repo with SPEC/INDEX layout. add_spec adds a feature; add_touch_commit
    adds a later commit that touches a source file (the drift signal)."""

    def __init__(self, spec_dir="docs/specs", initial_date="2026-01-01T00:00:00Z"):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.spec_dir_rel = spec_dir
        git(["init", "-q", "-b", "main"], cwd=self.path)
        git(["config", "user.email", "specalign@example.invalid"], cwd=self.path)
        git(["config", "user.name", "SpecAlign Test"], cwd=self.path)
        git(["config", "commit.gpgsign", "false"], cwd=self.path)
        # Baseline commit (sets BASELINE_DATE source) with a non-source file
        (self.path / "README.md").write_text("# test repo\n")
        git(["add", "README.md"], cwd=self.path)
        self._commit_at(initial_date, "chore: baseline")

    def add_spec(
        self,
        fid,
        title,
        sources,
        tag,
        registry_status="Approved",
        last_verified="2026-08-15",
    ):
        spec_path = self.path / self.spec_dir_rel / f"SPEC-{fid}-{title}.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        sources_str = ", ".join(sources)
        spec_path.write_text(
            f"""---
## §0 Card

| Field | Value |
|---|---|
| Feature | {fid} - {title} |
| Sources | {sources_str} |
"""
        )
        # Create the source files referenced (so git log <path> works)
        for src in sources:
            if src.endswith("/") or "/" not in src:
                continue
            p = self.path / src
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text(f"# initial {src}\n")
        git(["add", "-A"], cwd=self.path)
        self._commit_at("2026-08-15T12:00:00Z", f"docs(specs): add SPEC-{fid}")
        git(["tag", tag], cwd=self.path)
        # INDEX row
        index_path = self.path / self.spec_dir_rel / "INDEX.md"
        existing = ""
        if index_path.exists():
            existing = index_path.read_text()
        new_row = (
            f"| {fid} | {title} | Page | {registry_status} | 1.0.0 "
            f"| {tag} | {last_verified} | ✓ | ✓ | ✓ |\n"
        )
        index_path.write_text(
            (existing or "# Registry\n| ID | Title | Type | Status | Version | Tag | Last verified | Code | DB | Behavior |\n|---|---|---|---|---|---|---|---|---|---|\n")
            + new_row
        )
        git(["add", "-A"], cwd=self.path)
        self._commit_at("2026-08-15T12:30:00Z", f"docs(specs): registry row {fid}")

    def add_touch_commit(self, source_path, message="feat: edit source", date="2026-09-01T00:00:00Z"):
        """Simulate code drift: a commit AFTER the spec tag that edits a source file."""
        full = self.path / source_path
        full.write_text(f"# drift edit {source_path} at {date}\n")
        git(["add", source_path], cwd=self.path)
        self._commit_at(date, message)

    def _commit_at(self, iso_date, message):
        env = {**os.environ, "GIT_AUTHOR_DATE": iso_date, "GIT_COMMITTER_DATE": iso_date}
        subprocess.run(
            ["git", "commit", "-q", "-m", message],
            cwd=str(self.path), check=True, env=env,
        )

    def cleanup(self):
        self.tmp.cleanup()


class DriftProbeTests(unittest.TestCase):
    def setUp(self):
        self.fx = FixtureRepo()
        self.addCleanup(self.fx.cleanup)

    def _run_json(self, *args):
        rc, out, err = run([str(self.fx.path), *args, "--json"], cwd=self.fx.path)
        self.assertIn(rc, (0, 1), f"non-zero exit; stderr={err}")
        return json.loads(out)

    def test_clean_when_no_post_tag_source_changes(self):
        self.fx.add_spec("F1", "files-list", ["src/a.ts", "src/b.ts"], "spec/F1-foo-v1.0.0")
        result = self._run_json("drift")
        self.assertEqual(len(result["features"]), 1)
        f = result["features"][0]
        self.assertEqual(f["id"], "F1")
        self.assertEqual(f["status"], "clean")
        self.assertEqual(f["offending_commits"], [])
        self.assertIn("watermark", f)

    def test_drifted_when_source_touched_after_tag(self):
        self.fx.add_spec("F2", "parties", ["src/c.ts"], "spec/F2-parties-v1.0.0")
        self.fx.add_touch_commit("src/c.ts")
        result = self._run_json("drift")
        f = result["features"][0]
        self.assertEqual(f["status"], "drifted")
        self.assertEqual(len(f["offending_commits"]), 1)
        c = f["offending_commits"][0]
        self.assertIn("hash", c)
        self.assertIn("date", c)
        self.assertIn("subject", c)

    def test_subset_filter(self):
        self.fx.add_spec("F1", "one", ["src/a.ts"], "spec/F1-v1.0.0")
        self.fx.add_spec("F2", "two", ["src/b.ts"], "spec/F2-v2.0.0")
        self.fx.add_touch_commit("src/b.ts")
        result = self._run_json("drift", "F1")
        self.assertEqual([f["id"] for f in result["features"]], ["F1"])
        self.assertEqual(result["features"][0]["status"], "clean")

    def test_unverifiable_when_sources_unparsable(self):
        self.fx.add_spec("F3", "wild", ["stuff"], "spec/F3-w-v1.0.0")
        result = self._run_json("drift")
        f = result["features"][0]
        self.assertEqual(f["status"], "unverifiable")
        self.assertIn("reason", f)

    def test_multi_tag_uses_newest(self):
        self.fx.add_spec("F4", "evolving", ["src/d.ts"], "spec/F4-e-v1.0.0")
        self.fx.add_touch_commit("src/d.ts", date="2026-09-15T00:00:00Z")
        git(["tag", "spec/F4-e-v1.1.0"], cwd=self.fx.path)
        self.fx.add_touch_commit("src/d.ts", date="2026-10-01T00:00:00Z", message="feat: post-v1.1.0")
        result = self._run_json("drift")
        f = result["features"][0]
        self.assertEqual(f["status"], "drifted")
        self.assertEqual(len(f["offending_commits"]), 1)
        self.assertIn("post-v1.1.0", f["offending_commits"][0]["subject"])

    def test_watermark_prefers_tag_over_last_verified(self):
        self.fx.add_spec(
            "F5", "future", ["src/e.ts"], "spec/F5-v1.0.0", last_verified="2026-12-31"
        )
        result = self._run_json("drift")
        f = result["features"][0]
        self.assertEqual(f["status"], "clean")

    def test_human_output_default(self):
        self.fx.add_spec("F6", "human", ["src/f.ts"], "spec/F6-v1.0.0")
        self.fx.add_touch_commit("src/f.ts")
        rc, out, _ = run([str(self.fx.path), "drift"], cwd=self.fx.path)
        self.assertEqual(rc, 1)
        self.assertIn("F6", out)
        self.assertIn("drifted", out.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
