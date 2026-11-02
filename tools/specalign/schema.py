"""Schema fingerprint: a stable hash of the database objects a spec depends on.

Git history cannot show that a column was changed by hand in the live database. The DB adapter's canonical
introspection query (adapters/<db>/introspection.sql) returns rows `kind | tbl | name | detail` for columns,
constraints, indexes and triggers; this module canonicalises them and hashes the result.

    python -m specalign schema fingerprint --input rows.json            print the fingerprint
    python -m specalign schema snapshot REPO F6 --input rows.json       store rows under <SPEC_DIR>/schema/F6.json
    python -m specalign schema check REPO F6 --input rows.json          compare with the spec's §0 `Schema fingerprint`
                                                                         (and, when a snapshot exists, list the changes)

Exit codes of `check`: 0 match · 1 mismatch · 2 error · 3 the spec records no fingerprint (`n/a`).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .common import SpecAlignError, parse_card, read_text, require_repo, spec_files

SCHEMA = "specalign.schema/1"
KEYS = ("kind", "tbl", "name", "detail")
FP_RE = re.compile(r"sha256:([0-9a-f]{16})")


def load_rows(path: Path) -> list[dict]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecAlignError(f"cannot read introspection rows {path}: {exc}") from exc
    if isinstance(data, dict):
        data = data.get("rows", data.get("data"))
    if not isinstance(data, list) or not data:
        raise SpecAlignError("introspection input must be a non-empty JSON array of rows")
    return data


def canonical(rows: list[dict]) -> list[tuple[str, str, str, str]]:
    out = []
    for i, r in enumerate(rows):
        missing = [k for k in KEYS if k not in r]
        if missing:
            raise SpecAlignError(f"row {i} lacks {', '.join(missing)} (expected keys: {', '.join(KEYS)})")
        out.append(tuple(re.sub(r"\s+", " ", str(r[k])).strip() for k in KEYS))
    out.sort()
    if len(set(out)) != len(out):
        raise SpecAlignError("introspection rows contain duplicates; the query must return one row per object")
    return out


def fingerprint(rows: list[dict]) -> str:
    blob = json.dumps(canonical(rows), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()[:16]


def describe(rows: list[dict]) -> str:
    c = canonical(rows)
    tables = sorted({r[1] for r in c})
    return f"{fingerprint(rows)} ({len(c)} objects; tables: {', '.join(tables)})"


def diff(old: list[dict], new: list[dict]) -> dict[str, list[str]]:
    a = {(k, t, n): d for k, t, n, d in canonical(old)}
    b = {(k, t, n): d for k, t, n, d in canonical(new)}
    return {
        "added": sorted(f"{k} {t}.{n}: {b[(k, t, n)]}" for (k, t, n) in b.keys() - a.keys()),
        "removed": sorted(f"{k} {t}.{n}: {a[(k, t, n)]}" for (k, t, n) in a.keys() - b.keys()),
        "changed": sorted(f"{k} {t}.{n}: {a[(k, t, n)]}  →  {b[(k, t, n)]}"
                          for (k, t, n) in a.keys() & b.keys() if a[(k, t, n)] != b[(k, t, n)]),
    }


def _spec_path(repo: Path, spec_dir: str, fid: str) -> Path:
    paths = spec_files(repo / spec_dir).get(fid.upper())
    if not paths:
        raise SpecAlignError(f"no spec file for {fid}")
    return paths[0]


def snapshot_path(repo: Path, spec_dir: str, fid: str) -> Path:
    return repo / spec_dir / "schema" / f"{fid.upper()}.json"


def snapshot(repo: Path, spec_dir: str, fid: str, rows: list[dict]) -> Path:
    repo = require_repo(repo)
    _spec_path(repo, spec_dir, fid)
    dest = snapshot_path(repo, spec_dir, fid)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = [dict(zip(KEYS, r)) for r in canonical(rows)]
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return dest


def check(repo: Path, spec_dir: str, fid: str, rows: list[dict]) -> dict:
    repo = require_repo(repo)
    card = parse_card(read_text(_spec_path(repo, spec_dir, fid)))
    recorded = card.get("schema fingerprint", "")
    m = FP_RE.search(recorded)
    current = fingerprint(rows)
    res = {"feature": fid.upper(), "current": current, "recorded": m.group(0) if m else None, "changes": None}
    if not m:
        res["status"] = "unrecorded"
        return res
    res["status"] = "match" if m.group(0) == current else "mismatch"
    snap = snapshot_path(repo, spec_dir, fid)
    if res["status"] == "mismatch" and snap.exists():
        res["changes"] = diff(json.loads(snap.read_text(encoding="utf-8")), rows)
    return res
