# Approval statements (v2)

A gate closes only on a recorded approval. This file is the complete list of statement forms.

## How a gate closes

1. The agent shows the **filled** statement (all `<…>` replaced) in its message, together with whatever it summarises
   (file list, diff, table, SQL).
2. The user replies. The gate closes when the reply **approves that message unchanged** — a bare yes, "approved",
   "accept your recommendations", or the statement itself. Any qualification ("yes but…", a changed list, a different
   version) is a **new instruction**: update the statement, show it again.
3. The agent records, in the run manifest (and §13D of the spec): statement id, filled text, the user's reply
   **verbatim**, and the UTC time. The agent never reconstructs a reply from memory.
4. A reply to an *earlier* message never closes a later gate. Approval in one context does not carry to another
   (a write approval is not a tag approval; one feature's approval is not another's).

A combined reply such as "approve the write, tags and push" is valid only if the message it answers contained the
filled **W1, G1 and P1** statements (use the combined form C1).

## Forms

| Id | Gate | Filled statement |
|---|---|---|
| T1 | Tier (stage 1) | «I classify this run as `<Micro\|Standard\|Core>` per the agent's recommendation; discussion, citation discipline and final approval remain mandatory.» |
| R1 | Remediation (stage 4) | «I authorize a **remediating** run for `<F-id>`: dispositions as in the table above, code/test/DB changes limited to `<file list>`. Anything else needs a new confirmation.» |
| D1 | Live DDL (stage 5) | «I approve applying `<migration file>` to `<database>`: pre-check `<query → result>`, rollback `<script>`, verification `<query>`.» — one statement per migration, see `ddl-protocol.md`. |
| X1 | Deletion of data or files | «I approve deleting `<what>` using exactly `<scoped statement>` (expected `<n>` rows, matched by `<prefix / owner / time window>`).» |
| W1 | Write gate (stage 11) | «I approve writing/editing `<files>` for `<FEATURE>` v`<X.Y.Z>`, including the finalization commit.» |
| V1 | Major version | «I approve a **major** bump of `<F-id>` to v`<X.0.0>` because `<contract break>`.» |
| G1 | Tags | «I approve creating the tag(s) `<tag 1>`, `<tag 2>` …» — list every tag, including those for ripple patches. |
| P1 | Push | «I approve pushing `<branch>` and the tag(s) above to `<remote>`.» |
| C1 | Combined W1 + G1 + P1 | «I approve the write (W1), the tag(s) (G1) and the push (P1) exactly as listed above.» |
| N1 | Rescan with no changes | «I confirm the rescan was a no-op: no INDEX changes, no drift flips.» |

For a rescan that edits `INDEX.md`, use W1 with the file list `docs/specs/INDEX.md` after showing the exact `git diff`.

## Rules

- **Never** tag, push, delete data, apply DDL or force-push without the matching form.
- Quote the user's words exactly; do not paraphrase them into a stronger approval.
- Forms are fixed text. A project may add forms in its binding but may not weaken these.
- `specalign finalize tag|push` (when available) refuses to run without a recorded G1/P1/C1 in the manifest.
