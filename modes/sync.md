# Mode SYNC — bring an existing spec back in line with reality

SYNC audits a spec against the **current** code, database and runtime, closes every gap, and re-baselines.
It runs the same stages as GENESIS with stage 2 starting from the spec and with the additions below.

## 1. Classify the drift first (stage 0 / 2)

`python -m specalign drift <repo> <F-id>` lists commits since the registered tag. Classify each:

| Class | What it is | What SYNC does |
|---|---|---|
| **code** | source in `Sources` changed behaviour | re-read, update the affected claims, new evidence |
| **ripple** | a shared file changed for *another* feature | check only the claims that file backs; PATCH if unaffected; record "no behavioural change" |
| **db** | schema/constraint/trigger changed | re-introspect (3b), update §5/§6, refresh the fingerprint |
| **docs-only** | spec text was wrong or stale, code unchanged | correct the text, PATCH |
| **evidence** | claim was `code-verified-only` / `historical-log` and can now be exercised | upgrade the label with fresh evidence, PATCH |
| **dead source** | pattern in `Sources` matches no file | fix the `Sources` line; record the rename/removal |

A drift listing is the **starting point, not the verdict**: no commit and no drift can still hide DB or dependency
changes, so stage 3 reads the code regardless.

## 2. Legacy normalization

A spec written under an older template is normalised **at its next SYNC**: add the missing blocks (§13A–§13D, tier
row, evidence legend, IDs), keep every old claim that still holds, and mark what changed. Normalization alone is a
MINOR bump (`gates/versioning.md`). The registry's legacy note is cleared when the last legacy spec is done.

## 3. Rule 9 in practice — superseded wording

When behaviour changes, do not delete the old text silently:
- §13C row: version, date, `Fixed | Changed | Deprecated | Removed`, what changed, the approval id, and
  **"Superseded wording: …"** quoting the old statement or naming where it was.
- In the body, the new behaviour is stated plainly; the old statement lives in §13C (or a clearly marked
  "superseded" note) so a reader of the old version can map it.

## 4. Fixing behaviour during a SYNC

Findings follow the checkpoint (stage 4) like in any run. The version bump follows `gates/versioning.md`; a contract
change makes it **major** and needs V1 — decide it before remediation starts, not after.

## 5. Ripple patches

Fixing a shared piece in this run changes what other approved specs say. For each affected spec: PATCH bump, §13C row,
§13D row, own tag, updated INDEX row — all listed in the W1/G1 statements (`gates/versioning.md`). Do not leave them
stale "for later".

## 6. After SYNC

`python -m specalign registry check` must pass 9/9; `drift` for the feature must be clean; the registry's
"next recommended pilot" note is refreshed.
