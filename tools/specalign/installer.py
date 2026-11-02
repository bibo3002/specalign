"""Install / sync the skill into `~/.claude/skills/specalign` and `<project>/.opencode/skills/specalign`.

* Copies exactly the skill payload (no tests, no .git, no caches); text files are written with LF.
* Writes INSTALL-MANIFEST.json (version, source commit, sha256 per file).
* `--check` verifies a target against its manifest AND against the source: hand-edited, missing,
  unexpected and out-of-date files are reported.
* An update refuses to overwrite a file that was edited by hand since the last install (use --force).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MANIFEST = "INSTALL-MANIFEST.json"
PAYLOAD = ["SKILL.md", "README.md", "LICENSE", "VERSION", "CHANGELOG.md",
           "stages", "modes", "gates", "templates", "references", "adapters", "scripts", "tools"]
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".txt", ".sql", ".toml", ".cfg", ".ini", ""}


# Files shipped by releases before 1.0 that no longer exist; an install removes them (they would shadow new code).
LEGACY_FILES = ("scripts/test_drift_probe.py",)


def source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def payload_files(root: Path) -> dict[str, bytes]:
    """{posix relative path: bytes as they will be installed}."""
    out: dict[str, bytes] = {}
    for name in PAYLOAD:
        base = root / name
        if base.is_file():
            candidates = [base]
        elif base.is_dir():
            candidates = [p for p in sorted(base.rglob("*")) if p.is_file()]
        else:
            continue
        for p in candidates:
            rel = p.relative_to(root)
            if any(part in SKIP_DIRS for part in rel.parts) or p.suffix in SKIP_SUFFIXES:
                continue
            data = p.read_bytes()
            if p.suffix.lower() in TEXT_SUFFIXES:
                data = data.replace(b"\r\n", b"\n")
            out[rel.as_posix()] = data
    return out


def source_commit(root: Path) -> str | None:
    try:
        proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, check=False)
        return proc.stdout.decode().strip() or None if proc.returncode == 0 else None
    except OSError:
        return None


def read_manifest(target: Path) -> dict | None:
    mf = target / MANIFEST
    if not mf.exists():
        return None
    try:
        return json.loads(mf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def file_hash(path: Path) -> str | None:
    try:
        return sha256(path.read_bytes())
    except OSError:
        return None


def check(target: Path, root: Path) -> dict:
    """Compare a target install with its manifest and with the source."""
    result = {"target": str(target), "installed": False, "version": None, "hand_edited": [], "missing": [],
              "out_of_date": [], "unexpected": [], "ok": False}
    manifest = read_manifest(target)
    if manifest is None:
        return result
    result["installed"], result["version"] = True, manifest.get("version")
    recorded: dict[str, str] = manifest.get("files", {})
    source = {rel: sha256(data) for rel, data in payload_files(root).items()}
    for rel, digest in recorded.items():
        current = file_hash(target / rel)
        if current is None:
            result["missing"].append(rel)
        elif current != digest:
            result["hand_edited"].append(rel)
    for rel, digest in source.items():
        if recorded.get(rel) != digest:
            result["out_of_date"].append(rel)
    for rel in recorded:
        if rel not in source:
            result["out_of_date"].append(rel)
    known = set(recorded) | {MANIFEST}
    for p in sorted(target.rglob("*")):
        if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(target).parts):
            rel = p.relative_to(target).as_posix()
            if rel not in known and p.suffix not in SKIP_SUFFIXES:
                result["unexpected"].append(rel)
    result["ok"] = not (result["hand_edited"] or result["missing"] or result["out_of_date"])
    return result


def install(target: Path, root: Path, force: bool = False, dry_run: bool = False) -> dict:
    files = payload_files(root)
    previous = read_manifest(target)
    old: dict[str, str] = (previous or {}).get("files", {})
    conflicts = [rel for rel, digest in old.items() if (file_hash(target / rel) not in (None, digest))]
    if conflicts and not force:
        return {"target": str(target), "installed": False, "refused": True, "hand_edited": conflicts}
    written, removed = [], []
    for rel, data in files.items():
        dest = target / rel
        if dest.exists() and sha256(dest.read_bytes()) == sha256(data):
            continue
        written.append(rel)
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    for rel in old:
        if rel not in files and (target / rel).exists():
            removed.append(rel)
            if not dry_run:
                (target / rel).unlink()
    for rel in LEGACY_FILES:
        if (target / rel).exists() and rel not in files:
            removed.append(rel)
            if not dry_run:
                (target / rel).unlink()
    if not dry_run:
        version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").exists() else "unknown"
        manifest = {"version": version, "source_commit": source_commit(root),
                    "files": {rel: sha256(data) for rel, data in sorted(files.items())}}
        target.mkdir(parents=True, exist_ok=True)
        (target / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
        for d in sorted((p for p in target.rglob("*") if p.is_dir()), reverse=True):
            if d.name in SKIP_DIRS:
                shutil.rmtree(d, ignore_errors=True)
            elif not any(d.iterdir()):
                d.rmdir()
    return {"target": str(target), "installed": True, "refused": False, "written": written, "removed": removed,
            "dry_run": dry_run}


def targets(home: Path | None, project: Path | None, only_global: bool, only_project: bool) -> list[Path]:
    out: list[Path] = []
    if not only_project:
        base = home if home is not None else Path(os.path.expanduser("~"))
        out.append(base / ".claude" / "skills" / "specalign")
    if project is not None and not only_global:
        out.append(project / ".opencode" / "skills" / "specalign")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="install.py", description="Install or verify the SpecAlign skill")
    ap.add_argument("--project", type=Path, help="adopting project root (also installs .opencode/skills/specalign)")
    ap.add_argument("--home", type=Path, help="home directory (default: the current user's)")
    ap.add_argument("--global-only", action="store_true", help="only ~/.claude/skills/specalign")
    ap.add_argument("--project-only", action="store_true", help="only the project copy")
    ap.add_argument("--check", action="store_true", help="verify instead of installing (exit 1 on any mismatch)")
    ap.add_argument("--force", action="store_true", help="overwrite files that were hand-edited after install")
    ap.add_argument("--dry-run", action="store_true", help="show what would change")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = source_root()
    dirs = targets(args.home, args.project, args.global_only, args.project_only)
    if not dirs:
        print("error: nothing to do (give --project or drop --project-only)", file=sys.stderr)
        return 2
    results, bad = [], False
    for t in dirs:
        if args.check:
            r = check(t, root)
            bad |= not r["ok"]
        else:
            r = install(t, root, force=args.force, dry_run=args.dry_run)
            bad |= bool(r.get("refused"))
        results.append(r)
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            if args.check:
                state = "OK" if r["ok"] else ("NOT INSTALLED" if not r["installed"] else "MISMATCH")
                print(f"{state}  {r['target']}  (version {r['version']})")
                for k in ("hand_edited", "missing", "out_of_date", "unexpected"):
                    for rel in r[k]:
                        print(f"    {k}: {rel}")
            elif r.get("refused"):
                print(f"REFUSED  {r['target']}: hand-edited since the last install (use --force):")
                for rel in r["hand_edited"]:
                    print(f"    {rel}")
            else:
                verb = "would write" if r["dry_run"] else "wrote"
                print(f"{r['target']}: {verb} {len(r['written'])} file(s), removed {len(r['removed'])}")
    return 1 if bad else 0
