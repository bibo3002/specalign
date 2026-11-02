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

from pathlib import Path

from . import drift as drift_mod
from . import docedit as docedit_mod
from . import evals as evals_mod
from . import finalize as finalize_mod
from . import inventory as inventory_mod
from . import lint as lint_mod
from . import manifest as manifest_mod
from . import preflight as preflight_mod
from . import schema as schema_mod
from . import registry as registry_mod
from .common import SpecAlignError, read_text


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
    if args.own_only:
        if any(f.get("drift_class") == "own" for f in payload["features"]) and not args.exit_zero:
            return 1
    elif "drifted" in statuses and not args.exit_zero:
        return 1
    if args.strict and "unverifiable" in statuses:
        return 3
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    payload = lint_mod.run_lint(args.repo, args.spec_dir, args.tag_prefix, args.features or None,
                                [Path(f) for f in args.file] or None)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(lint_mod.human_report(payload, show_warnings=not args.no_warnings))
    s = payload["summary"]
    return 1 if s["errors"] or (args.strict and s["warnings"]) else 0


def _kv(items: list[str], what: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for it in items:
        if "=" not in it:
            raise SpecAlignError(f"{what} expects COLUMN=VALUE, got {it!r}")
        k, v = it.split("=", 1)
        out[k.strip()] = v
    return out


def cmd_docedit(args: argparse.Namespace) -> int:
    doc = docedit_mod.Doc(Path(args.file))
    if args.op == "append-row":
        cells = list(args.cell)
        if args.cells_file:
            cells = json.loads(Path(args.cells_file).read_text(encoding="utf-8"))
        result = doc.append_row(cells, args.section, args.table, args.key, args.with_column)
    elif args.op == "patch-row":
        match = _kv([args.match], "--match")
        (mcol, mval), = match.items()
        result = doc.patch_row(mcol, mval, _kv(args.set, "--set"), args.section, args.table, args.with_column)
    elif args.op == "set-card":
        result = doc.set_card(args.field, args.value)
    else:  # replace-block
        body = read_text(Path(args.body_file)).split("\n")
        result = doc.replace_block(args.section, body)
    if args.dry_run:
        print(doc.diff() or "(no change)")
    elif doc.save():
        pass
    print(f"{Path(args.file).name}: {result}" + (" (dry run, nothing written)" if args.dry_run and doc.changed() else ""))
    return 0


def _text_arg(inline: str | None, file: str | None, what: str) -> str:
    if file:
        return read_text(Path(file)).rstrip("\n")
    if inline is None:
        raise SpecAlignError(f"{what} is required (inline or --{what.split()[0]}-file)")
    return inline


def cmd_manifest(args: argparse.Namespace) -> int:
    repo = args.repo
    if args.op == "init":
        rel = manifest_mod.init(repo, args.spec_dir, args.feature.upper(), args.mode, args.tier, args.run_type,
                                args.skill_version, args.date)
        print(f"created {rel}")
        return 0
    if args.op == "stage":
        data = manifest_mod.set_stage(repo, args.number, args.run, args.force)
        print(f"stage {data['stage']} ({manifest_mod.STAGES[data['stage']]})")
        return 0
    if args.op == "approve":
        rec = manifest_mod.approve(repo, args.gate, _text_arg(args.statement, args.statement_file, "statement"),
                                   _text_arg(args.reply, args.reply_file, "reply"), args.run)
        print(f"recorded {rec['gate']} at {rec['at']}")
        return 0
    if args.op == "add":
        raw = _text_arg(args.json, args.json_file, "json payload")
        manifest_mod.add(repo, args.kind, json.loads(raw), args.run)
        print(f"added {args.kind}")
        return 0
    if args.op == "show":
        info = manifest_mod.show(repo, args.run)
        if args.json:
            print(json.dumps(info, indent=2, ensure_ascii=False))
        else:
            print(f"{info['feature']} {info['mode']} ({info['tier'] or 'tier not set'}, {info['run_type']}) — {info['run']}")
            print(f"stage {info['stage']} {info['stage_name']}  →  next {info['next_stage']} {info['next_stage_name']}")
            print("blocked by: " + ("; ".join(info["blocked_by"]) or "nothing"))
            print("approvals: " + (", ".join(info["approvals"]) or "none"))
            print("dispositions: " + (", ".join(f"{k}={v}" for k, v in info["dispositions"].items()) or "none"))
        return 0
    res = manifest_mod.verify(repo, args.run)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        for n in res["notes"]:
            print(f"  note  {n}")
        for p in res["problems"]:
            print(f"  ERROR {p}")
        print("manifest OK" if res["ok"] else "manifest has problems")
    return 0 if res["ok"] else 1


def cmd_preflight(args: argparse.Namespace) -> int:
    payload = preflight_mod.run_preflight(args.repo, args.spec_dir, args.path)
    print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else preflight_mod.human_report(payload))
    return 0 if payload["ok"] else 1


def cmd_finalize(args: argparse.Namespace) -> int:
    plan = Path(args.plan)
    if args.op in {"plan", "apply"}:
        if args.op == "plan":
            rep = finalize_mod.plan_report(args.repo, plan, args.spec_dir, args.tag_prefix)
        else:
            rep = finalize_mod.apply_plan(args.repo, plan, args.spec_dir, args.tag_prefix, args.run)
        public = {k: v for k, v in rep.items() if not k.startswith("_")}
        if args.json:
            print(json.dumps(public, indent=2, ensure_ascii=False))
        else:
            for rel, d in rep["diffs"].items():
                print(d.rstrip() or f"(no change in {rel})")
            for n in rep["notes"]:
                print(f"  note  {n}")
            for pr in rep["problems"]:
                print(f"  ERROR {pr}")
            for b in rep.get("registry_blocking", []):
                print(f"  ERROR registry {b['check']}: {'; '.join(b['errors'][:3])}")
            for t in rep.get("registry_tag_checks_pending", []):
                print(f"  note  registry check {t} will pass once the tag exists")
            verb = "would change" if args.op == "plan" else "changed"
            print()
            print(f"{verb} {len(rep['changed'])} file(s): {', '.join(rep['changed']) or 'none'}")
        return 0 if rep["ok"] else 1
    if args.op == "staged":
        res = finalize_mod.staged_check(args.repo, plan)
        print(json.dumps(res, indent=2) if args.json else
              (f"staged {len(res['staged'])} file(s) = plan" if res["ok"] else
               f"STAGED MISMATCH — extra: {res['extra'] or '-'}; missing: {res['missing'] or '-'}"))
        return 0 if res["ok"] else 1
    if args.op == "tag":
        for t in finalize_mod.create_tags(args.repo, plan, args.commit, args.run):
            print(f"created tag {t}")
        return 0
    cmd = finalize_mod.push_command(args.repo, plan, args.remote, args.branch, args.run)
    print(" ".join(cmd))
    if args.execute:
        return finalize_mod.run_push(args.repo, cmd)
    print("(not executed; add --execute to run it)")
    return 0


def cmd_inventory(args: argparse.Namespace) -> int:
    payload = inventory_mod.run_inventory(args.repo, args.spec_dir, [f.upper() for f in args.features] or None,
                                          Path(args.tables_file) if args.tables_file else None)
    print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else inventory_mod.human_report(payload))
    return 1 if args.strict and (payload["summary"]["undocumented"] or payload["summary"]["missing_in_code"]) else 0


def cmd_schema(args: argparse.Namespace) -> int:
    rows = schema_mod.load_rows(Path(args.input))
    if args.op == "fingerprint":
        print(schema_mod.describe(rows))
        return 0
    if args.op == "snapshot":
        print(f"wrote {schema_mod.snapshot(args.repo, args.spec_dir, args.feature, rows)}")
        print(schema_mod.describe(rows))
        return 0
    res = schema_mod.check(args.repo, args.spec_dir, args.feature, rows)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif res["status"] == "unrecorded":
        print(f"{res['feature']}: the spec records no schema fingerprint; current is {res['current']}")
    elif res["status"] == "match":
        print(f"{res['feature']}: schema matches {res['recorded']}")
    else:
        print(f"{res['feature']}: SCHEMA CHANGED — recorded {res['recorded']}, current {res['current']}")
        for kind, items in (res["changes"] or {}).items():
            for it in items:
                print(f"    {kind}: {it}")
        if res["changes"] is None:
            print("    (no snapshot stored; run `schema snapshot` at the next finalization to get a diff)")
    return {"match": 0, "mismatch": 1, "unrecorded": 3}[res["status"]]


def cmd_eval(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else Path(__file__).resolve().parents[2]
    results = evals_mod.run(root, Path(args.transcripts) if args.transcripts else None, args.only or None)
    if args.json:
        print(json.dumps([r.__dict__ for r in results], indent=2, ensure_ascii=False))
    else:
        print(evals_mod.human_report(results))
    failed = any(r.status == "fail" for r in results)
    missing = args.require_all and any(r.status == "not-exercised" for r in results)
    return 1 if failed or missing else 0


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
    dr.add_argument("--own-only", action="store_true", help="fail only on a feature's own drift, not ripple from shared files")
    dr.add_argument("--strict", action="store_true", help="exit 3 when a feature is unverifiable")
    dr.set_defaults(func=cmd_drift)

    li = sub.add_parser("lint", help="structure, IDs and traceability of spec files")
    common(li)
    li.add_argument("features", nargs="*", help="optional F-ids (default: every spec)")
    li.add_argument("--file", action="append", default=[], help="lint this spec file directly (repeatable)")
    li.add_argument("--no-warnings", action="store_true", help="hide warnings in the human report")
    li.add_argument("--strict", action="store_true", help="warnings also fail the run")
    li.set_defaults(func=cmd_lint)

    de = sub.add_parser("docedit", help="table-aware edits of spec / registry markdown (encoding and EOL preserved)")
    de_sub = de.add_subparsers(dest="op", required=True)

    def edit_common(sp: argparse.ArgumentParser, section: bool = True) -> None:
        sp.add_argument("file")
        sp.add_argument("--dry-run", action="store_true", help="print the diff, write nothing")
        if section:
            sp.add_argument("--section", default=None, help="block code such as 13C (default: whole file)")
            sp.add_argument("--table", type=int, default=0, help="table number inside the scope (default 0)")
            sp.add_argument("--with-column", default=None, help="pick the first table that has this column")
        sp.set_defaults(func=cmd_docedit)

    ar = de_sub.add_parser("append-row", help="append a row unless it is already there")
    edit_common(ar)
    ar.add_argument("--cell", action="append", default=[], help="one cell (repeat per column)")
    ar.add_argument("--cells-file", default=None, help="JSON list of cells (avoids shell quoting)")
    ar.add_argument("--key", default=None, help="column that identifies the row; a row with the same key is replaced")
    pr = de_sub.add_parser("patch-row", help="set cells of the row matched by a key column")
    edit_common(pr)
    pr.add_argument("--match", required=True, help="COLUMN=VALUE selecting exactly one row")
    pr.add_argument("--set", action="append", default=[], required=True, help="COLUMN=VALUE to set (repeatable)")
    sc = de_sub.add_parser("set-card", help="set a §0 Card field")
    edit_common(sc, section=False)
    sc.add_argument("--field", required=True)
    sc.add_argument("--value", required=True)
    rb = de_sub.add_parser("replace-block", help="replace the body of a block")
    edit_common(rb)
    rb.add_argument("--body-file", required=True)

    mf = sub.add_parser("manifest", help="run record and resumable run state")
    mf_sub = mf.add_subparsers(dest="op", required=True)

    def mcommon(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("repo")
        sp.add_argument("--run", default=None, help="run record path relative to the repo (default: active run)")
        sp.set_defaults(func=cmd_manifest)

    mi = mf_sub.add_parser("init", help="start a run record")
    mi.add_argument("repo")
    mi.add_argument("feature")
    mi.add_argument("--mode", required=True, choices=["GENESIS", "SYNC", "DRIFT", "RESCAN", "genesis", "sync", "drift", "rescan"])
    mi.add_argument("--tier", default=None, choices=["Micro", "Standard", "Core"])
    mi.add_argument("--run-type", default="documentation-only", choices=["documentation-only", "remediating"])
    mi.add_argument("--skill-version", default="")
    mi.add_argument("--date", default=None, help="UTC date for the file name (default today)")
    mi.add_argument("--spec-dir", default="docs/specs")
    mi.set_defaults(func=cmd_manifest)
    ms = mf_sub.add_parser("stage", help="advance to a stage (checks recorded approvals)")
    mcommon(ms)
    ms.add_argument("number", type=int)
    ms.add_argument("--force", default=None, metavar="REASON", help="enter anyway; the override and reason are recorded")
    ma = mf_sub.add_parser("approve", help="record an approval: filled statement + the user's verbatim reply")
    mcommon(ma)
    ma.add_argument("gate", help="T1 R1 D1 X1 W1 V1 G1 P1 C1 N1")
    ma.add_argument("--statement", default=None)
    ma.add_argument("--statement-file", default=None)
    ma.add_argument("--reply", default=None)
    ma.add_argument("--reply-file", default=None, help="file holding the reply verbatim (avoids shell quoting)")
    mad = mf_sub.add_parser("add", help="append a disposition / file / migration / test / cleanup / commit / tag / note")
    mcommon(mad)
    mad.add_argument("kind", choices=sorted(manifest_mod.COLLECTIONS))
    mad.add_argument("--json", default=None, help="payload as a JSON object")
    mad.add_argument("--json-file", default=None)
    msh = mf_sub.add_parser("show", help="where the run is and what blocks the next stage")
    mcommon(msh)
    msh.add_argument("--json", action="store_true")
    mv = mf_sub.add_parser("verify", help="integrity of the record (hashes, approvals, DDL, tags)")
    mcommon(mv)
    mv.add_argument("--json", action="store_true")

    pf = sub.add_parser("preflight", help="stage 0: binding, repository state, tag namespace, encodings")
    common(pf)
    pf.add_argument("--path", action="append", default=[], help="extra code path that must have no tracked changes (repeatable)")
    pf.set_defaults(func=cmd_preflight)

    fz = sub.add_parser("finalize", help="plan-driven finalization (dry-run first); gated tag and push")
    fz_sub = fz.add_subparsers(dest="op", required=True)

    def fcommon(sp: argparse.ArgumentParser) -> None:
        common(sp)
        sp.add_argument("plan", help="finalize plan JSON (schema specalign.finalize-plan/1)")
        sp.add_argument("--run", default=None)
        sp.set_defaults(func=cmd_finalize)

    for name, hp in (("plan", "show the exact diff and lint result; write nothing"),
                     ("apply", "write the edits (needs W1/C1 in the run manifest)"),
                     ("staged", "staged files must equal the plan's expect_files"),
                     ("tag", "create the planned tags (needs G1/C1 naming each)"),
                     ("push", "print / run the push (needs P1/C1)")):
        sp = fz_sub.add_parser(name, help=hp)
        fcommon(sp)
        if name == "tag":
            sp.add_argument("--commit", default="HEAD")
        if name == "push":
            sp.add_argument("--remote", required=True)
            sp.add_argument("--branch", default=None)
            sp.add_argument("--execute", action="store_true", help="actually run git push")

    iv = sub.add_parser("inventory", help="endpoints (and tables) in code vs what the spec says; advisory")
    common(iv)
    iv.add_argument("features", nargs="*")
    iv.add_argument("--tables-file", default=None, help="JSON array of real table names (from the DB adapter)")
    iv.add_argument("--strict", action="store_true", help="exit 1 when something in code is undocumented")
    iv.set_defaults(func=cmd_inventory)

    sc = sub.add_parser("schema", help="fingerprint of the database objects a spec depends on")
    sc_sub = sc.add_subparsers(dest="op", required=True)
    sf = sc_sub.add_parser("fingerprint", help="hash introspection rows")
    sf.add_argument("--input", required=True, help="JSON rows from the adapter's introspection query")
    sf.set_defaults(func=cmd_schema)
    for name, hp in (("snapshot", "store the rows under <SPEC_DIR>/schema/<F>.json"),
                     ("check", "compare with the spec's recorded fingerprint")):
        sp = sc_sub.add_parser(name, help=hp)
        common(sp)
        sp.add_argument("feature")
        sp.add_argument("--input", required=True)
        sp.set_defaults(func=cmd_schema)

    ev = sub.add_parser("eval", help="run the executable evals of the validation matrix (skill repository)")
    ev.add_argument("--root", default=None, help="skill repository root (default: this checkout)")
    ev.add_argument("--transcripts", default=None, help="directory of recorded agent transcripts <id>.txt")
    ev.add_argument("--only", type=int, action="append", help="run only this scenario id (repeatable)")
    ev.add_argument("--require-all", action="store_true", help="a scenario without evidence also fails the run")
    ev.add_argument("--json", action="store_true")
    ev.set_defaults(func=cmd_eval)
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
