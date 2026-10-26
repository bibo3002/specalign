#!/usr/bin/env python3
"""SpecAlign drift probe (v0.10.0).

Read-only. Walks SPEC_DIR for SPEC-F*.md, parses each §0 Card Sources line, computes
a per-feature watermark (newest of: finalization tag commit date · INDEX last_verified),
and reports any git commits that touched source paths after the watermark.

Stdlib-only. Invocation:
    python3 scripts/drift_probe.py <repo_root> [--spec-dir <path>] [drift [F-ids...]] [--json]

Output: human table by default; --json for machine-readable report (stable contract
for future CI use).

Limitations (stated, not hidden):
  - DB-only changes invisible unless inside a listed source file.
  - Source tokens that are not file paths (e.g., bare words, table names) report the
    feature as `unverifiable`; fix the spec's §0 Card Sources line at next SYNC.
  - Watermark trusts git history integrity.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# §0 Card row pattern: "| Sources | {value} |"
SOURCES_ROW_RE = re.compile(r"^\s*\|\s*Sources\s*\|\s*(.+?)\s*\|\s*$", re.MULTILINE)
# A token that *looks like* a repo-relative file path: starts with a segment and contains /
PATH_TOKEN_RE = re.compile(r"`?([A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+)`?")
# Filename-only heuristic for sources like "server/index.ts" (already a path)
INDEX_ROW_ID_RE = re.compile(r"^\|\s*(F\d+)\s*\|", re.MULTILINE)
LAST_VERIFIED_RE = re.compile(r"^\|\s*(F\d+)\s*\|.*\|\s*([\d-]+)\s*\|\s*✓", re.MULTILINE)
TAG_PREFIX_DEFAULT = "spec/"


def _git(args: list[str], cwd: Path) -> str:
    """Run git in cwd; return stdout. Raises on non-zero exit."""
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True
    )
    return proc.stdout


def parse_sources(spec_text: str) -> tuple[list[str], list[str]]:
    """Return (paths, warnings). `paths` is the list of repo-relative file paths
    extracted from the §0 Card Sources row. Tokens that don't look like file paths
    become warnings (the spec is unverifiable)."""
    m = SOURCES_ROW_RE.search(spec_text)
    if not m:
        return [], ["no §0 Card `Sources` row found"]
    raw = m.group(1)
    tokens = [t.strip() for t in raw.split(",")]
    paths: list[str] = []
    warnings: list[str] = []
    for tok in tokens:
        # Strip backticks and trailing parenthesized annotations like `(:709,:861)`
        clean = re.sub(r"`", "", tok)
        clean = re.sub(r"\s*\([^)]*\)\s*$", "", clean).strip()
        if not clean:
            continue
        if "/" in clean or clean.endswith((".ts", ".vue", ".js", ".py", ".sql", ".md")):
            paths.append(clean)
        else:
            warnings.append(f"unparseable source token: {tok!r}")
    return paths, warnings


def spec_feature_id(spec_text: str, fallback_path: Path) -> str | None:
    """Try §0 Card `Feature | F{n} - title` then fallback to SPEC-F{n}-slug in filename."""
    m = re.search(r"^\|\s*Feature\s*\|\s*(F\d+)\b", spec_text, re.MULTILINE)
    if m:
        return m.group(1)
    fm = re.search(r"SPEC-(F\d+)-", fallback_path.name)
    return fm.group(1) if fm else None


def index_meta(index_text: str) -> dict[str, str]:
    """Return {F-id: last_verified_date} parsed from INDEX.md table rows."""
    out: dict[str, str] = {}
    # Pattern finds: | F4 | ... | tag | 2026-08-23 | ✓ |
    for m in re.finditer(
        r"^\|\s*(F\d+)\s*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|[^|\n]*\|\s*([\d-]+)\s*\|",
        index_text, re.MULTILINE,
    ):
        out[m.group(1)] = m.group(2)
    return out


def watermark_dates(spec_id: str, tag_prefix: str, repo: Path) -> tuple[str | None, str]:
    """Return (watermark_iso_date_or_None, source_label). Source tells us which signal won.
    Watermark is EXCLUSIVE: we add 1 second to the tag's commit timestamp so that
    the finalization commit itself is NOT considered drift."""
    try:
        # Use `git tag -l` with pattern for listing + sorting
        pattern = f"{tag_prefix}{spec_id}-*"
        out = _git(["tag", "-l", pattern, "--sort=-creatordate"], cwd=repo)
        tags = [t for t in out.splitlines() if t.startswith(f"{tag_prefix}{spec_id}-")]
    except subprocess.CalledProcessError:
        tags = []
    tag_date = None
    if tags:
        try:
            # Get committer date of the tagged commit, add 1 second to make watermark EXCLUSIVE
            raw = _git(["log", "-1", "--format=%cI", tags[0]], cwd=repo).strip()
            if raw:
                from datetime import datetime, timezone, timedelta
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                dt = dt + timedelta(seconds=1)
                tag_date = dt.isoformat().replace("+00:00", "Z")
            else:
                tag_date = None
        except (subprocess.CalledProcessError, ValueError):
            tag_date = None
    return tag_date, ("tag" if tag_date else "fallback")


def commits_since(paths: list[str], watermark_iso: str, repo: Path) -> list[dict[str, str]]:
    """Return commits touching any of `paths` with author date >= watermark."""
    out: list[dict[str, str]] = []
    for p in paths:
        try:
            log_out = _git(
                ["log", f"--since={watermark_iso}", "--format=%H|%cI|%s", "--", p],
                cwd=repo,
            )
        except subprocess.CalledProcessError:
            continue
        for line in log_out.splitlines():
            if not line.strip():
                continue
            parts = line.split("|", 2)
            if len(parts) != 3:
                continue
            hash_, date, subject = parts
            out.append({"hash": hash_, "date": date, "subject": subject, "path": p})
    return out


@dataclasses.dataclass
class FeatureReport:
    id: str
    status: str  # "drifted" | "clean" | "unverifiable"
    watermark: str | None = None
    sources: list[str] = dataclasses.field(default_factory=list)
    offending_commits: list[dict[str, str]] = dataclasses.field(default_factory=list)
    reason: str | None = None

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def evaluate_feature(
    spec_id: str,
    sources: list[str],
    warnings: list[str],
    watermark_iso: str | None,
    repo: Path,
) -> FeatureReport:
    if warnings:
        return FeatureReport(
            id=spec_id, status="unverifiable", sources=sources,
            reason="; ".join(warnings),
        )
    if not watermark_iso:
        return FeatureReport(
            id=spec_id, status="unverifiable", sources=sources,
            reason="no watermark (no tag and no last_verified date)",
        )
    commits = commits_since(sources, watermark_iso, repo)
    return FeatureReport(
        id=spec_id,
        status="drifted" if commits else "clean",
        watermark=watermark_iso,
        sources=sources,
        offending_commits=commits,
    )


def human_report(reports: list[FeatureReport]) -> str:
    if not reports:
        return "No features found.\n"
    lines = ["Feature report:"]
    for r in reports:
        marker = {"drifted": "✗ DRIFTED", "clean": "✓ clean", "unverifiable": "? unverifiable"}[r["status"]]
        lines.append(f"\n  {r['id']}: {marker}")
        if r["watermark"]:
            lines.append(f"    watermark: {r['watermark']}")
        if r["sources"]:
            lines.append(f"    sources:   {', '.join(r['sources'])}")
        if r["offending_commits"]:
            lines.append(f"    offending ({len(r['offending_commits'])}):")
            for c in r["offending_commits"]:
                lines.append(f"      {c['hash'][:10]} {c['date'][:10]} {c['subject']} ({c['path']})")
        if r["reason"]:
            lines.append(f"    reason: {r['reason']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="drift_probe", description="SpecAlign drift probe")
    parser.add_argument("repo", help="path to the repo root")
    parser.add_argument("action", nargs="?", default="drift", choices=["drift"],
                        help="command (currently only 'drift')")
    parser.add_argument("filter", nargs="*", help="optional F-id subset filter")
    parser.add_argument("--spec-dir", default="docs/specs",
                        help="SPEC_DIR relative to repo (default: docs/specs)")
    parser.add_argument("--tag-prefix", default=TAG_PREFIX_DEFAULT,
                        help=f"tag prefix (default: {TAG_PREFIX_DEFAULT})")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of human table")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"error: {repo} is not a git repository", file=sys.stderr)
        return 2
    spec_dir = repo / args.spec_dir
    if not spec_dir.exists():
        print(f"error: spec dir {spec_dir} does not exist", file=sys.stderr)
        return 2

    # Load INDEX metadata (last_verified) once
    index_path = spec_dir / "INDEX.md"
    index_text = index_path.read_text() if index_path.exists() else ""
    idx_meta = index_meta(index_text)

    # Walk specs
    specs = sorted(spec_dir.glob("SPEC-F*.md"))
    if args.filter:
        specs = [s for s in specs if (spec_id := spec_feature_id(s.read_text(), s)) and spec_id in args.filter]

    reports: list[FeatureReport] = []
    for sp in specs:
        text = sp.read_text()
        fid = spec_feature_id(text, sp)
        if not fid:
            continue
        sources, warnings = parse_sources(text)
        wm_iso, _ = watermark_dates(fid, args.tag_prefix, repo)
        # Fallback: last_verified if no tag
        if not wm_iso and fid in idx_meta:
            wm_iso = f"{idx_meta[fid]}T00:00:00Z"
        reports.append(evaluate_feature(fid, sources, warnings, wm_iso, repo))

    payload = {
        "repo": str(repo),
        "spec_dir": str(spec_dir),
        "features": [r.to_json() for r in reports],
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(human_report([r.to_json() for r in reports]))
    # Exit 0 if no drift, 1 if drift detected, 2 only on hard errors above.
    return 1 if any(r.status == "drifted" for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
