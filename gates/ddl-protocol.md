# Live DDL and data-safety protocol

## When it applies

Any statement that changes schema or data in a database the project uses (migrations, constraint changes, index
drops, cleanup `DELETE`/`UPDATE`). R1 does **not** cover it. Each migration needs its own **D1** confirmation.

## Before applying (shown in the D1 message)

1. **The migration file** (path + full text). It must be idempotent or guarded (`IF EXISTS`, `IF NOT EXISTS`, checks
   that fail loudly) and run in **one transaction**.
2. **Pre-check query and its result** — proves the change is safe on the live data (e.g. no row violates the new
   CHECK, the index to drop really is a duplicate).
3. **Rollback** — the exact script that reverses it, or the statement "irreversible" with the reason.
4. **Verification query** — what you will run afterwards and the expected result.
5. The adapter used (`DB_TOOL`) and the target database.

## After applying

Run the verification query, run it once more to prove idempotence when the migration claims it, record in the
manifest: migration id, pre-check result, applied-at (UTC), verification result, rollback reference.

## Data-safety rules (not negotiable)

- **Audit logs are immutable.** Never delete or edit audit rows by hand. Test suites may remove only the audit rows
  *they created*, identified by test key **and** a time window. Rows left by interactive/browser tests stay.
  An explicit user instruction naming the rows (form X1) is the only exception, and the statement must be scoped.
- **Test data is namespaced.** Create only rows carrying `TEST_DATA_PREFIX`; clean up only by that prefix (plus
  owner / time window where the table allows). A cleanup statement is shown (X1) before it runs, with the expected
  row count; after it runs, a count query proves the result.
- **Never** `DELETE`/`UPDATE` without a `WHERE` that you have shown; never `TRUNCATE` or `DROP` outside an approved
  migration.
- **No bypass.** If a tool or permission layer refuses a data action, stop and ask. Do not try an equivalent route.
- **Shared environments:** if the database is shared with real users, say so in the binding and treat every write as
  production.
