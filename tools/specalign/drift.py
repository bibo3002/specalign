"""Drift detection: which commits changed a spec's declared sources after its release tag.

Replaces scripts/drift_probe.py. Differences that matter:
  * the §0 Card `Sources` line is parsed token by token (brace groups, globs, directories,
    parenthetical notes, `tests`/`tables` labels); one odd token no longer voids the feature;
  * the comparison range is `<tag>..HEAD` (exact), not a time window;
  * renames count as a change of the old path;
  * sources that match no tracked file are reported as dead patterns.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .common import (
    SpecAlignError, card_feature_id, git, git_ok, norm_tag, parse_card, parse_index, read_text,
    require_repo, spec_files, tag_version,
)
from .registry import resolve_tag_prefix

SCHEMA = "specalign.drift/1"


# --------------------------------------------------------------------------- Sources parsing

def _strip_parens(s: str) -> str:
    """Remove balanced (...) groups (annotations such as `(:709,:861)` or `(the per-file functions)`)."""
    out: list[str] = []
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth:
                depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def _split_top(s: str, seps: str = ",;") -> list[str]:
    """Split on separators that are outside {...} groups."""
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in s:
        if ch == "{":
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
        if depth == 0 and ch in seps:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def brace_expand(s: str) -> list[str]:
    """`a/{b,c/{d,e}}.ts` → ['a/b.ts', 'a/c/d.ts', 'a/c/e.ts']. Unbalanced braces stay literal."""
    i = s.find("{")
    if i < 0:
        return [s]
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                break
    else:
        return [s]
    pre, inner, post = s[:i], s[i + 1:j], s[j + 1:]
    out: list[str] = []
    for alt in _split_top(inner, ","):
        for mid in brace_expand(alt):
            for tail in brace_expand(post):
                out.append(pre + mid + tail)
    return out


LABEL_RE = re.compile(r"^(tests?|tables?|migrations?)\s+(.*)$", re.IGNORECASE)
PREFIX_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z ]*\s*:\s*(.*)$")
LINE_REF_RE = re.compile(r"(?::\d+(?:[-,]\d+)*)+$")
EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,5}$")


@dataclass
class SourceSpec:
    patterns: list[str] = field(default_factory=list)
    db_objects: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def parse_sources(raw: str) -> SourceSpec:
    spec = SourceSpec()
    text = _strip_parens(raw.replace("`", ""))
    mode = "files"
    for piece in _split_top(text):
        tok = piece.strip()
        if not tok:
            continue
        m = PREFIX_LABEL_RE.match(tok)
        if m:                                   # "host :" style prefix label
            tok = m.group(1).strip()
        m = LABEL_RE.match(tok)
        if m:                                   # "tests x", "tables x"
            mode = "tables" if m.group(1).lower().startswith("table") else "files"
            tok = m.group(2).strip()
        tok = LINE_REF_RE.sub("", tok).strip()
        if not tok:
            continue
        for alt in brace_expand(tok):
            alt = alt.strip()
            if not alt:
                continue
            if re.search(r"\s", alt):
                spec.notes.append(f"unparseable source token ignored: {alt!r}")
            elif "/" in alt or EXT_RE.search(alt) or any(c in alt for c in "*?"):
                spec.patterns.append(alt)
                mode = "files"
            elif mode == "tables":
                spec.db_objects.append(alt)
            else:
                spec.notes.append(f"non-path token ignored: {alt!r}")
    return spec


def source_matches(pattern: str, path: str) -> bool:
    """Directory prefix, glob (`*` crosses `/`), or exact path / path inside a directory."""
    if pattern.endswith("/"):
        return path.startswith(pattern)
    if any(c in pattern for c in "*?["):
        return fnmatch.fnmatchcase(path, pattern)
    return path == pattern or path.startswith(pattern + "/")


def sources_line(text: str) -> str | None:
    card = parse_card(text)
    return card.get("sources")


# --------------------------------------------------------------------------- base resolution

@dataclass
class Base:
    ref: str | None        # tag name or commit hash; None = whole history
    kind: str              # index-tag | latest-tag | last-verified-date | none


def resolve_base(repo: Path, prefix: str, fid: str, index_tag: str, last_verified: str) -> Base:
    tags = [t for t in git(repo, "tag", "-l", f"{prefix}{fid}-*").split() if t.startswith(f"{prefix}{fid}-")]
    if index_tag and index_tag in tags:
        return Base(index_tag, "index-tag")
    versioned = [(tag_version(t), t) for t in tags if tag_version(t)]
    if versioned:
        return Base(max(versioned)[1], "latest-tag")
    m = re.match(r"\d{4}-\d{2}-\d{2}", last_verified or "")
    if m:
        commit = git(repo, "rev-list", "-1", f"--before={m.group(0)}T23:59:59Z", "HEAD", check=False).strip()
        return Base(commit or None, "last-verified-date")
    return Base(None, "none")


# --------------------------------------------------------------------------- commits

def commits_in_range(repo: Path, base: str | None) -> list[dict]:
    rng = f"{base}..HEAD" if base else "HEAD"
    out = git(repo, "log", rng, "--no-renames", "--name-only", "--format=%x01%H%x02%cI%x02%s")
    commits: list[dict] = []
    for chunk in out.split("\x01"):
        if not chunk.strip():
            continue
        head, _, files = chunk.partition("\n")
        parts = head.split("\x02")
        if len(parts) != 3:
            continue
        commits.append({
            "hash": parts[0], "date": parts[1], "subject": parts[2],
            "files": [f for f in files.split("\n") if f.strip()],
        })
    return commits


# --------------------------------------------------------------------------- report

@dataclass
class FeatureReport:
    id: str
    status: str                     # drifted | clean | unverifiable
    base: str | None = None
    base_kind: str = "none"
    sources: list[str] = field(default_factory=list)
    db_objects: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    dead_patterns: list[str] = field(default_factory=list)
    offending_commits: list[dict] = field(default_factory=list)
    reason: str | None = None
    drift_class: str | None = None      # own | ripple | None (clean / unverifiable)


def evaluate(fid: str, raw_sources: str | None, base: Base, repo: Path,
             tracked: list[str], history: dict[str | None, list[dict]]) -> FeatureReport:
    if not raw_sources:
        return FeatureReport(fid, "unverifiable", reason="no §0 Card `Sources` row")
    src = parse_sources(raw_sources)
    rep = FeatureReport(fid, "clean", base=base.ref, base_kind=base.kind, sources=src.patterns,
                        db_objects=src.db_objects, notes=src.notes)
    if not src.patterns:
        rep.status, rep.reason = "unverifiable", "no file-path tokens in Sources"
        return rep
    if base.kind == "none":
        rep.status, rep.reason = "unverifiable", "no tag and no last-verified date to compare against"
        return rep
    rep.dead_patterns = [p for p in src.patterns if not any(source_matches(p, f) for f in tracked)]
    commits = history[base.ref] if base.ref in history else history.setdefault(base.ref, commits_in_range(repo, base.ref))
    for c in commits:
        hit = [f for f in c["files"] if any(source_matches(p, f) for p in src.patterns)]
        if hit:
            rep.offending_commits.append({"hash": c["hash"], "date": c["date"], "subject": c["subject"], "files": hit})
    if rep.offending_commits:
        rep.status = "drifted"
    return rep


def run_drift(repo: Path, spec_dir: str = "docs/specs", tag_prefix: str | None = None,
              only: list[str] | None = None) -> dict:
    repo = require_repo(repo)
    sdir = repo / spec_dir
    if not sdir.exists():
        raise SpecAlignError(f"spec dir {sdir} does not exist")
    prefix = resolve_tag_prefix(repo, spec_dir, tag_prefix)
    index_path = sdir / "INDEX.md"
    rows = {r.fid: r for r in parse_index(read_text(index_path))} if index_path.exists() else {}
    tracked = [f for f in git(repo, "ls-files").split("\n") if f]
    history: dict[str | None, list[dict]] = {}

    reports: list[FeatureReport] = []
    patterns_by_fid: dict[str, list[str]] = {}
    bases: dict[str, Base] = {}
    ordered = sorted(spec_files(sdir).items(), key=lambda kv: int(kv[0][1:]))
    for fid, paths in ordered:                       # every spec is needed to know which files are shared
        row = rows.get(fid)
        sources = sources_line(read_text(paths[0]))
        patterns_by_fid[fid] = parse_sources(sources).patterns if sources else []
        bases[fid] = resolve_base(repo, prefix, fid, row.tag if row else "", row.last_verified if row else "")
    for fid, paths in ordered:
        if only and fid not in only:
            continue
        reports.append(evaluate(fid, sources_line(read_text(paths[0])), bases[fid], repo, tracked, history))

    _classify(repo, reports, patterns_by_fid, bases)
    return {"schema": SCHEMA, "repo": str(repo), "spec_dir": spec_dir, "tag_prefix": prefix,
            "features": [asdict(r) for r in reports]}


def _classify(repo: Path, reports: list[FeatureReport], patterns: dict[str, list[str]], bases: dict[str, Base]) -> None:
    """Split drift into the feature's own changes and ripple from files other specs also document.

    A commit is `ripple` for F when every file it touches in F's sources is also a source of another spec;
    `covered_by` names those specs whose release tag already contains the commit (they absorbed the change, so
    F needs a ripple patch rather than a rewrite). Anything else is `own` drift."""
    ancestor_cache: dict[tuple[str, str], bool] = {}

    def contained(commit: str, ref: str | None) -> bool:
        if not ref:
            return False
        key = (commit, ref)
        if key not in ancestor_cache:
            ancestor_cache[key] = git_ok(repo, "merge-base", "--is-ancestor", commit, ref)
        return ancestor_cache[key]

    for rep in reports:
        if not rep.offending_commits:
            continue
        kinds = set()
        for c in rep.offending_commits:
            shared: dict[str, list[str]] = {}
            for f in c["files"]:
                others = sorted(g for g, pats in patterns.items()
                                if g != rep.id and any(source_matches(p, f) for p in pats))
                if others:
                    shared[f] = others
            c["shared_with"] = sorted({g for v in shared.values() for g in v})
            c["covered_by"] = sorted(g for g in c["shared_with"] if g in bases and contained(c["hash"], bases[g].ref))
            c["class"] = "ripple" if shared and len(shared) == len(c["files"]) else "own"
            kinds.add(c["class"])
        rep.drift_class = "own" if "own" in kinds else "ripple"


def human_report(payload: dict) -> str:
    feats = payload["features"]
    if not feats:
        return "No features found.\n"
    marks = {"drifted": "✗ DRIFTED", "clean": "✓ clean", "unverifiable": "? unverifiable"}
    lines = ["Drift report:"]
    for f in feats:
        lines.append(f"\n  {f['id']}: {marks[f['status']]}")
        if f["base"]:
            lines.append(f"    compared against: {f['base']} ({f['base_kind']})")
        if f["sources"]:
            lines.append(f"    sources: {len(f['sources'])} pattern(s)")
        for c in f["offending_commits"]:
            subject = c["subject"] if len(c["subject"]) <= 100 else c["subject"][:97] + "..."
            extra = ""
            if c.get("class") == "ripple":
                extra = f"  [ripple via {', '.join(c['shared_with'])}" + (f"; already in {', '.join(c['covered_by'])}" if c["covered_by"] else "") + "]"
            lines.append(f"      {c['hash'][:10]} {c['date'][:10]} {subject}{extra}")
            for p in c["files"]:
                lines.append(f"          {p}")
        for p in f["dead_patterns"]:
            lines.append(f"    dead source (matches no tracked file): {p}")
        for n in f["notes"]:
            lines.append(f"    note: {n}")
        if f["reason"]:
            lines.append(f"    reason: {f['reason']}")
    return "\n".join(lines) + "\n"
