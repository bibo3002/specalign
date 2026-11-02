"""Executable evals for the skill's validation matrix (references/verification-playbook.md §5).

`python -m specalign eval [--transcripts DIR] [--require-all]` reads `evals/scenarios.json`.

Two kinds of scenario:
  tool        the guard is mechanical; the scenario names the unit tests that prove it and the runner executes them
  transcript  the guard is the agent's behaviour; a recorded agent transcript (`DIR/<id>.txt`: the agent's messages and
              the commands it ran) is graded by rules:
                must      regexes that must match somewhere
                must_not  regexes that must not match anywhere
                order     [first, then] pairs: if `then` matches, `first` must match earlier
              Without a transcript the scenario is reported `not exercised` — never assumed passed.

The shipped good/bad example transcripts (evals/examples) prove that the graders discriminate; they are not evidence
about any model's behaviour.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .common import SpecAlignError

SCHEMA = "specalign.evals/1"


@dataclass
class Result:
    id: int
    title: str
    kind: str
    status: str            # pass | fail | not-exercised
    detail: str = ""


def load_scenarios(root: Path) -> list[dict]:
    path = Path(root) / "evals" / "scenarios.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecAlignError(f"cannot read {path}: {exc}") from exc
    if data.get("schema") != SCHEMA:
        raise SpecAlignError(f"{path}: expected schema {SCHEMA}")
    return data["scenarios"]


def grade(scenario: dict, text: str) -> tuple[bool, list[str]]:
    problems: list[str] = []
    for pat in scenario.get("must", []):
        if not re.search(pat, text, re.I | re.M):
            problems.append(f"missing: /{pat}/")
    for pat in scenario.get("must_not", []):
        m = re.search(pat, text, re.I | re.M)
        if m:
            problems.append(f"forbidden: /{pat}/ matched {m.group(0)!r}")
    for first, then in scenario.get("order", []):
        t = re.search(then, text, re.I | re.M)
        if t:
            f = re.search(first, text[: t.start()], re.I | re.M)
            if not f:
                problems.append(f"order: /{then}/ occurs without /{first}/ before it")
    return not problems, problems


def run_tool_scenario(root: Path, scenario: dict) -> Result:
    tests = scenario["tests"]
    proc = subprocess.run([sys.executable, "-m", "unittest", *tests], cwd=str(Path(root) / "tests"),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = proc.returncode == 0
    tail = (proc.stderr or proc.stdout).strip().splitlines()[-3:]
    return Result(scenario["id"], scenario["title"], "tool", "pass" if ok else "fail",
                  f"{len(tests)} test(s)" if ok else " | ".join(tail))


def run(root: Path, transcripts: Path | None = None, only: list[int] | None = None) -> list[Result]:
    results: list[Result] = []
    for sc in load_scenarios(root):
        if only and sc["id"] not in only:
            continue
        if sc["kind"] == "tool":
            results.append(run_tool_scenario(root, sc))
            continue
        guard = run_tool_scenario(root, sc) if sc.get("tests") else None
        if guard is not None and guard.status == "fail":
            results.append(Result(sc["id"], sc["title"], "transcript", "fail", "mechanical guard: " + guard.detail))
            continue
        note = "mechanical guard passes; " if guard is not None else ""
        path = Path(transcripts) / f"{sc['id']}.txt" if transcripts else None
        if not path or not path.exists():
            results.append(Result(sc["id"], sc["title"], "transcript", "not-exercised", note + "no recorded transcript"))
            continue
        ok, problems = grade(sc, path.read_text(encoding="utf-8"))
        results.append(Result(sc["id"], sc["title"], "transcript", "pass" if ok else "fail",
                              "; ".join(problems) if problems else note.rstrip("; ")))
    return results


def human_report(results: list[Result]) -> str:
    marks = {"pass": "✓", "fail": "✗", "not-exercised": "·"}
    lines = [f"  {marks[r.status]} {r.id:>2} {r.kind:<10} {r.title}" + (f"  — {r.detail}" if r.detail else "") for r in results]
    counts = {s: sum(r.status == s for r in results) for s in marks}
    lines.append(f"\n{counts['pass']} passed, {counts['fail']} failed, {counts['not-exercised']} not exercised")
    return "\n".join(lines)
