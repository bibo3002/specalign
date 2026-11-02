"""Run manifest and resumable run state.

One JSON record per run (`<SPEC_DIR>/runs/<date>-<F>-<mode>.json`, schema `specalign.run/1`) holds what the prose
of §13B/§13D only claims: approvals (filled statement + the user's reply verbatim + UTC time), dispositions,
files written (sha256), migrations, tests, cleanup counts, commits and tags. `.specalign/run-state.json` points at
the active record, so a compacted or new session continues at the right stage (`manifest show`).

The tool cannot prove that a reply was really typed by the user — it makes the claim explicit, timestamped,
append-only and checkable by a second reader (`manifest verify`, `finalize tag|push`).
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .common import SpecAlignError, require_repo

SCHEMA = "specalign.run/1"
STATE_SCHEMA = "specalign.run-state/1"
STATE_PATH = Path(".specalign") / "run-state.json"

STAGES = [
    "preflight", "scope-tier", "inventory", "read", "checkpoint", "remediation", "verification", "draft",
    "socratic", "cross-section", "self-check", "write-gate", "finalize", "handoff",
]
GATES = {"T1", "R1", "D1", "X1", "W1", "V1", "G1", "P1", "C1", "N1"}
MODES = {"GENESIS", "SYNC", "DRIFT", "RESCAN"}
TIERS = {"Micro", "Standard", "Core"}
RUN_TYPES = {"documentation-only", "remediating"}
DISPOSITIONS = {"Fix", "Accept", "Defer", "Reject"}
COLLECTIONS = {"disposition", "file", "migration", "test", "cleanup", "commit", "tag", "note"}
PLACEHOLDER_RE = re.compile(r"<[^<>\n]{1,60}>")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


# --------------------------------------------------------------------------- persistence

def _load(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecAlignError(f"cannot read run record {path}: {exc}") from exc
    if data.get("schema") != SCHEMA:
        raise SpecAlignError(f"{path}: unexpected schema {data.get('schema')!r}")
    return data


def _save(repo: Path, rel: str, data: dict) -> None:
    data["updated_at"] = utcnow()
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    state = {"schema": STATE_SCHEMA, "run": rel.replace("\\", "/"), "stage": data["stage"], "updated_at": data["updated_at"]}
    sp = repo / STATE_PATH
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n")


def active(repo: Path, run: str | None = None) -> tuple[str, dict]:
    """(relative path, record) of the explicit run or the one in run-state.json."""
    repo = require_repo(repo)
    if run is None:
        sp = repo / STATE_PATH
        if not sp.exists():
            raise SpecAlignError("no active run (no .specalign/run-state.json); start one with `manifest init`")
        run = json.loads(sp.read_text(encoding="utf-8"))["run"]
    return run, _load(repo / run)


# --------------------------------------------------------------------------- operations

def init(repo: Path, spec_dir: str, feature: str, mode: str, tier: str | None = None,
         run_type: str = "documentation-only", skill_version: str = "", date: str | None = None) -> str:
    repo = require_repo(repo)
    mode = mode.upper()
    if mode not in MODES:
        raise SpecAlignError(f"mode must be one of {sorted(MODES)}")
    if tier and tier not in TIERS:
        raise SpecAlignError(f"tier must be one of {sorted(TIERS)}")
    if run_type not in RUN_TYPES:
        raise SpecAlignError(f"run type must be one of {sorted(RUN_TYPES)}")
    if not re.fullmatch(r"F\d+", feature):
        raise SpecAlignError("feature must look like F12")
    day = date or utcnow()[:10]
    rel = f"{spec_dir.strip('/')}/runs/{day}-{feature}-{mode.lower()}.json"
    if (repo / rel).exists():
        raise SpecAlignError(f"{rel} already exists (resume it, or pass another --date)")
    data = {
        "schema": SCHEMA, "run_id": Path(rel).stem, "feature": feature, "mode": mode, "tier": tier,
        "run_type": run_type, "skill_version": skill_version, "stage": 0, "created_at": utcnow(),
        "approvals": [], "dispositions": [], "files": [], "migrations": [], "tests": [], "cleanup": [],
        "commits": [], "tags": [], "notes": [], "overrides": [],
    }
    _save(repo, rel, data)
    return rel


def approve(repo: Path, gate: str, statement: str, reply: str, run: str | None = None) -> dict:
    gate = gate.upper()
    if gate not in GATES:
        raise SpecAlignError(f"unknown gate {gate!r}; forms: {', '.join(sorted(GATES))}")
    if not statement.strip() or not reply.strip():
        raise SpecAlignError("both the filled statement and the user's verbatim reply are required")
    if PLACEHOLDER_RE.search(statement):
        raise SpecAlignError(f"statement still contains a placeholder: {PLACEHOLDER_RE.search(statement).group(0)!r}")
    rel, data = active(repo, run)
    rec = {"gate": gate, "statement": statement.strip(), "reply": reply, "at": utcnow()}
    data["approvals"].append(rec)
    _save(Path(repo).resolve(), rel, data)
    return rec


def has_approval(data: dict, gates: set[str], containing: list[str] | None = None) -> bool:
    """True when an approval of one of `gates` exists whose statement mentions every string in `containing`."""
    for a in data["approvals"]:
        if a["gate"] in gates and all(c in a["statement"] for c in (containing or [])):
            return True
    return False


def in_r1_scope(data: dict, path: str) -> bool:
    """True when an R1 statement names the file, or a directory (`dir/`) above it."""
    path = path.replace("\\", "/")
    parents = [path.rsplit("/", i)[0] + "/" for i in range(1, path.count("/") + 1)]
    for a in data["approvals"]:
        if a["gate"] == "R1" and (path in a["statement"] or any(p in a["statement"] for p in parents)):
            return True
    return False


def required_for(data: dict, stage: int) -> list[str]:
    """Gate requirements that must be recorded before entering `stage`."""
    need: list[str] = []
    if stage >= 2 and not has_approval(data, {"T1"}):
        need.append("T1 (tier decision)")
    if stage >= 5 and data["run_type"] == "remediating" and not has_approval(data, {"R1"}):
        need.append("R1 (remediation authorization)")
    if stage >= 6:
        for m in data["migrations"]:
            if not has_approval(data, {"D1"}, [m.get("file", "")]):
                need.append(f"D1 for {m.get('file')}")
    if stage >= 12 and not has_approval(data, {"W1", "C1"}):
        need.append("W1 or C1 (write gate)")
    return need


def set_stage(repo: Path, stage: int, run: str | None = None, force: str | None = None) -> dict:
    if not 0 <= stage < len(STAGES):
        raise SpecAlignError(f"stage must be 0–{len(STAGES) - 1}")
    rel, data = active(repo, run)
    if stage > data["stage"] + 1 and not force:
        raise SpecAlignError(f"cannot jump from stage {data['stage']} to {stage}; stages run in order (--force REASON)")
    missing = required_for(data, stage)
    if missing and stage > data["stage"]:
        if not force:
            raise SpecAlignError(f"stage {stage} ({STAGES[stage]}) needs recorded approvals first: {'; '.join(missing)}")
        data["overrides"].append({"stage": stage, "missing": missing, "reason": force, "at": utcnow()})
    data["stage"] = stage
    _save(Path(repo).resolve(), rel, data)
    return data


def add(repo: Path, kind: str, payload: dict, run: str | None = None) -> dict:
    if kind not in COLLECTIONS:
        raise SpecAlignError(f"kind must be one of {sorted(COLLECTIONS)}")
    repo_p = require_repo(repo)
    rel, data = active(repo_p, run)
    payload = dict(payload)
    if kind == "disposition":
        if payload.get("disposition") not in DISPOSITIONS or not re.fullmatch(r"DF-\d+", str(payload.get("id", ""))):
            raise SpecAlignError("disposition needs id (DF-n) and disposition in Fix/Accept/Defer/Reject")
        data["dispositions"] = [d for d in data["dispositions"] if d["id"] != payload["id"]] + [payload]
    elif kind == "file":
        p = repo_p / payload.get("path", "")
        if not p.is_file():
            raise SpecAlignError(f"file not found: {payload.get('path')}")
        if payload.get("scope") == "remediation" and not in_r1_scope(data, payload["path"]):
            raise SpecAlignError(f"{payload['path']} is not in the R1 file list; a remediating run may change only the "
                                 "files it listed — ask for an R1 amendment first")
        payload["sha256"] = sha256_of(p)
        data["files"] = [f for f in data["files"] if f["path"] != payload["path"]] + [payload]
    elif kind == "migration":
        if not payload.get("file"):
            raise SpecAlignError("migration needs file (and should carry pre_check, rollback, verification, applied_at)")
        if payload.get("applied_at") and not has_approval(data, {"D1"}, [payload["file"]]):
            raise SpecAlignError(f"no D1 approval naming {payload['file']} is recorded; DDL needs its own confirmation")
        data["migrations"] = [m for m in data["migrations"] if m["file"] != payload["file"]] + [payload]
    elif kind == "tag":
        data["tags"].append(payload)
    else:
        key = {"test": "tests", "cleanup": "cleanup", "commit": "commits", "note": "notes"}[kind]
        data[key].append(payload)
    _save(repo_p, rel, data)
    return data


def verify(repo: Path, run: str | None = None) -> dict:
    repo_p = require_repo(repo)
    rel, data = active(repo_p, run)
    problems: list[str] = []
    notes: list[str] = []
    for f in data["files"]:
        p = repo_p / f["path"]
        if not p.is_file():
            problems.append(f"recorded file is missing: {f['path']}")
        elif sha256_of(p) != f["sha256"]:
            notes.append(f"{f['path']} changed after it was recorded (re-add it if the change is intended)")
    for a in data["approvals"]:
        if PLACEHOLDER_RE.search(a["statement"]):
            problems.append(f"{a['gate']} approval at {a['at']} has an unfilled statement")
    for m in data["migrations"]:
        if m.get("applied_at"):
            for key in ("pre_check", "rollback", "verification"):
                if not m.get(key):
                    problems.append(f"migration {m['file']} was applied without {key}")
            if not has_approval(data, {"D1"}, [m["file"]]):
                problems.append(f"migration {m['file']} was applied without a D1 approval")
    for t in data["tags"]:
        if not has_approval(data, {"G1", "C1"}, [t.get("name", "")]):
            problems.append(f"tag {t.get('name')} has no G1/C1 approval naming it")
    for o in data["overrides"]:
        notes.append(f"stage {o['stage']} entered with missing gates ({'; '.join(o['missing'])}): {o['reason']}")
    missing = required_for(data, data["stage"])
    if missing:
        problems.append(f"stage {data['stage']} reached without: {'; '.join(missing)}")
    return {"run": rel, "stage": data["stage"], "problems": problems, "notes": notes, "ok": not problems}


def show(repo: Path, run: str | None = None) -> dict:
    rel, data = active(repo, run)
    nxt = min(data["stage"] + 1, len(STAGES) - 1)
    return {
        "run": rel, "feature": data["feature"], "mode": data["mode"], "tier": data["tier"], "run_type": data["run_type"],
        "stage": data["stage"], "stage_name": STAGES[data["stage"]], "next_stage": nxt, "next_stage_name": STAGES[nxt],
        "blocked_by": required_for(data, nxt), "approvals": [f"{a['gate']} @ {a['at']}" for a in data["approvals"]],
        "dispositions": {d["id"]: d["disposition"] for d in data["dispositions"]},
        "open_files": [f["path"] for f in data["files"]], "tags": [t.get("name") for t in data["tags"]],
    }
