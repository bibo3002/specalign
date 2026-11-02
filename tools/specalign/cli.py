"""Command line: `python -m specalign <command>` (also tools/specalign.py).

Exit codes (stable contract for CI):
    0  ok / no drift
    1  findings (registry errors, or drift found)
    2  hard error (not a repo, unreadable file, git failure, bad usage)
    3  `drift --strict` only: nothing drifted but some feature is unverifiable
"""
from __future__ import annotations

import argparse
import json
import sys

from . import drift as drift_mod
from . import registry as registry_mod
from .common import SpecAlignError


def _emit_registry(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    for c in payload["checks"]:
        print(f"  {'✓' if c['passed'] else '✗'} {c['check']}")
        for e in c["errors"]:
            print(f"      ERROR {e}")
        for w in c["warnings"]:
            print(f"      warn  {w}")
    s = payload["summary"]
    print(f"\nSummary: {s['checks'] - s['failed']}/{s['checks']} checks passed, {s['warnings']} warning(s) "
          f"[{s['rows']} INDEX rows, {s['spec_files']} spec files, tag prefix {payload['tag_prefix']!r}]")


def cmd_registry(args: argparse.Namespace) -> int:
    payload = registry_mod.run_checks(args.repo, args.spec_dir, args.tag_prefix)
    _emit_registry(payload, args.json)
    failed = payload["summary"]["failed"] > 0
    strict_warn = args.strict and payload["summary"]["warnings"] > 0
    if (failed or strict_warn) and not args.json:
        print("FAIL: registry findings above", file=sys.stderr)
    return 1 if (failed or strict_warn) else 0


def cmd_drift(args: argparse.Namespace) -> int:
    payload = drift_mod.run_drift(args.repo, args.spec_dir, args.tag_prefix, args.features or None)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(drift_mod.human_report(payload))
    statuses = [f["status"] for f in payload["features"]]
    if "drifted" in statuses and not args.exit_zero:
        return 1
    if args.strict and "unverifiable" in statuses:
        return 3
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specalign", description="SpecAlign tooling")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("repo", help="repository root")
        sp.add_argument("--spec-dir", default="docs/specs", help="SPEC_DIR relative to the repo (default docs/specs)")
        sp.add_argument("--tag-prefix", default=None, help="override TAG_PREFIX (default: binding.md, else 'spec/')")
        sp.add_argument("--json", action="store_true", help="machine-readable output")

    reg = sub.add_parser("registry", help="INDEX ↔ spec ↔ tag consistency")
    reg_sub = reg.add_subparsers(dest="registry_command", required=True)
    chk = reg_sub.add_parser("check", help="run all registry checks")
    common(chk)
    chk.add_argument("--strict", action="store_true", help="warnings also fail the run")
    chk.set_defaults(func=cmd_registry)

    dr = sub.add_parser("drift", help="source changes since each spec's release tag")
    common(dr)
    dr.add_argument("features", nargs="*", help="optional F-ids to limit the report (e.g. F2 F6)")
    dr.add_argument("--exit-zero", action="store_true", help="report only; never fail on drift")
    dr.add_argument("--strict", action="store_true", help="exit 3 when a feature is unverifiable")
    dr.set_defaults(func=cmd_drift)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except SpecAlignError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
