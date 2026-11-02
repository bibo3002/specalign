"""Table-aware, encoding- and line-ending-preserving edits of spec / registry markdown.

Replaces the ad-hoc edit scripts every run used to write. A document is held as LF lines; the original
line ending (LF or CRLF) and a UTF-8 BOM are restored on save. Writes are atomic (temp file + replace).

Operations (all idempotent):
  append_row   add a row to a table unless an identical row (or the same key) is already there
  patch_row    set cells of the row whose key column equals a value
  set_card     set a `| Field | Value |` row of the §0 Card (adds it when missing)
  replace_block replace the body of a `## §N` block
"""
from __future__ import annotations

import difflib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .common import SpecAlignError, is_separator, split_row

HEADING_RE = re.compile(r"^##\s+§(\d+[A-D]?)\b")


def esc(cell: str) -> str:
    return cell.replace("|", "\\|").replace("\n", " ").strip()


def fmt_row(cells: list[str]) -> str:
    return "| " + " | ".join(esc(c) for c in cells) + " |"


def fmt_like(template: str, cells: list[str]) -> str:
    """Render `cells` with the column widths of an existing row, so an aligned table stays aligned."""
    raw = re.split(r"(?<!\\)\|", template.strip())
    if len(raw) >= 2 and raw[0] == "":
        raw = raw[1:]
    if raw and raw[-1].strip() == "":
        raw = raw[:-1]
    widths = [len(seg) for seg in raw]
    aligned = any(len(seg) > len(seg.strip()) + 2 for seg in raw)
    if not aligned or len(widths) != len(cells):
        return fmt_row(cells)
    parts = []
    for width, cell in zip(widths, cells):
        text = esc(cell)
        parts.append((" " + text).ljust(max(width, len(text) + 2)) if len(text) + 2 <= width else f" {text} ")
    return "|" + "|".join(parts) + "|"


@dataclass
class Table:
    header_line: int          # index into doc.lines
    header: list[str]         # lower-cased
    rows: list[int]           # line indexes of data rows
    end: int                  # index of the last table line


class Doc:
    def __init__(self, path: Path):
        self.path = Path(path)
        try:
            raw = self.path.read_bytes()
        except OSError as exc:
            raise SpecAlignError(f"cannot read {path}: {exc}") from exc
        self.bom = raw.startswith(b"\xef\xbb\xbf")
        if self.bom:
            raw = raw[3:]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SpecAlignError(f"{path} is not valid UTF-8: {exc}") from exc
        self.eol = "\r\n" if text.count("\r\n") > text.count("\n") / 2 and "\r\n" in text else "\n"
        self.trailing_newline = text.endswith("\n")
        body = text.replace("\r\n", "\n").replace("\r", "\n")
        self.original = body
        self.lines = body.split("\n")
        if self.trailing_newline:
            self.lines.pop()                    # split() leaves a final empty element

    # ---------------------------------------------------------------- structure
    def text(self) -> str:
        return "\n".join(self.lines) + ("\n" if self.trailing_newline else "")

    def changed(self) -> bool:
        return self.text() != self.original

    def block_range(self, code: str | None) -> tuple[int, int]:
        """[start, end) line indexes of a block's body; the whole document when `code` is None."""
        if code is None:
            return 0, len(self.lines)
        start = None
        for i, line in enumerate(self.lines):
            m = HEADING_RE.match(line)
            if m and start is None and m.group(1) == code:
                start = i + 1
            elif start is not None and re.match(r"^##\s", line):
                return start, i
        if start is None:
            raise SpecAlignError(f"{self.path.name}: block §{code} not found")
        return start, len(self.lines)

    def tables(self, code: str | None = None) -> list[Table]:
        lo, hi = self.block_range(code)
        out: list[Table] = []
        i, fenced = lo, False
        while i < hi:
            line = self.lines[i]
            if line.strip().startswith("```"):
                fenced = not fenced
            cells = None if fenced else split_row(line)
            if cells is not None and i + 1 < hi:
                sep = split_row(self.lines[i + 1])
                if sep is not None and is_separator(sep):
                    rows, j = [], i + 2
                    while j < hi and split_row(self.lines[j]) is not None:
                        rows.append(j)
                        j += 1
                    out.append(Table(i, [c.lower() for c in cells], rows, j - 1))
                    i = j
                    continue
            i += 1
        return out

    def pick_table(self, code: str | None, index: int = 0, with_column: str | None = None) -> Table:
        tabs = self.tables(code)
        if with_column:
            tabs = [t for t in tabs if any(with_column.lower() in h for h in t.header)]
        if not tabs or index >= len(tabs):
            where = f"§{code}" if code else "the document"
            raise SpecAlignError(f"{self.path.name}: no table #{index} in {where}")
        return tabs[index]

    @staticmethod
    def column(table: Table, name: str) -> int:
        low = name.lower()
        for i, h in enumerate(table.header):
            if h == low:
                return i
        for i, h in enumerate(table.header):
            if low in h:
                return i
        raise SpecAlignError(f"no column {name!r} (columns: {', '.join(table.header)})")

    def cells_at(self, line_index: int) -> list[str]:
        return split_row(self.lines[line_index]) or []

    # ---------------------------------------------------------------- operations
    def append_row(self, cells: list[str], code: str | None = None, table: int = 0,
                   key: str | None = None, with_column: str | None = None) -> str:
        """Returns 'added', 'unchanged' (identical row present) or 'updated' (same key, different cells)."""
        t = self.pick_table(code, table, with_column)
        if len(cells) > len(t.header):
            raise SpecAlignError(f"row has {len(cells)} cells, table has {len(t.header)} columns")
        cells = cells + [""] * (len(t.header) - len(cells))
        template = self.lines[t.rows[-1]] if t.rows else None
        new = fmt_like(template, cells) if template else fmt_row(cells)
        kc = self.column(t, key) if key else None
        for ln in t.rows:
            existing = self.cells_at(ln)
            if [esc(c) for c in existing] == [esc(c) for c in cells]:
                return "unchanged"
            if kc is not None and kc < len(existing) and existing[kc] == cells[kc].strip():
                self.lines[ln] = new
                return "updated"
        at = (t.rows[-1] if t.rows else t.header_line + 1) + 1
        self.lines.insert(at, new)
        return "added"

    def patch_row(self, match_column: str, match_value: str, sets: dict[str, str], code: str | None = None,
                  table: int = 0, with_column: str | None = None) -> str:
        t = self.pick_table(code, table, with_column)
        mc = self.column(t, match_column)
        hits = [ln for ln in t.rows if mc < len(self.cells_at(ln)) and self.cells_at(ln)[mc] == match_value.strip()]
        if not hits:
            raise SpecAlignError(f"{self.path.name}: no row with {match_column} = {match_value!r}")
        if len(hits) > 1:
            raise SpecAlignError(f"{self.path.name}: {len(hits)} rows match {match_column} = {match_value!r}")
        ln = hits[0]
        cells = self.cells_at(ln)
        cells += [""] * (len(t.header) - len(cells))
        before = list(cells)
        for col, value in sets.items():
            cells[self.column(t, col)] = value
        if [esc(c) for c in cells] == [esc(c) for c in before]:
            return "unchanged"
        self.lines[ln] = fmt_like(self.lines[ln], cells)
        return "updated"

    def set_card(self, field: str, value: str) -> str:
        t = self.pick_table("0", 0)
        fc = 0
        for ln in t.rows:
            cells = self.cells_at(ln)
            if cells and cells[fc].lower() == field.lower():
                if len(cells) > 1 and cells[1] == value.strip():
                    return "unchanged"
                self.lines[ln] = fmt_row([cells[0], value])
                return "updated"
        self.lines.insert(t.end + 1, fmt_row([field, value]))
        return "added"

    def replace_block(self, code: str, body: list[str]) -> str:
        lo, hi = self.block_range(code)
        new = [""] + [b.rstrip() for b in body] + [""]
        old = self.lines[lo:hi]
        # keep one blank line before the next heading
        if [l.rstrip() for l in old] == new or [l.rstrip() for l in old] == new[:-1]:
            return "unchanged"
        self.lines[lo:hi] = new
        return "updated"

    # ---------------------------------------------------------------- output
    def diff(self) -> str:
        return "".join(difflib.unified_diff(
            self.original.splitlines(keepends=True), self.text().splitlines(keepends=True),
            fromfile=f"a/{self.path.name}", tofile=f"b/{self.path.name}"))

    def save(self) -> bool:
        if not self.changed():
            return False
        data = self.text().replace("\n", self.eol).encode("utf-8")
        if self.bom:
            data = b"\xef\xbb\xbf" + data
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".docedit-", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            os.replace(tmp, self.path)
        except OSError as exc:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise SpecAlignError(f"cannot write {self.path}: {exc}") from exc
        self.original = self.text()
        return True
