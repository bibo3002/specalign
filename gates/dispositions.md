# Deviation flags and dispositions

## Deviation Flags (DF)

Every finding of the reading stages becomes `DF-n` (numbered once, never renumbered). Each DF has:
**severity** (blocker / high / medium / low), **claim** (what is wrong, with a citation — Rule 4), **evidence**,
**recommended disposition**.

## Disposition vocabulary

| Disposition | Meaning | Spec status after the run | Required |
|---|---|---|---|
| **Fix** | Change code/tests/DB in this run | `Resolved` | the fix, a test or an explicit "untestable because…", an AC, an evidence id |
| **Accept** | Real, tolerated for now | `Accepted` | reason, owner, what would reopen it |
| **Defer** | Real, to be fixed later | `Deferred` | trigger or date, where it is tracked |
| **Reject** | Not a defect after investigation | `Rejected` | the evidence that disproves it |

Every DF ends the run in exactly one terminal status. `Open` is not terminal — an Approved spec with an Open DF is
a registry error.

## The checkpoint message (stage 4)

The agent lists every DF with its recommended disposition **and** the files each Fix would touch:

```
| DF | Sev | Claim | Disposition | Files in scope | Test |
|----|-----|-------|-------------|----------------|------|
| DF-1 | high | … | Fix | server/routes/x.ts, tests/api/x.test.ts | contract |
| DF-9 | low | … | Defer (trigger: second tenant) | — | — |
Live DDL needed: migration 011 (separate D1 confirmation)
```

The user answers with the table edited, or "accept your recommendations". That reply, quoted verbatim, is the
**R1 authorization** (see `approval-statements.md`).

## "Fix all" and other shorthand

Shorthand is accepted only as a pointer to the table the agent just showed:

- "fix all" = every DF **marked Fix in the table**, no more. DFs the agent recommended Accept/Defer/Reject stay so
  unless the user changes them.
- If the user's words disagree with the table, the agent restates the resulting table and waits.
- A DF whose fix needs files outside the list, or live DDL, goes back to the user (R1 amendment / D1).

## Traceability

`DF → AC → evidence id` is mandatory for every `Resolved` DF: the spec's acceptance criterion states the corrected
behaviour and cites the evidence (see `evidence.md`). A DF with no AC is not Resolved.
