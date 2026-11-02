"""Shared helpers: UTF-8 file reading, git access, binding / INDEX / spec-card parsing."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class SpecAlignError(Exception):
    """A hard error (bad repo, unreadable file, git failure). The CLI maps it to exit code 2."""


# --------------------------------------------------------------------------- files

def read_text(path: Path) -> str:
    """Read a text file as UTF-8 (BOM tolerated) and normalise line endings to LF."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise SpecAlignError(f"cannot read {path}: {exc}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SpecAlignError(f"{path} is not valid UTF-8: {exc}") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n")


# --------------------------------------------------------------------------- git

def git(repo: Path, *args: str, check: bool = True) -> str:
    """Run git in `repo` and return stdout decoded as UTF-8 (paths are never quoted)."""
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=false", *args],
            cwd=str(repo), capture_output=True, check=False,
        )
    except OSError as exc:
        raise SpecAlignError(f"cannot run git: {exc}") from exc
    out = proc.stdout.decode("utf-8", errors="replace")
    if check and proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise SpecAlignError(f"git {' '.join(args)} failed: {err}")
    return out


def git_ok(repo: Path, *args: str) -> bool:
    """True when the git command exits 0 (used for existence probes)."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(repo), capture_output=True, check=False,
        )
    except OSError as exc:
        raise SpecAlignError(f"cannot run git: {exc}") from exc
    return proc.returncode == 0


def require_repo(repo: Path) -> Path:
    repo = Path(repo).resolve()
    if not (repo / ".git").exists():
        raise SpecAlignError(f"{repo} is not a git repository")
    return repo


# --------------------------------------------------------------------------- binding

BINDING_KEY_RE = re.compile(r"^([A-Z][A-Z0-9_]*):[ \t]*(.*)$")


def parse_binding(text: str) -> dict[str, str]:
    """Top-level `KEY: value` lines of binding.md (keys are UPPER_SNAKE at column 0)."""
    out: dict[str, str] = {}
    for line in text.split("\n"):
        m = BINDING_KEY_RE.match(line)
        if m and m.group(1) not in out:
            out[m.group(1)] = m.group(2).strip().replace("`", "")
    return out


def load_binding(repo: Path, spec_dir: str) -> dict[str, str]:
    path = Path(repo) / spec_dir / "binding.md"
    return parse_binding(read_text(path)) if path.exists() else {}


# --------------------------------------------------------------------------- tables

def split_row(line: str) -> list[str] | None:
    """Cells of a markdown table row, or None when the line is not a row."""
    s = line.strip()
    if not s.startswith("|"):
        return None
    s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-+:?", c) for c in cells)


# --------------------------------------------------------------------------- versions / tags

VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def norm_version(value: str) -> str:
    """'v1.2.3', '1.2.3 (draft)' → '1.2.3'; '—', '' → ''."""
    m = VERSION_RE.match(value.strip().strip("`").strip())
    return ".".join(m.groups()) if m else ""


def norm_tag(value: str) -> str:
    """First token of a tag cell without backticks; dashes and '' → ''."""
    parts = value.strip().strip("`").split()
    tag = parts[0].strip("`") if parts else ""
    return "" if tag in {"—", "-", "–"} else tag


def status_word(value: str) -> str:
    """'Merged → F6' → 'Merged'; 'Approved' → 'Approved'."""
    parts = value.replace("`", "").split()
    return parts[0] if parts else ""


def tag_version(tag: str) -> tuple[int, int, int] | None:
    m = re.search(r"-v(\d+)\.(\d+)\.(\d+)$", tag)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


# --------------------------------------------------------------------------- INDEX

@dataclass
class IndexRow:
    fid: str
    title: str
    type: str
    status: str          # base word, e.g. "Approved"
    status_raw: str
    version: str         # normalised "1.2.3" or ""
    tag: str             # normalised tag or ""
    last_verified: str
    line: int
    cells: dict[str, str] = field(default_factory=dict)


HEADER_ALIASES = {
    "id": "id", "title": "title", "type": "type", "status": "status", "version": "version",
    "tag": "tag", "last verified": "last_verified", "code": "code", "db": "db", "behavior": "behavior",
}


def parse_index(text: str) -> list[IndexRow]:
    """Parse the registry table by its header names (column order may change)."""
    rows: list[IndexRow] = []
    columns: dict[str, int] | None = None
    for no, line in enumerate(text.split("\n"), start=1):
        cells = split_row(line)
        if cells is None:
            if columns is not None and line.strip() == "":
                columns = None  # blank line ends the table
            continue
        if is_separator(cells):
            continue
        low = [c.lower() for c in cells]
        if columns is None:
            if "id" in low and "status" in low:
                columns = {HEADER_ALIASES[c]: i for i, c in enumerate(low) if c in HEADER_ALIASES}
            continue
        id_col = columns.get("id", 0)
        if id_col >= len(cells) or not re.fullmatch(r"F\d+", cells[id_col]):
            continue

        def cell(name: str) -> str:
            i = columns.get(name) if columns else None
            return cells[i] if i is not None and i < len(cells) else ""

        rows.append(IndexRow(
            fid=cells[id_col], title=cell("title"), type=cell("type"),
            status=status_word(cell("status")), status_raw=cell("status"),
            version=norm_version(cell("version")), tag=norm_tag(cell("tag")),
            last_verified=cell("last_verified"), line=no,
            cells={k: cell(k) for k in columns},
        ))
    return rows


# --------------------------------------------------------------------------- spec §0 card

def parse_card(text: str) -> dict[str, str]:
    """Field → value of the §0 Card table (keys lower-cased). Empty when no card exists."""
    card: dict[str, str] = {}
    in_card = False
    for line in text.split("\n"):
        if re.match(r"^##\s+§0\b", line):
            in_card = True
            continue
        if in_card and re.match(r"^##\s", line):
            break
        if not in_card:
            continue
        cells = split_row(line)
        if cells is None or len(cells) < 2 or is_separator(cells):
            continue
        key = cells[0].lower()
        if key == "field":
            continue
        card.setdefault(key, cells[1])
    return card


def card_feature_id(card: dict[str, str]) -> str | None:
    m = re.match(r"(F\d+)\b", card.get("feature", ""))
    return m.group(1) if m else None


def spec_files(spec_dir: Path) -> dict[str, list[Path]]:
    """F-id → every SPEC-F{n}-*.md file in the directory."""
    out: dict[str, list[Path]] = {}
    for f in sorted(Path(spec_dir).glob("SPEC-F*.md")):
        m = re.match(r"SPEC-(F\d+)-", f.name)
        if m:
            out.setdefault(m.group(1), []).append(f)
    return out
