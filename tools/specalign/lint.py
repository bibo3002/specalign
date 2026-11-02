"""Spec linter: structure, IDs, terminal states and the DF → AC → evidence chain.

`python -m specalign lint <repo> [F-ids | --file SPEC.md]`

Severity model. A spec made with the v1.0 template (its §0 Card has a `Skill version` row) is checked
strictly: traceability breaks are errors. A legacy spec (no such row) gets the same checks but traceability
breaks are warnings, so the existing corpus can be linted without a flood — it is normalised at its next SYNC.
Rules that protect a *released* spec (Approved) are errors in both formats.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .common import (
    SpecAlignError, card_feature_id, is_separator, norm_version, parse_card, read_text, split_row,
    spec_files,
)
from .drift import parse_sources

SCHEMA = "specalign.lint/1"

BLOCKS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13A", "13B", "13C", "13D", "14"]
STATUSES = {"Draft", "Verifying", "Approved", "Stale"}
DF_TERMINAL = {"Resolved", "Accepted", "Deferred", "Rejected"}
DF_STATES = DF_TERMINAL | {"Open", "Superseded"}
LABELS = {
    "code", "db", "static", "unit", "contract", "runtime", "runtime-js-click", "runtime-synthetic",
    "historical-log", "code-verified-only", "decision",
}
LABEL_ALIASES = {"inject": "contract", "DB": "db", "browser": "runtime", "test": "unit"}
MARKER_RE = re.compile(r"\b(PENDING|TODO|TBD|FIXME)\b")
HEADING_RE = re.compile(r"^##\s+§(\d+[A-D]?)\b")


@dataclass
class Finding:
    rule: str
    severity: str          # error | warn
    line: int
    message: str


# --------------------------------------------------------------------------- parsing helpers

def split_sections(text: str) -> dict[str, tuple[int, list[str]]]:
    """Block code → (1-based line of its heading, its lines without the heading). First heading wins."""
    out: dict[str, tuple[int, list[str]]] = {}
    current: str | None = None
    for no, line in enumerate(text.split("\n"), start=1):
        m = HEADING_RE.match(line)
        if m:
            current = m.group(1)
            if current not in out:
                out[current] = (no, [])
            else:
                current = None            # duplicate heading: reported by L01, content ignored
            continue
        if re.match(r"^##\s", line):
            current = None
            continue
        if current is not None:
            out[current][1].append(line)
    return out


def section_tables(start_line: int, lines: list[str]) -> list[tuple[list[str], list[tuple[int, list[str]]]]]:
    """Tables of a block: (lower-cased header cells, [(line number, row cells)])."""
    tables: list[tuple[list[str], list[tuple[int, list[str]]]]] = []
    header: list[str] | None = None
    rows: list[tuple[int, list[str]]] = []
    fenced = False
    for off, line in enumerate(lines, start=start_line + 1):
        if line.strip().startswith("```"):
            fenced = not fenced
        cells = None if fenced else split_row(line)
        if cells is None:
            if header is not None:
                tables.append((header, rows))
                header, rows = None, []
            continue
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if is_separator(cells):
            continue
        rows.append((off, cells))
    if header is not None:
        tables.append((header, rows))
    return tables


def _col(header: list[str], *names: str) -> int | None:
    for i, h in enumerate(header):
        if any(n in h for n in names):
            return i
    return None


def _strip_code(text: str) -> str:
    """Drop fenced blocks so quoted examples do not trip the marker rule."""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


# --------------------------------------------------------------------------- the linter

def lint_text(text: str, filename: str = "", tag_prefix: str = "spec/") -> list[Finding]:
    out: list[Finding] = []
    card = parse_card(text)
    strict = "skill version" in card
    status = card.get("status", "").replace("`", "").split()[0] if card.get("status") else ""
    released = status == "Approved"

    def add(rule: str, sev: str, line: int, msg: str) -> None:
        out.append(Finding(rule, sev, line, msg))

    def trace(rule: str, line: int, msg: str) -> None:        # traceability: strict only
        add(rule, "error" if strict else "warn", line, msg)

    secs = split_sections(text)

    # L01 blocks ------------------------------------------------------------------------------
    headings = [(no, m.group(1)) for no, ln in enumerate(text.split("\n"), 1) if (m := HEADING_RE.match(ln))]
    seen: dict[str, int] = {}
    for no, code in headings:
        if code in seen:
            add("L01-blocks", "error", no, f"duplicate heading §{code} (first at line {seen[code]})")
        seen.setdefault(code, no)
    for code in BLOCKS:
        if code not in seen:
            add("L01-blocks", "error", 1, f"missing block §{code}")
    order = [c for _, c in headings if c in BLOCKS]
    if order != sorted(order, key=BLOCKS.index):
        add("L01-blocks", "warn", 1, "blocks are not in template order")

    # L02 card --------------------------------------------------------------------------------
    if not card:
        add("L02-card", "error", 1, "§0 Card table not found")
    for key in ("feature", "status", "version", "tag", "sources"):
        if card and not card.get(key):
            add("L02-card", "error", seen.get("0", 1), f"§0 Card lacks '{key}'")
    if card and not card.get("tier"):
        add("L02-card", "warn", seen.get("0", 1), "§0 Card lacks 'tier'")
    if status and status not in STATUSES:
        add("L02-card", "error", seen.get("0", 1), f"unknown status {status!r}")
    ver = norm_version(card.get("version", ""))
    if card.get("version") and not ver:
        add("L02-card", "error", seen.get("0", 1), f"version {card['version']!r} is not vX.Y.Z")
    fid = card_feature_id(card)
    m = re.match(r"SPEC-(F\d+)-", filename)
    if m and fid and m.group(1) != fid:
        add("L02-card", "error", seen.get("0", 1), f"filename says {m.group(1)}, card says {fid}")
    tag_cell = card.get("tag", "").replace("`", "").split()
    tag = tag_cell[0] if tag_cell else ""
    if released and ver:
        want = f"-v{ver}"
        if not tag.endswith(want) or not tag.startswith(tag_prefix):
            add("L02-card", "error", seen.get("0", 1),
                f"released spec: tag {tag!r} must start with {tag_prefix!r} and end with {want!r}")
    if released and card.get("sources") and not parse_sources(card["sources"]).patterns:
        add("L02-card", "error", seen.get("0", 1), "Sources yields no file pattern (drift cannot be checked)")

    # L03/L04 ids, DF states ---------------------------------------------------------------------
    df_rows: dict[str, tuple[int, str]] = {}
    if "13A" in secs:
        start, lines = secs["13A"]
        for header, rows in section_tables(start, lines):
            idc = _col(header, "id")
            stc = _col(header, "status", "disposition")
            if idc is None:
                continue
            for no, cells in rows:
                if idc >= len(cells):
                    continue
                rid = cells[idc]
                if re.fullmatch(r"DF-\d+", rid):
                    if rid in df_rows:
                        add("L03-ids", "error", no, f"duplicate {rid} (first at line {df_rows[rid][0]})")
                    df_rows[rid] = (no, " | ".join(cells))
                    cell = cells[stc] if stc is not None and stc < len(cells) else " | ".join(cells)
                    state = re.search(r"\b(Open|Resolved|Accepted|Deferred|Rejected|Superseded)\b", cell)
                    if not state:
                        add("L04-df-state", "error" if strict else "warn", no, f"{rid} has no recognisable status")
                    elif state.group(1) == "Open":
                        add("L04-df-state", "error" if released else "warn", no,
                            f"{rid} is still Open" + (" on an Approved spec" if released else ""))
                    df_rows[rid] = (no, cell + " " + " | ".join(cells))
    acs: dict[str, tuple[int, list[str], list[str]]] = {}     # id → (line, cells, header)
    if "11" in secs:
        start, lines = secs["11"]
        for header, rows in section_tables(start, lines):
            idc = _col(header, "ac id", "id")
            if idc is None:
                continue
            for no, cells in rows:
                if idc < len(cells) and re.fullmatch(r"AC-[\w.-]+", cells[idc]):
                    if cells[idc] in acs:
                        add("L03-ids", "error", no, f"duplicate {cells[idc]} (first at line {acs[cells[idc]][0]})")
                    acs[cells[idc]] = (no, cells, header)

    # L05 DF → AC ----------------------------------------------------------------------------------
    for did, (no, row) in df_rows.items():
        if re.search(r"\bResolved\b", row):
            cited = re.findall(r"\bAC-[\w.-]+", row)
            if not cited:
                trace("L05-df-ac", no, f"{did} is Resolved but cites no AC")
            for a in cited:
                a = a.rstrip(".-")
                if acs and a not in acs:
                    add("L05-df-ac", "error", no, f"{did} cites {a}, which is not in §11")

    # L06 AC → flow / evidence ----------------------------------------------------------------------
    v_ids = _ids_in(secs.get("13B"), r"V-\d+")
    d_ids = _ids_in(secs.get("13B"), r"D-\d+")
    flow_text = "\n".join(secs["4"][1]) if "4" in secs else ""
    for aid, (no, cells, header) in acs.items():
        fc = _col(header, "flow")
        flow = cells[fc] if fc is not None and fc < len(cells) else ""
        if not flow.strip() or flow.strip() in {"—", "-"}:
            trace("L06-ac-flow", no, f"{aid} names no flow")
        else:
            for f in re.findall(r"F\d+-[\w.]+", flow):
                if flow_text and f not in flow_text:
                    add("L06-ac-flow", "warn", no, f"{aid} cites flow {f}, which is not described in §4")
        ec = _col(header, "evidence")
        if ec is not None and ec < len(cells):
            for v in re.findall(r"\bV-\d+", cells[ec]):
                if v not in v_ids:
                    add("L06-ac-flow", "error", no, f"{aid} cites {v}, which is not in §13B")
        elif strict:
            add("L06-ac-flow", "error", no, f"{aid}: the §11 table has no Evidence column")

    # L07 evidence labels -----------------------------------------------------------------------------
    if "13B" in secs:
        start, lines = secs["13B"]
        for header, rows in section_tables(start, lines):
            idc = _col(header, "id")
            lc = _col(header, "label", "method")
            if idc is None or lc is None:
                continue
            for no, cells in rows:
                if idc >= len(cells) or not re.fullmatch(r"(V|D)-\d+", cells[idc]):
                    continue
                if lc >= len(cells):
                    continue
                words = [w for w in re.findall(r"[A-Za-z][A-Za-z-]*", cells[lc].replace("`", ""))]
                known = [w for w in words if w in LABELS or w in LABEL_ALIASES]
                if not known:
                    add("L07-evidence", "error" if strict else "warn", no,
                        f"{cells[idc]}: no label from the evidence vocabulary in {cells[lc][:40]!r}")
                elif strict and any(w in LABEL_ALIASES for w in known if w not in LABELS):
                    add("L07-evidence", "warn", no, f"{cells[idc]}: legacy alias {known[0]!r} (use the canonical label)")

    # L08 §13D → D-entries ---------------------------------------------------------------------------
    if "13D" in secs:
        start, lines = secs["13D"]
        for header, rows in section_tables(start, lines):
            ec = _col(header, "evidence")
            if ec is None:
                continue
            for no, cells in rows:
                if ec >= len(cells):
                    continue
                ref = cells[ec]
                if re.search(r"SPEC-F\d+", ref):
                    continue                                   # points into another spec
                for d in re.findall(r"\bD-\d+", ref):
                    if d not in d_ids:
                        trace("L08-approval", no, f"§13D cites {d}, which is not in §13B")

    # L09 markers -------------------------------------------------------------------------------------
    for no, line in enumerate(_strip_code(text).split("\n"), start=1):
        if MARKER_RE.search(line):
            add("L09-markers", "error" if released else "warn", no, f"leftover marker {MARKER_RE.search(line).group(1)}")

    # L10 §14 -----------------------------------------------------------------------------------------
    if "14" in secs:
        body = "\n".join(secs["14"][1])
        overall = re.search(r"Overall:\s*\**\s*(PASS|FAIL)", body)
        if released and not overall:
            add("L10-selfcheck", "error", secs["14"][0], "Approved spec has no 'Overall: PASS|FAIL' line in §14")
        if released and overall and overall.group(1) == "FAIL":
            add("L10-selfcheck", "error", secs["14"][0], "Approved spec records Overall: FAIL")
        if released and "✗" in re.sub(r"✓/✗", "", body):
            add("L10-selfcheck", "error", secs["14"][0], "Approved spec has a ✗ row in §14")

    # L11 evolution history ---------------------------------------------------------------------------
    if "13C" in secs and ver:
        versions: list[tuple[int, str]] = []
        start, lines = secs["13C"]
        for header, rows in section_tables(start, lines):
            vc = _col(header, "version")
            if vc is None:
                continue
            for no, cells in rows:
                if vc < len(cells) and norm_version(cells[vc]):
                    versions.append((no, norm_version(cells[vc])))
        if not versions:
            add("L11-history", "error", start, "§13C has no version rows")
        else:
            nums = [v for _, v in versions]
            if ver not in nums:
                add("L11-history", "error" if released else "warn", versions[0][0],
                    f"card version v{ver} has no §13C row (rows: {', '.join('v' + n for n in dict.fromkeys(nums))})")
            top = max(nums, key=lambda v: tuple(int(x) for x in v.split(".")))
            if top != ver:
                add("L11-history", "error" if released else "warn", versions[0][0],
                    f"§13C has a newer version v{top} than the card (v{ver})")
            asc = nums == sorted(nums, key=lambda v: tuple(int(x) for x in v.split(".")))
            desc = nums == sorted(nums, key=lambda v: tuple(int(x) for x in v.split(".")), reverse=True)
            if not (asc or desc):
                add("L11-history", "warn", versions[0][0], "§13C rows are not in version order")
    return out


def _ids_in(sec: tuple[int, list[str]] | None, pattern: str) -> set[str]:
    if not sec:
        return set()
    return set(re.findall(r"(?m)^\|\s*(" + pattern + r")\s*\|", "\n".join(sec[1])))


# --------------------------------------------------------------------------- driver

def lint_file(path: Path, tag_prefix: str = "spec/") -> dict:
    text = read_text(path)
    findings = lint_text(text, Path(path).name, tag_prefix)
    return {
        "file": str(path),
        "format": "v1.0" if "skill version" in parse_card(text) else "legacy",
        "errors": sum(f.severity == "error" for f in findings),
        "warnings": sum(f.severity == "warn" for f in findings),
        "findings": [asdict(f) for f in findings],
    }


def run_lint(repo: Path, spec_dir: str = "docs/specs", tag_prefix: str | None = None,
             features: list[str] | None = None, files: list[Path] | None = None) -> dict:
    from .common import require_repo
    from .registry import resolve_tag_prefix
    if files:
        prefix = tag_prefix or "spec/"
        targets = [Path(f) for f in files]
    else:
        repo = require_repo(repo)
        prefix = resolve_tag_prefix(repo, spec_dir, tag_prefix)
        by_id = spec_files(repo / spec_dir)
        wanted = [f.upper() for f in features] if features else sorted(by_id, key=lambda s: int(s[1:]))
        missing = [f for f in wanted if f not in by_id]
        if missing:
            raise SpecAlignError(f"no spec file for {', '.join(missing)}")
        targets = [p for f in wanted for p in by_id[f]]
    reports = [lint_file(p, prefix) for p in targets]
    return {
        "schema": SCHEMA,
        "summary": {
            "specs": len(reports),
            "errors": sum(r["errors"] for r in reports),
            "warnings": sum(r["warnings"] for r in reports),
        },
        "reports": reports,
    }


def human_report(payload: dict, show_warnings: bool = True) -> str:
    lines: list[str] = []
    for r in payload["reports"]:
        name = Path(r["file"]).name
        lines.append(f"{name} [{r['format']}]: {r['errors']} error(s), {r['warnings']} warning(s)")
        for f in r["findings"]:
            if f["severity"] == "warn" and not show_warnings:
                continue
            lines.append(f"  {'ERROR' if f['severity'] == 'error' else 'warn '} L{f['line']:<4} {f['rule']}: {f['message']}")
    s = payload["summary"]
    lines.append(f"\nSummary: {s['specs']} spec(s), {s['errors']} error(s), {s['warnings']} warning(s)")
    return "\n".join(lines)
