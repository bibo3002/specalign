"""Registry check: INDEX.md ↔ spec files ↔ spec §0 Card ↔ git tags.

Replaces scripts/rescan_check.py. A check can only pass when the evidence exists:
the exact tag for the exact version must be present and must contain that spec version.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .common import (
    IndexRow, SpecAlignError, card_feature_id, git, git_ok, load_binding, norm_tag, norm_version,
    parse_card, parse_index, read_text, require_repo, spec_files, status_word,
)

SCHEMA = "specalign.registry/1"
DEFAULT_TAG_PREFIX = "spec/"

# Registry statuses whose rows promise a spec file, a version and a tag.
RELEASED = {"Approved", "Stale"}

CHECK_IDS = [
    "approved_has_spec_file",
    "spec_file_has_index_row",
    "approved_tag_matches_version",
    "tag_exists",
    "tag_contains_spec_version",
    "index_matches_spec_card",
    "undocumented_no_spec_file",
    "no_duplicate_ids",
    "spec_section0_fid_matches",
]


@dataclass
class Check:
    check: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_json(self) -> dict:
        return {"check": self.check, "passed": self.passed, "errors": self.errors, "warnings": self.warnings}


def resolve_tag_prefix(repo: Path, spec_dir: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    return load_binding(repo, spec_dir).get("TAG_PREFIX") or DEFAULT_TAG_PREFIX


def _spec_at_tag(repo: Path, tag: str, rel: PurePosixPath) -> dict[str, str] | None:
    """§0 Card of the spec file as it exists in the tagged commit (None when absent)."""
    raw = git(repo, "show", f"{tag}:{rel.as_posix()}", check=False)
    return parse_card(raw.replace("\r\n", "\n")) if raw else None


def run_checks(repo: Path, spec_dir: str = "docs/specs", tag_prefix: str | None = None) -> dict:
    repo = require_repo(repo)
    sdir = repo / spec_dir
    index_path = sdir / "INDEX.md"
    if not index_path.exists():
        raise SpecAlignError(f"INDEX.md not found at {index_path}")
    prefix = resolve_tag_prefix(repo, spec_dir, tag_prefix)

    rows = parse_index(read_text(index_path))
    files = spec_files(sdir)
    checks = {cid: Check(cid) for cid in CHECK_IDS}
    by_id: dict[str, list[IndexRow]] = {}
    for r in rows:
        by_id.setdefault(r.fid, []).append(r)

    # ---- duplicates (INDEX rows and spec files)
    for fid, group in by_id.items():
        if len(group) > 1:
            lines = ", ".join(str(r.line) for r in group)
            checks["no_duplicate_ids"].errors.append(f"{fid}: {len(group)} INDEX rows (lines {lines})")
    for fid, paths in files.items():
        if len(paths) > 1:
            checks["no_duplicate_ids"].errors.append(f"{fid}: {len(paths)} spec files ({', '.join(p.name for p in paths)})")

    cards: dict[str, dict[str, str]] = {}
    for fid, paths in files.items():
        cards[fid] = parse_card(read_text(paths[0]))

    # ---- spec files need a row
    for fid, paths in files.items():
        if fid not in by_id:
            checks["spec_file_has_index_row"].errors.append(f"{fid}: {paths[0].name} exists but INDEX.md has no row")

    for r in rows:
        paths = files.get(r.fid, [])
        card = cards.get(r.fid, {})
        rel = PurePosixPath(spec_dir) / paths[0].name if paths else None

        if r.status == "Undocumented":
            if paths:
                checks["undocumented_no_spec_file"].errors.append(f"{r.fid}: marked Undocumented but {paths[0].name} exists")
            continue
        if r.status == "Merged":
            continue

        if r.status in RELEASED and not paths:
            checks["approved_has_spec_file"].errors.append(f"{r.fid}: {r.status} but no SPEC-{r.fid}-*.md")

        if r.status in RELEASED:
            # the INDEX tag must be the exact tag of the INDEX version
            if not r.version or not r.tag:
                checks["approved_tag_matches_version"].errors.append(
                    f"{r.fid}: {r.status} but INDEX Version/Tag is empty (version={r.version!r}, tag={r.tag!r})")
            else:
                if not r.tag.startswith(f"{prefix}{r.fid}-") or not r.tag.endswith(f"-v{r.version}"):
                    checks["approved_tag_matches_version"].errors.append(
                        f"{r.fid}: tag {r.tag!r} is not '{prefix}{r.fid}-<slug>-v{r.version}'")
                exists = git_ok(repo, "rev-parse", "-q", "--verify", f"refs/tags/{r.tag}^{{commit}}")
                if not exists:
                    checks["tag_exists"].errors.append(f"{r.fid}: tag {r.tag} does not exist in git")
                elif rel is not None:
                    at_tag = _spec_at_tag(repo, r.tag, rel)
                    if at_tag is None:
                        checks["tag_contains_spec_version"].errors.append(
                            f"{r.fid}: {rel.as_posix()} does not exist in the commit tagged {r.tag}")
                    elif not at_tag:
                        checks["tag_contains_spec_version"].warnings.append(
                            f"{r.fid}: the spec at {r.tag} has no §0 Card, so its version cannot be verified (legacy format)")
                    else:
                        tagged = norm_version(at_tag.get("version", ""))
                        if tagged != r.version:
                            checks["tag_contains_spec_version"].errors.append(
                                f"{r.fid}: the spec at {r.tag} says version {tagged or '(none)'}, INDEX says {r.version}")

        # ---- INDEX row vs the spec's own §0 Card
        if paths:
            chk = checks["index_matches_spec_card"]
            if not card:
                chk.warnings.append(f"{r.fid}: {paths[0].name} has no §0 Card table (legacy format)")
            else:
                cs = status_word(card.get("status", ""))
                if not cs:
                    chk.warnings.append(f"{r.fid}: §0 Card has no Status")
                elif cs != r.status and not (r.status == "Stale" and cs in {"Approved", "Stale"}):
                    chk.errors.append(f"{r.fid}: INDEX status {r.status!r} but spec §0 Status {cs!r}")
                if r.version:
                    cv = norm_version(card.get("version", ""))
                    if not cv:
                        chk.warnings.append(f"{r.fid}: §0 Card has no Version")
                    elif cv != r.version:
                        chk.errors.append(f"{r.fid}: INDEX version {r.version} but spec §0 Version {cv}")
                if r.tag:
                    ct = norm_tag(card.get("tag", ""))
                    if not ct:
                        chk.warnings.append(f"{r.fid}: §0 Card has no Tag")
                    elif ct != r.tag:
                        chk.errors.append(f"{r.fid}: INDEX tag {r.tag} but spec §0 Tag {ct}")

    # ---- §0 Feature id vs file name
    for fid, paths in files.items():
        card = cards[fid]
        if not card:
            continue  # already reported as legacy under index_matches_spec_card
        actual = card_feature_id(card)
        if actual is None:
            checks["spec_section0_fid_matches"].warnings.append(f"{fid}: §0 Card has no Feature id (legacy)")
        elif actual != fid:
            checks["spec_section0_fid_matches"].errors.append(
                f"{fid}: file name says {fid} but §0 Card Feature is {actual}")

    ordered = [checks[c] for c in CHECK_IDS]
    failed = [c for c in ordered if not c.passed]
    return {
        "schema": SCHEMA,
        "repo": str(repo),
        "spec_dir": spec_dir,
        "tag_prefix": prefix,
        "summary": {
            "rows": len(rows), "spec_files": sum(len(v) for v in files.values()),
            "checks": len(ordered), "failed": len(failed),
            "warnings": sum(len(c.warnings) for c in ordered),
        },
        "checks": [c.to_json() for c in ordered],
    }
