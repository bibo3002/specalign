"""Throwaway git repositories laid out like an adopting project (docs/specs + INDEX + binding)."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

INDEX_HEADER = (
    "# Registry\n\n"
    "| ID  | Title | Type | Status | Version | Tag | Last verified | Code | DB | Behavior |\n"
    "|-----|-------|------|--------|---------|-----|---------------|------|----|----------|\n"
)


def card(fid: str, title: str, status: str, version: str, tag: str, sources: str) -> str:
    return (
        f"# SPEC-{fid} — {title}\n\n## §0 Card\n\n| Field | Value |\n|---|---|\n"
        f"| Feature | {fid} — {title} |\n| Status | {status} |\n| Version | v{version} |\n"
        f"| Tag | {tag} |\n| Sources | {sources} |\n\n## §1 Purpose\n\nنص عربي للتجربة.\n"
    )


class Repo:
    def __init__(self, spec_dir: str = "docs/specs", binding: str | None = None):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self.spec_dir = spec_dir
        self._clock = 0
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "T")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.autocrlf", "false")
        (self.path / spec_dir).mkdir(parents=True)
        self.index_rows: list[str] = []
        self.write_index()
        if binding is not None:
            self.write(f"{spec_dir}/binding.md", binding)
        self.write("README.md", "# fixture\n")
        self.commit("baseline")

    # -- plumbing
    def git(self, *args: str, env: dict | None = None) -> str:
        proc = subprocess.run(["git", *args], cwd=self.path, capture_output=True, check=True,
                              env={**os.environ, **(env or {})})
        return proc.stdout.decode("utf-8")

    def write(self, rel: str, text: str, newline: str = "\n") -> None:
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.replace("\n", newline).encode("utf-8"))

    def commit(self, message: str, same_second: bool = False) -> str:
        if not same_second:
            self._clock += 60
        stamp = f"2026-01-01T00:{self._clock // 60:02d}:00Z"
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message, "--allow-empty",
                 env={"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})
        return self.git("rev-parse", "HEAD").strip()

    def tag(self, name: str) -> None:
        self.git("tag", name)

    # -- registry
    def write_index(self) -> None:
        self.write(f"{self.spec_dir}/INDEX.md", INDEX_HEADER + "\n".join(self.index_rows) + "\n")

    def add_feature(self, fid: str, slug: str = "feat", version: str = "1.0.0", status: str = "Approved",
                    sources: str = "src/a.ts", tag: str | None = "auto", index_tag: str | None = "auto",
                    card_version: str | None = None, card_status: str | None = None,
                    newline: str = "\n", make_tag: bool = True, last_verified: str = "2026-01-01") -> str:
        tagname = f"spec/{fid}-{slug}-v{version}" if tag == "auto" else (tag or "—")
        for src in sources.replace("`", "").split(","):
            src = src.strip()
            if src and "/" in src and not any(c in src for c in "{}*()"):
                self.write(src, f"// {src}\n")
        self.write(f"{self.spec_dir}/SPEC-{fid}-{slug}.md",
                   card(fid, slug, card_status or status, card_version or version, tagname, sources), newline)
        self.write_index_row(fid, slug, status, version, tagname if index_tag == "auto" else (index_tag or "—"),
                             last_verified)
        self.commit(f"spec {fid} v{version}")
        if make_tag and tag:
            self.tag(tagname)
        return tagname

    def write_index_row(self, fid: str, slug: str, status: str, version: str, tag: str,
                        last_verified: str = "2026-01-01") -> None:
        self.index_rows = [r for r in self.index_rows if not r.startswith(f"| {fid} ")]
        self.index_rows.append(f"| {fid} | {slug} | Tab | {status} | {version} | {tag} | {last_verified} | ✓ | ✓ | ✓ |")
        self.write_index()

    def cleanup(self) -> None:
        self._tmp.cleanup()
