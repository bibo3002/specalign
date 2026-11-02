# Evals

`scenarios.json` turns the validation matrix (`references/verification-playbook.md` §5, 29 rows) into something that
can fail.

```
python -m specalign eval                            # run from tools/; tool scenarios run, behavioural ones say "not exercised"
python -m specalign eval --transcripts evals/runs/2026-11-02 --require-all
```

## Two kinds of scenario

- **tool** — the guard is mechanical (a command refuses, a check fails). The scenario lists the unit tests that prove
  it; the runner executes them. These are authoritative and run in CI.
- **transcript** — the guard is what the agent does or says (asks for D1, refuses to delete audit rows, restates the
  table after "fix all"). A recorded transcript is graded by regex rules: `must`, `must_not`, and `order` pairs
  (`[first, then]`: if `then` occurs, `first` must occur earlier). Some transcript scenarios also list `tests`: the
  mechanical backstop that holds even when the agent misbehaves; it runs whether or not a transcript exists.

## Recording a transcript

1. Start a fresh agent session with the skill installed and a fixture project (a scratch clone, never production data).
2. Set up the scenario from the matrix row's *Procedure* column and give the agent only the user turns the row
   prescribes.
3. Save the whole exchange — the agent's messages **and** the commands/tool calls it ran — as `<id>.txt` in a dated
   directory (for example `evals/runs/2026-11-02/23.txt`).
4. `python -m specalign eval --transcripts <dir> --only 23` — the row is GREEN when the rules pass. Commit the
   transcript with the dated evidence entry in `studies/`.

Regexes are deliberately loose: they check for the required behaviour and the forbidden action, not exact wording. If a
rule fails on a correct transcript, fix the rule and say why in the commit.

## Examples

`examples/<id>-good.txt` (rows 23, 24, 26) and `<id>-bad.txt` (rows 3, 7, 10, 11, 15, 21, 23, 24, 26, 27) are **not** evidence about any model;
`tests/test_evals.py` uses them to prove that the graders accept the right behaviour and reject the wrong one.

## Recorded runs

`runs/2026-11-02/` holds the first recorded set: one transcript for each of the 17 behavioural rows. **What this is and
is not.** Each transcript is a fresh subagent (the same model family the skill runs on) given the installed skill and a
neutral one-paragraph scenario that does not hint at the expected behaviour. The subagent could only read the skill
directory and had to write its messages and every tool call it *would* make (`TOOL:` lines). So the evidence is
`simulated actions`, one sample per row, single turn: it shows that the skill's text leads the agent to the right
behaviour, not that a long live session never slips. Three rows (4, 10, 15) hit an API safeguard error on the first
attempt and were re-run with reworded scenarios.

**First-pass grading was 19 of 26 graded rows passing; all seven failures were defects of the rules, not of the agent**
(narrow phrases such as requiring the literal gate id `X1`, a `git checkout --` that makes no sense when only a tag is
wrong, and forbidden-command patterns that also matched an explanation of the command). The rules were revised after
seeing the transcripts, which is a weakness: each revised scenario carries a `rule_revision` note, and
`tests/test_evals.py` requires a bad-behaviour example that every revised rule still rejects. A later recording should
be graded by rules fixed beforehand.

**What the transcripts changed in the skill.** Three of fourteen agents invented CLI flags that do not exist
(`docedit set-row`, `--note`, a wrong argument order): `references/cli.md` now lists every command with exact examples
and a test parses each one with the real parser. The row-4 agent asked for a "remediating run" authorization when it had
found nothing to remediate: stage 4 now says a documentation-only run asks for no R1.
