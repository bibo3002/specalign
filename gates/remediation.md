# Run types and remediation

SpecAlign is **backward-looking**: a spec documents what exists and audits what changed. It does not govern
forward development (spec-first plans, implementation approval dashboards belong elsewhere). But an audit that
finds defects needs a lawful way to fix them in the same run, because the spec must describe the *corrected*
behaviour. That is a **remediating run**.

| Run type | When | May write |
|---|---|---|
| **documentation-only** | no Fix dispositions, or user wants findings only | only the draft spec file inside `SPEC_DIR` before the write gate |
| **remediating** | the user authorized R1 at the checkpoint | the files listed in R1 (code, tests, migrations) **in addition**, as they are fixed |

Declare the run type in the manifest at stage 4. A run never changes type silently.

## Rules for a remediating run

1. **Scope is the R1 file list.** Touching a file outside it needs an amended R1. Unrelated cleanups are DFs of a
   later run, not extras.
2. **Order:** Fix → test for that Fix → next Fix. A Fix with no test is allowed only with a written reason (§13B).
3. **Live DDL is separate** — see `ddl-protocol.md`; R1 never authorizes it.
4. **No outward actions:** no tag, push, deploy, or data deletion without G1/P1/X1.
5. **Everything lands in one commit** with the spec (spec and code that it describes ship together), unless the
   user asks otherwise. The commit is covered by the write gate (W1); verify the staged-file count first.
6. **Stop and ask** if a fix turns out to need a design decision, a contract change (see `versioning.md`), or
   files outside scope. Do not "fix forward".
7. **Run the whole test suite** after the last Fix; record the command and counts. A red suite blocks the draft.
8. Behavioural (browser) verification happens **after** the fixes, never before.

## What stays read-only

Until the write gate: no registry edit, no project-map edit, no tag. Rule 1 of the SKILL (read-only until
authorized) is satisfied because R1 *is* the authorization for the listed files.
