"""Dry-run adoptions: the tools walk a project that is not Sanad through a whole GENESIS-style run.

Two shapes, because the release criteria ask for more than one stack:
  * a small Python service (decorator routes, SQLite, pytest-style tests, no UI)
  * a tiny library with no database and no UI at all
Each run: preflight → manifest (T1 → stages) → draft spec → lint → finalize plan/apply → commit → tag → registry check,
then a code change and drift/inventory to see the spec go stale.
"""
import _path  # noqa: F401  (puts tools/ on sys.path)

import json
import tempfile
import unittest
from pathlib import Path

from fixture import Repo
from specalign.common import SpecAlignError
from specalign import drift, finalize, inventory, lint, manifest, preflight, registry
from test_lint import make_spec

BINDING = """# Project binding

PROJECT_MAP: README.md
SPEC_DIR: docs/specs
REGISTRY: docs/specs/INDEX.md
DB_TOOL: {db}
UI_TOOL: none
TAG_PREFIX: docs-spec/
TEST_DATA_PREFIX: __TEST_
BASELINE_DATE: 2026-01-01
TEST_COMMAND: python -m pytest -q

TEST_ACCOUNTS:
  - none

CONVENTIONS:
  English prose.

PROJECT_PITFALLS:
  - none
"""

SERVICE = '''from flask import Blueprint
bp = Blueprint("inv", __name__)

@bp.get("/items/<int:item_id>")
def get_item(item_id): ...

@bp.post("/items")
def create_item(): ...

@bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    db.execute("DELETE FROM items WHERE id = ?", item_id)
'''


class AdoptionBase(unittest.TestCase):
    db = "none"
    sources = ""
    slug = ""
    section6 = ""

    def setUp(self):
        self.repo = Repo(binding=BINDING.format(db=self.db))
        self.addCleanup(self.repo.cleanup)
        self.p = self.repo.path
        self.repo.write_index_row("F1", self.slug, "Undocumented", "—", "—")
        self.write_code()
        self.repo.commit("project code")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.plan_path = Path(tmp.name) / "plan.json"

    def write_code(self):
        raise NotImplementedError

    def spec_text(self):
        text = make_spec(status="Draft", tag=f"docs-spec/F1-{self.slug}-v1.0.0")
        text = text.replace("`src/a.ts`, `src/b/*`", self.sources)
        return text.replace("## §6 API\n\ntext.", "## §6 API\n\n" + self.section6) if self.section6 else text

    def run_gate_sequence(self):
        pf = preflight.run_preflight(self.p)
        self.assertTrue(pf["ok"], pf["findings"])
        rel = manifest.init(self.p, "docs/specs", "F1", "genesis", "Standard", date="2026-02-01")
        manifest.set_stage(self.p, 1)
        manifest.approve(self.p, "T1", "I classify this run as Standard per the agent's recommendation; discussion, "
                         "citation discipline and final approval remain mandatory.", "Standard, 1.0.0")
        for n in range(2, 12):
            if n == 11:
                break
            manifest.set_stage(self.p, n)
        self.repo.write(f"docs/specs/SPEC-F1-{self.slug}.md", self.spec_text())
        self.repo.commit("draft")
        return rel

    def finalize_and_tag(self):
        spec = f"docs/specs/SPEC-F1-{self.slug}.md"
        tag = f"docs-spec/F1-{self.slug}-v1.0.0"
        plan = {"schema": finalize.SCHEMA, "edits": [
            {"file": spec, "op": "set-card", "field": "Status", "value": "Approved"},
            {"file": "docs/specs/INDEX.md", "op": "patch-row", "match": {"ID": "F1"},
             "set": {"Status": "Approved", "Version": "1.0.0", "Tag": tag}}],
            "expect_files": [spec, "docs/specs/INDEX.md"], "tags": [tag]}
        self.plan_path.write_text(json.dumps(plan), encoding="utf-8")
        rep = finalize.plan_report(self.p, self.plan_path, tag_prefix="docs-spec/")
        self.assertTrue(rep["ok"], rep["problems"])
        manifest.approve(self.p, "W1", f"I approve writing/editing {spec}, docs/specs/INDEX.md for F1 v1.0.0, "
                         "including the finalization commit.", "approve the write")
        manifest.set_stage(self.p, 11)
        manifest.set_stage(self.p, 12)
        applied = finalize.apply_plan(self.p, self.plan_path, tag_prefix="docs-spec/")
        self.assertTrue(applied["ok"], applied.get("registry_blocking"))
        self.repo.git("add", spec, "docs/specs/INDEX.md")
        self.assertTrue(finalize.staged_check(self.p, self.plan_path)["ok"])
        self.repo.commit("finalize F1")
        manifest.approve(self.p, "G1", f"I approve creating the tag(s) {tag}.", "tag it")
        self.assertEqual(finalize.create_tags(self.p, self.plan_path), [tag])
        return tag


class PythonServiceAdoption(AdoptionBase):
    db = "sqlite file app.db"
    slug = "items"
    sources = "`app/items.py`, tests `tests/test_items.py`, tables `items`"
    section6 = "| `GET /items/:id` | x |\n| `POST /items` | y |\n| `DELETE /items/:id` | z |"

    def write_code(self):
        self.repo.write("app/items.py", SERVICE)
        self.repo.write("tests/test_items.py", "def test_get(): assert True\n")

    def test_full_run_then_drift(self):
        self.run_gate_sequence()
        self.assertEqual(lint.lint_text(self.spec_text(), "SPEC-F1-items.md", "docs-spec/"), [])
        tag = self.finalize_and_tag()
        reg = registry.run_checks(self.p)
        self.assertEqual(reg["summary"]["failed"], 0, reg)
        self.assertTrue(manifest.verify(self.p)["ok"])
        self.assertEqual(drift.run_drift(self.p)["features"][0]["status"], "clean")
        inv = inventory.run_inventory(self.p)["features"][0]
        self.assertEqual((inv["undocumented"], inv["missing_in_code"]), ([], []))

        # the code moves on: a new route appears, the spec goes stale and the tools say so
        self.repo.write("app/items.py", SERVICE + '\n@bp.put("/items/<int:item_id>")\ndef update_item(item_id): ...\n')
        self.repo.commit("add PUT")
        d = drift.run_drift(self.p)["features"][0]
        self.assertEqual((d["status"], d["drift_class"], d["base"]), ("drifted", "own", tag))
        inv = inventory.run_inventory(self.p)["features"][0]
        self.assertEqual(len(inv["undocumented"]), 1)
        self.assertIn("PUT /items/:p", inv["undocumented"][0])

    def test_gates_hold_in_a_non_sanad_project(self):
        self.run_gate_sequence()
        with self.assertRaises(SpecAlignError) as cm:
            manifest.set_stage(self.p, 12)                      # the write gate (stage 11) was never passed
        self.assertIn("cannot jump", str(cm.exception))
        manifest.set_stage(self.p, 11)
        with self.assertRaises(SpecAlignError) as cm:
            manifest.set_stage(self.p, 12)                      # no W1 recorded
        self.assertIn("W1", str(cm.exception))


class LibraryAdoption(AdoptionBase):
    slug = "slugify"
    sources = "`src/slugify.py`, tests `tests/test_slugify.py`"
    section6 = "N/A — a library with no network API."

    def write_code(self):
        self.repo.write("src/slugify.py", "def slugify(text):\n    return text.lower().replace(' ', '-')\n")
        self.repo.write("tests/test_slugify.py", "def test_it(): assert True\n")

    def test_no_db_no_ui_feature_goes_through_the_whole_flow(self):
        self.run_gate_sequence()
        self.finalize_and_tag()
        self.assertEqual(registry.run_checks(self.p)["summary"]["failed"], 0)
        inv = inventory.run_inventory(self.p)["features"][0]
        self.assertEqual((inv["endpoints_in_code"], inv["endpoints_in_spec"]), (0, 0))
        (self.p / "src" / "slugify.py").write_text("def slugify(t):\n    return t\n", encoding="utf-8")
        self.repo.commit("change behaviour")
        self.assertEqual(drift.run_drift(self.p)["features"][0]["drift_class"], "own")


if __name__ == "__main__":
    unittest.main()
