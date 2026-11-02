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

`examples/<id>-good.txt` and `<id>-bad.txt` exist for rows 23, 24 and 26. They are **not** evidence about any model;
`tests/test_evals.py` uses them to prove that the graders accept the right behaviour and reject the wrong one.
