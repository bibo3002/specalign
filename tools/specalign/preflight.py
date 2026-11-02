"""Stage-0 preflight: binding, repository state, tag namespace, encodings, active run.

`python -m specalign preflight <repo> [--path P ...]` — exit 0 ok, 1 findings, 2 error.
DB / UI reachability are agent steps (they need the MCP tools); the agent records their result in the manifest.

Failure codes (the names used by stage 0): BINDING_MISSING · BINDING_INCOMPLETE · DIRTY_TRACKED_FILES · and the
extra INDEX_MISSING · ENCODING · TAG_NAMESPACE.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .common import BINDING_KEY_RE, SpecAlignError, git, parse_index, read_text, require_repo

SCHEMA = "specalign.preflight/1"
REQUIRED = ["PROJECT_MAP", "SPEC_DIR", "REGISTRY", "DB_TOOL", "UI_TOOL", "TAG_PREFIX", "TEST_DATA_PREFIX", "BASELINE_DATE"]
BLOCKS = ["TEST_ACCOUNTS", "CONVENTIONS", "PROJECT_PITFALLS"]
RECOMMENDED = ["TEST_COMMAND", "TYPECHECK_COMMAND", "SKILL_VERSION", "CAPABILITIES"]
PLACEHOLDER_RE = re.compile(r"^<[^<>]*>$|^\{[^{}]*\}$|\b(TODO|TBD)\b")


@dataclass
class Finding:
    code: str
    severity: str        # error | warn | info
    message: str


def binding_entries(text: str) -> dict[str, tuple[str, str]]:
    """KEY → (inline value, indented/continuation body) for top-level binding keys."""
    out: dict[str, tuple[str, str]] = {}
    key = None
    body: list[str] = []

    def flush() -> None:
        if key is not None and key not in out:
            out[key] = (inline, "\n".join(body).strip())

    inline = ""
    for line in text.split("\n"):
        m = BINDING_KEY_RE.match(line)
        if m:
            flush()
            key, inline, body = m.group(1), m.group(2).strip().replace("`", ""), []
        elif key is not None and line.strip() and not line.startswith("#"):
            body.append(line.strip())
    flush()
    return out


def run_preflight(repo: Path, spec_dir: str = "docs/specs", paths: list[str] | None = None) -> dict:
    repo = require_repo(repo)
    f: list[Finding] = []

    def add(code: str, sev: str, msg: str) -> None:
        f.append(Finding(code, sev, msg))

    sd = repo / spec_dir
    binding_path = sd / "binding.md"
    entries: dict[str, tuple[str, str]] = {}
    if not binding_path.exists():
        add("BINDING_MISSING", "error", f"{binding_path.relative_to(repo).as_posix()} not found (offer to create it from templates/binding.template.md)")
    else:
        entries = binding_entries(read_text(binding_path))
        for key in REQUIRED:
            inline = entries.get(key, ("", ""))[0]
            if key not in entries or not inline:
                add("BINDING_INCOMPLETE", "error", f"binding key {key} is missing or empty")
            elif PLACEHOLDER_RE.search(inline):
                add("BINDING_INCOMPLETE", "error", f"binding key {key} still holds a placeholder: {inline!r}")
        for key in BLOCKS:
            inline, body = entries.get(key, ("", ""))
            if key not in entries or not (inline or body):
                add("BINDING_INCOMPLETE", "error", f"binding block {key} is missing or empty")
            elif PLACEHOLDER_RE.search(inline + " " + body.split("\n")[0]):
                add("BINDING_INCOMPLETE", "warn", f"binding block {key} still looks like a template placeholder")
        for key in RECOMMENDED:
            if key not in entries:
                add("BINDING_INCOMPLETE", "warn", f"recommended binding key {key} is absent (see templates/binding.template.md)")
        declared = entries.get("SPEC_DIR", ("", ""))[0]
        if declared and declared.strip("/") != spec_dir.strip("/"):
            add("BINDING_INCOMPLETE", "warn", f"binding SPEC_DIR {declared!r} differs from --spec-dir {spec_dir!r}")

    registry_rel = entries.get("REGISTRY", ("", ""))[0] or f"{spec_dir}/INDEX.md"
    index_path = repo / registry_rel
    if not index_path.exists():
        add("INDEX_MISSING", "error", f"registry {registry_rel} not found")
    elif not parse_index(read_text(index_path)):
        add("INDEX_MISSING", "error", f"registry {registry_rel} has no feature rows (header needs ID and Status columns)")

    # repository state: only TRACKED files under the spec dir (and any --path) block the run
    scope = [spec_dir] + list(paths or [])
    status = git(repo, "status", "--porcelain", "--untracked-files=no", "--", *scope)
    dirty = [ln[3:] for ln in status.split("\n") if ln.strip()]
    if dirty:
        add("DIRTY_TRACKED_FILES", "error", f"{len(dirty)} tracked file(s) modified: {', '.join(dirty[:8])}" + (" …" if len(dirty) > 8 else ""))
    untracked = [ln[3:] for ln in git(repo, "status", "--porcelain", "--", *scope).split("\n") if ln.startswith("??")]
    if untracked:
        add("UNTRACKED_NOTED", "info", f"{len(untracked)} untracked entr(ies) noted and ignored: {', '.join(untracked[:5])}")

    # tag namespace
    prefix = entries.get("TAG_PREFIX", ("", ""))[0] or "spec/"
    tags = [t for t in git(repo, "tag", "--list").split("\n") if t.strip()]
    spec_like = [t for t in tags if re.search(r"(^|/)F\d+-.+-v\d+\.\d+\.\d+$", t)]
    stray = [t for t in spec_like if not t.startswith(prefix)]
    if stray:
        add("TAG_NAMESPACE", "warn", f"spec-looking tags outside TAG_PREFIX {prefix!r}: {', '.join(stray[:5])}")
    foreign = [t for t in tags if t.startswith(prefix) and t not in spec_like]
    if foreign:
        add("TAG_NAMESPACE", "warn", f"tags under {prefix!r} that do not follow F{{n}}-slug-vX.Y.Z: {', '.join(foreign[:5])}")

    # encodings / line endings of the documents the run will edit
    if sd.exists():
        for p in sorted(list(sd.glob("*.md"))):
            raw = p.read_bytes()
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError:
                add("ENCODING", "error", f"{p.name} is not valid UTF-8")
                continue
            crlf, lf = raw.count(b"\r\n"), raw.count(b"\n") - raw.count(b"\r\n")
            if crlf and lf:
                add("ENCODING", "warn", f"{p.name} has mixed line endings ({crlf} CRLF, {lf} LF)")

    # active run
    state = repo / ".specalign" / "run-state.json"
    if state.exists():
        try:
            st = json.loads(state.read_text(encoding="utf-8"))
            add("RUN_ACTIVE", "info", f"active run {st.get('run')} at stage {st.get('stage')} — resume with `manifest show`")
        except (OSError, json.JSONDecodeError):
            add("RUN_ACTIVE", "warn", ".specalign/run-state.json is unreadable")

    errors = sum(x.severity == "error" for x in f)
    return {
        "schema": SCHEMA, "ok": errors == 0,
        "summary": {"errors": errors, "warnings": sum(x.severity == "warn" for x in f), "info": sum(x.severity == "info" for x in f)},
        "findings": [asdict(x) for x in f],
    }


def human_report(payload: dict) -> str:
    lines = []
    for x in payload["findings"]:
        tag = {"error": "ERROR", "warn": "warn ", "info": "info "}[x["severity"]]
        lines.append(f"  {tag} {x['code']}: {x['message']}")
    s = payload["summary"]
    lines.append(("preflight OK" if payload["ok"] else "preflight FAILED") +
                 f" — {s['errors']} error(s), {s['warnings']} warning(s), {s['info']} note(s)")
    return "\n".join(lines)
