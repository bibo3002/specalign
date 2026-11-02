"""Stage-12 finalization from a plan: dry-run by default, gated apply, tag and push.

    python -m specalign finalize plan   PLAN.json            show the exact diff, lint the result, compare files
    python -m specalign finalize apply  PLAN.json            write (needs a recorded W1/C1 naming every file)
    python -m specalign finalize staged PLAN.json            staged files must equal the plan's expect_files
    python -m specalign finalize tag    PLAN.json [--commit]  create the planned tags (needs G1/C1 naming each tag)
    python -m specalign finalize push   PLAN.json --remote R  print / run the push (needs P1/C1)

Plan (`specalign.finalize-plan/1`): {"edits": [...], "expect_files": [...], "tags": [...]}; an edit is
  {"file", "op": "append-row", "section", "cells": [...], "key"?, "table"?}
  {"file", "op": "patch-row",  "section"?, "match": {"Col": "val"}, "set": {"Col": "val"}, "with_column"?}
  {"file", "op": "set-card",   "field", "value"}
All edits are idempotent, so a half-finished apply can be re-run.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from . import lint as lint_mod
from . import manifest as manifest_mod
from . import registry as registry_mod
from .common import SpecAlignError, git, git_ok, parse_card, require_repo, norm_version
from .docedit import Doc

SCHEMA = "specalign.finalize-plan/1"
TAG_CHECKS = {"tag_exists", "tag_contains_spec_version"}      # cannot hold before the tag is created


def load_plan(path: Path) -> dict:
    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecAlignError(f"cannot read plan {path}: {exc}") from exc
    if plan.get("schema") != SCHEMA:
        raise SpecAlignError(f"plan must declare \"schema\": \"{SCHEMA}\"")
    for key in ("edits", "expect_files"):
        if not isinstance(plan.get(key), list) or not plan[key]:
            raise SpecAlignError(f"plan needs a non-empty '{key}' list")
    plan.setdefault("tags", [])
    return plan


def _rel(p: str) -> str:
    return p.replace("\\", "/")


def _apply_edits(repo: Path, plan: dict) -> dict[str, Doc]:
    docs: dict[str, Doc] = {}
    for i, e in enumerate(plan["edits"], start=1):
        rel = _rel(e["file"])
        if rel not in docs:
            path = repo / rel
            if not path.is_file():
                raise SpecAlignError(f"edit {i}: {rel} does not exist")
            docs[rel] = Doc(path)
        doc = docs[rel]
        try:
            op = e["op"]
            if op == "append-row":
                doc.append_row(list(e["cells"]), e.get("section"), e.get("table", 0), e.get("key"), e.get("with_column"))
            elif op == "patch-row":
                (mc, mv), = e["match"].items()
                doc.patch_row(mc, mv, dict(e["set"]), e.get("section"), e.get("table", 0), e.get("with_column"))
            elif op == "set-card":
                doc.set_card(e["field"], e["value"])
            elif op == "insert-block":
                doc.insert_block(e["code"], e["title"], list(e["body"]), e["after"])
            else:
                raise SpecAlignError(f"unknown op {op!r}")
        except (KeyError, ValueError) as exc:
            raise SpecAlignError(f"edit {i} ({rel}): malformed ({exc!r})") from exc
        except SpecAlignError as exc:
            raise SpecAlignError(f"edit {i} ({rel}): {exc}") from exc
    return docs


def plan_report(repo: Path, plan_path: Path, spec_dir: str = "docs/specs", tag_prefix: str | None = None) -> dict:
    repo = require_repo(repo)
    plan = load_plan(plan_path)
    docs = _apply_edits(repo, plan)
    changed = sorted(r for r, d in docs.items() if d.changed())
    expected = sorted({_rel(f) for f in plan["expect_files"]})
    problems: list[str] = []
    if sorted(set(changed) - set(expected)):
        problems.append("edits touch files not in expect_files: " + ", ".join(sorted(set(changed) - set(expected))))
    missing = sorted(set(expected) - set(changed))
    notes = [f"already applied or unchanged: {m}" for m in missing]
    prefix = registry_mod.resolve_tag_prefix(repo, spec_dir, tag_prefix)
    lint_reports = []
    for rel in changed:
        if re.search(r"SPEC-F\d+-[^/]*\.md$", rel):
            lint_reports.append(lint_mod.lint_text(docs[rel].text(), Path(rel).name, prefix))
            errs = [f for f in lint_reports[-1] if f.severity == "error"]
            for f in errs:
                problems.append(f"{rel} would fail lint: {f.rule} L{f.line} {f.message}")
    for tag in plan["tags"]:
        if not tag.startswith(prefix):
            problems.append(f"planned tag {tag!r} does not start with TAG_PREFIX {prefix!r}")
        if git_ok(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}"):
            problems.append(f"planned tag {tag!r} already exists")
    return {
        "plan": str(plan_path), "changed": changed, "expect_files": expected, "problems": problems, "notes": notes,
        "diffs": {r: docs[r].diff() for r in changed}, "ok": not problems, "_docs": docs, "_plan": plan,
    }


def apply_plan(repo: Path, plan_path: Path, spec_dir: str = "docs/specs", tag_prefix: str | None = None,
               run: str | None = None) -> dict:
    repo = require_repo(repo)
    rep = plan_report(repo, plan_path, spec_dir, tag_prefix)
    if not rep["ok"]:
        raise SpecAlignError("plan has problems:\n  " + "\n  ".join(rep["problems"]))
    _, data = manifest_mod.active(repo, run)
    statements = [a["statement"] for a in data["approvals"] if a["gate"] in {"W1", "C1"}]
    if not statements:
        raise SpecAlignError("no W1/C1 approval is recorded in the run manifest; the write gate is not closed")
    for rel in rep["changed"]:
        if not any(rel in s or Path(rel).name in s for s in statements):
            raise SpecAlignError(f"no recorded W1/C1 statement names {rel}")
    for rel in rep["changed"]:
        rep["_docs"][rel].save()
        manifest_mod.add(repo, "file", {"path": rel, "via": "finalize apply"}, run)
    reg = registry_mod.run_checks(repo, spec_dir, tag_prefix)
    blocking = [c for c in reg["checks"] if not c["passed"] and c["check"] not in TAG_CHECKS]
    rep["registry_blocking"] = [{"check": c["check"], "errors": c["errors"]} for c in blocking]
    rep["registry_tag_checks_pending"] = [c["check"] for c in reg["checks"] if not c["passed"] and c["check"] in TAG_CHECKS]
    rep["ok"] = not blocking
    return rep


def staged_check(repo: Path, plan_path: Path) -> dict:
    repo = require_repo(repo)
    plan = load_plan(plan_path)
    staged = sorted(x for x in git(repo, "diff", "--cached", "--name-only").split("\n") if x.strip())
    expected = sorted({_rel(f) for f in plan["expect_files"]})
    return {"staged": staged, "expected": expected, "extra": sorted(set(staged) - set(expected)),
            "missing": sorted(set(expected) - set(staged)), "ok": staged == expected}


def _spec_version_at(repo: Path, commit: str, rel: str) -> str:
    return norm_version(parse_card(git(repo, "show", f"{commit}:{rel}", check=False)).get("version", ""))


def create_tags(repo: Path, plan_path: Path, commit: str = "HEAD", run: str | None = None) -> list[str]:
    repo = require_repo(repo)
    plan = load_plan(plan_path)
    if not plan["tags"]:
        raise SpecAlignError("the plan lists no tags")
    rel_run, data = manifest_mod.active(repo, run)
    for tag in plan["tags"]:
        if not manifest_mod.has_approval(data, {"G1", "C1"}, [tag]):
            raise SpecAlignError(f"no G1/C1 approval naming {tag} is recorded; refusing to tag")
        if git_ok(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}"):
            raise SpecAlignError(f"tag {tag} already exists (tags are frozen baselines)")
    # the run record changes after the commit (G1/P1 are recorded then), so it never counts as "dirty"
    ignore = [f":(exclude){Path(rel_run).parent.as_posix()}", ":(exclude).specalign"]
    if git(repo, "status", "--porcelain", "--untracked-files=no", "--", ".", *ignore).strip():
        raise SpecAlignError("tracked files are modified; commit the finalization first, then tag")
    sha = git(repo, "rev-parse", commit).strip()
    created = []
    for tag in plan["tags"]:
        m = re.search(r"/?(F\d+)-.+-v(\d+\.\d+\.\d+)$", tag)
        if m:
            fid, want = m.group(1), m.group(2)
            for rel in sorted({_rel(e["file"]) for e in plan["edits"]}):
                if Path(rel).name.startswith(f"SPEC-{fid}-"):
                    have = _spec_version_at(repo, sha, rel)
                    if have != want:
                        raise SpecAlignError(f"{rel} at {sha[:8]} is v{have or '?'}, but tag {tag} says v{want}")
        git(repo, "tag", tag, sha)
        manifest_mod.add(repo, "tag", {"name": tag, "commit": sha}, run)
        created.append(tag)
    return created


def push_command(repo: Path, plan_path: Path, remote: str, branch: str | None = None, run: str | None = None) -> list[str]:
    repo = require_repo(repo)
    plan = load_plan(plan_path)
    _, data = manifest_mod.active(repo, run)
    if not manifest_mod.has_approval(data, {"P1", "C1"}, [remote]):
        raise SpecAlignError(f"no P1/C1 approval naming remote {remote!r} is recorded; refusing to push")
    for tag in plan["tags"]:
        if not manifest_mod.has_approval(data, {"P1", "C1"}, [tag]):
            raise SpecAlignError(f"the recorded push approval does not name {tag}")
    branch = branch or git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    return ["git", "push", remote, branch, *plan["tags"]]


def run_push(repo: Path, cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=str(repo), check=False).returncode
