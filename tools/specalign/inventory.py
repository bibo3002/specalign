"""Static inventory: endpoints (and, with a table list, tables) in a spec's source files versus what the spec says.

Git history cannot show a route that was always undocumented, or a documented route that no longer exists. This
reads the feature's `Sources` files and compares:

  * endpoints registered in code        vs  `METHOD /path` cells of the spec's §6
  * tables touched by SQL in code       vs  tables named in the spec's §5 / Sources `tables` label
    (only when a table list is given with --tables-file: a JSON array of real table names from the DB adapter)

The result is advisory (exit 0) unless --strict: a spec may legitimately describe an endpoint it only consumes,
and a shared file may register another feature's route. Every finding names the file and line so the agent can
decide in the SYNC run. Framework patterns are the common ones; extend ENDPOINT_PATTERNS for others.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .common import SpecAlignError, git, read_text, require_repo, spec_files
from .drift import parse_sources, source_matches, sources_line
from .lint import split_sections

SCHEMA = "specalign.inventory/1"
METHODS = "get|post|put|patch|delete"
ENDPOINT_PATTERNS = [
    # Fastify / Express / Koa-router style: app.get('/x'  router.post("/x"
    re.compile(rf"\b(?:app|fastify|server|router|instance|routes?)\.({METHODS})\(\s*['\"`](/[^'\"`]*)['\"`]", re.I),
    # Python decorators: @app.get("/x")  @router.post("/x")  @bp.route("/x", methods=["POST"])
    re.compile(rf"@\w+\.({METHODS})\(\s*['\"](/[^'\"]*)['\"]", re.I),
]
PY_ROUTE = re.compile(r"@\w+\.route\(\s*['\"](/[^'\"]*)['\"](?:[^)]*methods\s*=\s*\[([^\]]*)\])?", re.I)
# `GET /api/x`, and the elided form `POST …/:id/lawyers` (the ellipsis stands for the mount path)
SPEC_ENDPOINT = re.compile(rf"`?\b({METHODS.upper()})\s+(…|\.\.\.)?(/[A-Za-z0-9_\-./:{{}}<>*]*)", re.I)
DYNAMIC_ROUTE = re.compile(rf"\b(?:app|fastify|server|router)\.({METHODS})\(\s*`(/[^`$]*)\$\{{", re.I)
REMOVED_CONTEXT =re.compile(r"removed|no longer|retired|deprecated|~~", re.I)
SQL_TABLE = re.compile(r"\b(?:from|join|into|update)\s+(?:only\s+)?\"?([a-z_][a-z0-9_]*)\"?", re.I)
CODE_SUFFIXES = {".ts", ".js", ".mjs", ".cjs", ".py", ".go", ".rb", ".php", ".java", ".cs", ".kt", ".rs"}


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    elided: bool = field(default=False, compare=False)    # written `…/:id` in a spec: a fragment of a longer route

    def __str__(self) -> str:
        return f"{self.method} {self.path}"


def norm_path(path: str) -> str:
    path = path.split("?")[0].strip().rstrip("/") or "/"
    path = re.sub(r":[A-Za-z_][A-Za-z0-9_]*|\{[^}/]+\}|<[^>/]+>", ":p", path)
    return path


def code_endpoints(text: str) -> list[tuple[Endpoint, int]]:
    out: list[tuple[Endpoint, int]] = []
    for no, line in enumerate(text.split("\n"), start=1):
        for pat in ENDPOINT_PATTERNS:
            for m in pat.finditer(line):
                out.append((Endpoint(m.group(1).upper(), norm_path(m.group(2))), no))
        for m in PY_ROUTE.finditer(line):
            methods = re.findall(r"[A-Za-z]+", m.group(2) or "GET")
            for meth in methods:
                if meth.lower() in METHODS.split("|"):
                    out.append((Endpoint(meth.upper(), norm_path(m.group(1))), no))
    return out


def spec_endpoints(spec_text: str) -> set[Endpoint]:
    secs = split_sections(spec_text)
    body = "\n".join(secs["6"][1]) if "6" in secs else ""
    body = body.replace("\\|", "|")
    out: set[Endpoint] = set()
    for m in SPEC_ENDPOINT.finditer(body):
        line_start = body.rfind("\n", 0, m.start()) + 1
        if REMOVED_CONTEXT.search(body[max(line_start, m.start() - 70):m.start()]):
            continue                      # a mention of a route that no longer exists
        out.add(Endpoint(m.group(1).upper(), norm_path(m.group(3)), elided=bool(m.group(2))))
    return out


def _equivalent(a: Endpoint, b: Endpoint) -> bool:
    """Same method and path; tolerate a mount prefix such as /api on one side."""
    if a.method != b.method:
        return False
    if a.path == b.path:
        return True
    short, long_ = sorted((a.path, b.path), key=len)
    if a.elided or b.elided:
        return long_.endswith(short)
    # a mount prefix of exactly one segment (/api) may differ; deeper suffixes need two segments to be meaningful
    one_mount = long_.count("/") - short.count("/") == 1
    return long_.endswith(short) and (short.count("/") >= 2 or one_mount)


def code_tables(text: str, known: set[str]) -> set[str]:
    return {m.group(1).lower() for m in SQL_TABLE.finditer(text) if m.group(1).lower() in known}


def spec_tables(spec_text: str, known: set[str]) -> set[str]:
    secs = split_sections(spec_text)
    body = "\n".join(secs["5"][1]) if "5" in secs else ""
    words = set(re.findall(r"[a-z_][a-z0-9_]*", body.lower()))
    raw = sources_line(spec_text) or ""
    words |= set(parse_sources(raw).db_objects)
    return {w for w in words if w in known}


def _code_files(tracked: list[str]) -> list[str]:
    return [f for f in tracked if Path(f).suffix in CODE_SUFFIXES and "/tests/" not in f"/{f}"
            and not re.search(r"\.(test|spec)\.", f)]


def run_inventory(repo: Path, spec_dir: str = "docs/specs", features: list[str] | None = None,
                  tables_file: Path | None = None) -> dict:
    """Findings are repo-wide: a route registered in F8's file but documented by F1 is not a gap, and a route a
    spec lists that exists in another file is only consumed there. What remains is truly undocumented
    (`undocumented`) or truly absent from the code (`missing_in_code`)."""
    repo = require_repo(repo)
    known: set[str] | None = None
    if tables_file:
        try:
            known = {str(t).lower() for t in json.loads(Path(tables_file).read_text(encoding="utf-8"))}
        except (OSError, json.JSONDecodeError) as exc:
            raise SpecAlignError(f"cannot read --tables-file: {exc}") from exc
    tracked = [f for f in git(repo, "ls-files").split("\n")
               if f and (repo / f).is_file() and not f.startswith((".opencode/", ".claude/"))]
    code = _code_files(tracked)
    specs = {fid: read_text(paths[0]) for fid, paths in spec_files(repo / spec_dir).items()}
    spec_eps = {fid: spec_endpoints(t) for fid, t in specs.items()}

    where: dict[Endpoint, list[str]] = {}        # every endpoint in the repo's code → "file:line"
    per_file: dict[str, list[tuple[Endpoint, int]]] = {}
    dynamic: dict[str, int] = {}
    dynamic_prefixes: set[tuple[str, str]] = set()   # routes built as `/prefix/${name}`: cannot be listed, only bounded
    file_text: dict[str, str] = {}
    for f in code:
        body = read_text(repo / f)
        file_text[f] = body
        found = [(ep, no) for ep, no in code_endpoints(body) if "$" not in ep.path]
        dyn = DYNAMIC_ROUTE.findall(body)
        if dyn:
            dynamic[f] = len(dyn)
            dynamic_prefixes.update((m.upper(), norm_path(pref)) for m, pref in dyn)
        per_file[f] = found
        for ep, no in found:
            where.setdefault(ep, []).append(f"{f}:{no}")

    def documented_by(ep: Endpoint) -> list[str]:
        return sorted(fid for fid, eps in spec_eps.items() if any(_equivalent(ep, s) for s in eps))

    def exists(ep: Endpoint) -> bool:
        return (any(_equivalent(ep, e) for e in where)
                or any(ep.method == m and ep.path.startswith(pref.rstrip("/") + "/") for m, pref in dynamic_prefixes))

    out = []
    for fid in sorted(specs, key=lambda x: int(x[1:])):
        if features and fid not in features:
            continue
        raw = sources_line(specs[fid])
        pats = parse_sources(raw).patterns if raw else []
        files = [f for f in code if any(source_matches(p, f) for p in pats)]
        mine: dict[Endpoint, list[str]] = {}
        tables_in_code: set[str] = set()
        for f in files:
            for ep, no in per_file.get(f, []):
                mine.setdefault(ep, []).append(f"{f}:{no}")
            if known is not None:
                tables_in_code |= code_tables(file_text[f], known)
        undocumented = sorted(f"{e}  @ {', '.join(w)}" for e, w in mine.items() if not documented_by(e))
        missing = sorted(str(s) for s in spec_eps[fid] if not s.elided and not exists(s))
        entry = {
            "id": fid, "files_scanned": len(files), "endpoints_in_code": len(mine), "endpoints_in_spec": len(spec_eps[fid]),
            "undocumented": undocumented, "missing_in_code": missing,
            "dynamic_routes": {f: n for f, n in dynamic.items() if f in files},
        }
        if known is not None:
            owners = {g for g, t in specs.items() if g != fid}
            elsewhere = set().union(*(spec_tables(specs[g], known) for g in owners)) if owners else set()
            entry["tables_undocumented"] = sorted(tables_in_code - spec_tables(specs[fid], known) - elsewhere)
        out.append(entry)
    return {"schema": SCHEMA, "tables_checked": known is not None, "features": out,
            "summary": {"features": len(out),
                        "undocumented": sum(len(e["undocumented"]) + len(e.get("tables_undocumented", [])) for e in out),
                        "missing_in_code": sum(len(e["missing_in_code"]) for e in out)}}


def human_report(payload: dict) -> str:
    lines = ["Inventory (advisory):"]
    for e in payload["features"]:
        bad = e["undocumented"] or e["missing_in_code"] or e.get("tables_undocumented")
        lines.append(f"\n  {'!' if bad else '✓'} {e['id']}: {e['endpoints_in_code']} endpoint(s) in code, "
                     f"{e['endpoints_in_spec']} in §6 ({e['files_scanned']} file(s) scanned)")
        for x in e["undocumented"]:
            lines.append(f"      registered in code, documented by no spec:  {x}")
        for x in e["missing_in_code"]:
            lines.append(f"      in §6, found in no source file (removed? renamed?):  {x}")
        for x in e.get("tables_undocumented", []):
            lines.append(f"      table used in code, named by no spec:  {x}")
        for f, n in e["dynamic_routes"].items():
            lines.append(f"      note: {n} dynamically built route(s) in {f} cannot be inventoried statically")
    s = payload["summary"]
    lines.append(f"\nSummary: {s['undocumented']} undocumented, {s['missing_in_code']} missing in code"
                 + ("" if payload["tables_checked"] else " (tables not checked: pass --tables-file)"))
    return "\n".join(lines)
