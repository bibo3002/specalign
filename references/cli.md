# CLI quick reference

Run from the skill's `tools/` directory, or with `PYTHONPATH=<skill>/tools` from the project root. `.` is the
repository root. Every example below is parsed by the real argument parser in `tests/test_skill_docs.py`, so it cannot
drift from the tool. Arabic or quoted text goes into a **file** (`--reply-file`, `--cells-file`, `--statement-file`,
`--json-file`, `--body-file`), not into a shell string.

There is no `docedit set-row`, no `--note` flag and no `manifest add <repo> <F-id>`: a DF's status is changed with
`docedit patch-row`, a note is `manifest add . note --json '{"text": "…"}'`.

```
python -m specalign --version
python -m specalign preflight . --path src/pages --path server/routes
python -m specalign registry check .
python -m specalign registry check . --json --strict
python -m specalign drift . F2 F6 --own-only
python -m specalign drift . --exit-zero --json
python -m specalign lint . F6
python -m specalign lint . --baseline docs/specs/lint-baseline.json --no-warnings
python -m specalign lint . --write-baseline docs/specs/lint-baseline.json
python -m specalign lint . --file docs/specs/SPEC-F6-basic-data.md
python -m specalign inventory . F6 --tables-file tables.json
python -m specalign schema fingerprint --input rows.json
python -m specalign schema snapshot . F6 --input rows.json
python -m specalign schema check . F6 --input rows.json
```

## Editing specs and the registry (`docedit FILE` comes after the operation name)

```
python -m specalign docedit append-row docs/specs/SPEC-F6-basic-data.md --section 13C --cells-file row.json
python -m specalign docedit append-row docs/specs/SPEC-F6-basic-data.md --section 13B --cell V-9 --cell 2026-11-02 --cell "tests" --cell unit --cell pass --key ID
python -m specalign docedit patch-row docs/specs/SPEC-F6-basic-data.md --section 13A --match ID=DF-3 --set "Status=Accepted(owner, reason, reopen trigger)"
python -m specalign docedit patch-row docs/specs/INDEX.md --match ID=F6 --set "Last verified=2026-11-02" --set Status=Approved
python -m specalign docedit set-card docs/specs/SPEC-F6-basic-data.md --field Status --value Approved
python -m specalign docedit replace-block docs/specs/SPEC-F6-basic-data.md --section 14 --body-file body.md --dry-run
```
`--cells-file` is a JSON list of cell strings. `--key COLUMN` replaces an existing row with the same key instead of
adding one. Every operation is idempotent; `--dry-run` prints the diff and writes nothing.

## Run record (`manifest <op> <repo> …`; the repository comes first, then the gate or kind)

```
python -m specalign manifest init . F6 --mode SYNC --tier Core --run-type remediating --skill-version 1.0.0
python -m specalign manifest stage . 1
python -m specalign manifest stage . 5 --force "reason the gate is skipped, recorded as an override"
python -m specalign manifest approve . T1 --statement-file statement.txt --reply-file reply.txt
python -m specalign manifest add . disposition --json-file disposition.json
python -m specalign manifest add . file --json-file file.json
python -m specalign manifest add . migration --json-file migration.json
python -m specalign manifest add . test --json-file tests.json
python -m specalign manifest add . cleanup --json-file cleanup.json
python -m specalign manifest add . note --json-file note.json
python -m specalign manifest show .
python -m specalign manifest verify .
```
Payload shapes: disposition `{"id": "DF-3", "disposition": "Fix|Accept|Defer|Reject", "files": [...]}`; file
`{"path": "server/routes/files.ts", "scope": "remediation"}` (scope only for files changed under R1); migration
`{"file": "server/migrations/012_x.sql", "pre_check": "…", "rollback": "…", "verification": "…", "applied_at": "UTC"}`;
test `{"command": "npm test", "passed": 120, "failed": 0}`; cleanup `{"query": "select count(*) …", "count": 0}`;
note `{"text": "…"}`. Gates: T1 R1 D1 X1 W1 V1 G1 P1 C1 N1.

## Finalization (`finalize <op> <repo> <plan.json>`)

```
python -m specalign finalize plan . plan.json
python -m specalign finalize apply . plan.json
python -m specalign finalize staged . plan.json
python -m specalign finalize tag . plan.json --commit HEAD
python -m specalign finalize push . plan.json --remote origin
python -m specalign finalize push . plan.json --remote origin --execute
```

## Skill repository only

```
python -m specalign eval --transcripts evals/runs/2026-11-02
python -m specalign eval --only 23 --require-all
```
