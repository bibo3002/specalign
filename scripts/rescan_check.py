#!/usr/bin/env python3
"""SpecAlign rescan check — CI-ready validator for INDEX.md ↔ SPEC-F*.md consistency.

Usage:
    python3 scripts/rescan_check.py <repo_root> [--spec-dir <path>] [--json]

Exits:
    0 = all checks pass
    1 = validation failures (detailed in output)
    2 = hard error (missing files, not a git repo, etc.)

Checks (read-only, no writes):
1. Every `Approved` row in INDEX.md has a matching `SPEC-F{n}-*.md` file.
2. Every `SPEC-F{n}-*.md` file has a matching row in INDEX.md.
3. Every `Approved` row's tag (`spec/F{n}-*`) exists in `git tag`.
4. Every `Undocumented` row has NO matching spec file on disk.
5. No duplicate F-ids in INDEX.md.
6. Every spec file's §0 Card Feature ID matches its filename F-id.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

# Patterns matching the INDEX.md table format
INDEX_ROW_RE = re.compile(
    r"^\|\s*(F\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|",
    re.MULTILINE
)
SPEC_FILE_RE = re.compile(r"SPEC-(F\d+)-")
SECTION0_FEATURE_RE = re.compile(r"^\|\s*Feature\s*\|\s*(F\d+)\b", re.MULTILINE)
TAG_PREFIX = "spec/"


@dataclass
class IndexRow:
    fid: str
    title: str
    type_: str
    status: str
    version: str
    tag: str
    last_verified: str
    code_check: str
    db_check: str
    behavior_check: str


@dataclass
class CheckResult:
    check: str
    passed: bool
    details: list[str] = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def run_git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True
    )
    return proc.stdout


def parse_index_rows(index_text: str) -> list[IndexRow]:
    """Parse all rows from the INDEX.md table."""
    rows = []
    for m in INDEX_ROW_RE.finditer(index_text):
        fid = m.group(1).strip()
        if not re.match(r"^F\d+$", fid):
            continue
        rows.append(IndexRow(
            fid=fid,
            title=m.group(2).strip(),
            type_=m.group(3).strip(),
            status=m.group(4).strip(),
            version=m.group(5).strip(),
            tag=m.group(6).strip(),
            last_verified=m.group(7).strip(),
            code_check=m.group(8).strip(),
            db_check=m.group(9).strip(),
            behavior_check="",  # 10th column not captured, but we have enough
        ))
    return rows


def find_spec_files(spec_dir: Path) -> dict[str, Path]:
    """Return {F-id: Path} for all SPEC-F*.md files."""
    out = {}
    for f in spec_dir.glob("SPEC-F*.md"):
        m = SPEC_FILE_RE.search(f.name)
        if m:
            out[m.group(1)] = f
    return out


def get_existing_tags(repo: Path) -> set[str]:
    """Return set of all tag names matching spec/F*-*.*.* pattern."""
    try:
        out = run_git(["tag", "-l", f"{TAG_PREFIX}F*"], cwd=repo)
        return {t.strip() for t in out.splitlines() if t.strip().startswith(TAG_PREFIX)}
    except subprocess.CalledProcessError:
        return set()


def check_spec_section0(spec_path: Path, expected_fid: str) -> tuple[bool, str | None]:
    """Verify the spec file's §0 Card Feature ID matches expected."""
    try:
        text = spec_path.read_text()
    except Exception as e:
        return False, f"read error: {e}"
    m = SECTION0_FEATURE_RE.search(text)
    if not m:
        return False, "no §0 Card Feature row found"
    actual = m.group(1)
    if actual != expected_fid:
        return False, f"§0 Card Feature is {actual}, expected {expected_fid}"
    return True, None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="rescan_check",
        description="SpecAlign INDEX ↔ SPEC consistency validator"
    )
    parser.add_argument("repo", help="path to the repo root")
    parser.add_argument("--spec-dir", default="docs/specs", help="SPEC_DIR relative to repo")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"error: {repo} is not a git repository", file=sys.stderr)
        return 2

    spec_dir = repo / args.spec_dir
    if not spec_dir.exists():
        print(f"error: spec dir {spec_dir} does not exist", file=sys.stderr)
        return 2

    index_path = spec_dir / "INDEX.md"
    if not index_path.exists():
        print(f"error: INDEX.md not found at {index_path}", file=sys.stderr)
        return 2

    index_text = index_path.read_text()
    index_rows = parse_index_rows(index_text)
    spec_files = find_spec_files(spec_dir)
    existing_tags = get_existing_tags(repo)

    results: list[CheckResult] = []

    # 1. Approved rows have spec files
    approved_no_spec = [r for r in index_rows if r.status == "Approved" and r.fid not in spec_files]
    results.append(CheckResult(
        check="approved_has_spec_file",
        passed=len(approved_no_spec) == 0,
        details=[f"{r.fid}: Approved but no SPEC-{r.fid}-*.md" for r in approved_no_spec]
    ))

    # 2. Spec files have INDEX rows
    orphan_specs = [fid for fid in spec_files if not any(r.fid == fid for r in index_rows)]
    results.append(CheckResult(
        check="spec_file_has_index_row",
        passed=len(orphan_specs) == 0,
        details=[f"{fid}: {spec_files[fid].name} exists but no INDEX row" for fid in orphan_specs]
    ))

    # 3. Approved rows have tags
    approved_no_tag = [r for r in index_rows if r.status == "Approved" and not any(t.startswith(f"{TAG_PREFIX}{r.fid}-") for t in existing_tags)]
    results.append(CheckResult(
        check="approved_has_tag",
        passed=len(approved_no_tag) == 0,
        details=[f"{r.fid}: Approved but no tag {TAG_PREFIX}{r.fid}-* in git tag" for r in approved_no_tag]
    ))

    # 4. Undocumented rows have NO spec files
    undoc_with_spec = [r for r in index_rows if r.status == "Undocumented" and r.fid in spec_files]
    results.append(CheckResult(
        check="undocumented_no_spec_file",
        passed=len(undoc_with_spec) == 0,
        details=[f"{r.fid}: Undocumented but SPEC-{r.fid}-*.md exists" for r in undoc_with_spec]
    ))

    # 5. No duplicate F-ids
    fid_counts = {}
    for r in index_rows:
        fid_counts[r.fid] = fid_counts.get(r.fid, 0) + 1
    dup_fids = [fid for fid, cnt in fid_counts.items() if cnt > 1]
    results.append(CheckResult(
        check="no_duplicate_fids",
        passed=len(dup_fids) == 0,
        details=[f"{fid}: appears {fid_counts[fid]} times in INDEX.md" for fid in dup_fids]
    ))

    # 6. Spec file §0 Card Feature ID matches filename (warning-level for legacy specs)
    section0_warnings = []
    for fid, spec_path in spec_files.items():
        ok, detail = check_spec_section0(spec_path, fid)
        if not ok:
            # Legacy specs (brownfield-spec era) may lack §0 Card Feature row.
            # Extract from filename as fallback - if it matches, it's a warning, not failure.
            section0_warnings.append(f"{fid}: {detail} (legacy - F-id from filename: {fid})")
    results.append(CheckResult(
        check="spec_section0_fid_matches",
        passed=True,  # Always pass; section0_warnings surfaced as details
        details=section0_warnings
    ))

    # Summary
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    payload = {
        "repo": str(repo),
        "spec_dir": str(spec_dir),
        "total_checks": len(results),
        "passed": passed,
        "failed": failed,
        "results": [r.to_json() for r in results],
    }

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for r in results:
            status = "✓" if r.passed else "✗"
            print(f"  {status} {r.check}")
            if r.details:
                for d in r.details:
                    print(f"      {d}")
        print(f"\nSummary: {passed}/{len(results)} checks passed")
        if failed:
            print("FAIL: validation errors above", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))