# Adapters

The core skill is stack-neutral. Everything that depends on a stack is declared in `binding.md` and performed
through an adapter: a short description of how to do a few things with the project's tools.

## DB adapter

Must provide: introspection of tables, columns, constraints, indexes, triggers (and views / enums where the engine
has them); a read-only query; a guarded write (D1 / X1 scope); a **schema fingerprint**.

| Engine | Introspection query | Notes |
|---|---|---|
| PostgreSQL | `adapters/postgres/introspection.sql` | exercised against a live database (Sanad); views, enums and functions need extra queries, see `references/verification-playbook.md` §1 |
| MySQL / MariaDB | `adapters/mysql/introspection.sql` | same row shape; not yet exercised against a live server |
| SQLite | `adapters/sqlite/introspection.sql` | DDL text per object; not yet exercised against a live file |
| none | — | the feature has no database: mark §5 `N/A — reason`, `Schema fingerprint: n/a` |

**Fingerprint workflow.** Run the engine's query for the spec's tables through `DB_TOOL`, save the result as a JSON
array of rows `{kind, tbl, name, detail}`, then `python -m specalign schema fingerprint --input rows.json` and put the
printed `sha256:…` in the §0 Card (`Schema fingerprint`). Store the rows with
`schema snapshot <repo> <F-id> --input rows.json`. Later, `schema check <repo> <F-id> --input rows.json` exits 1 when
the live schema no longer matches and lists the added / removed / changed objects from the snapshot. The query must
return one row per object (duplicates are an error).

## UI adapter

Must provide: open a page, act under the declared **capability profile**, capture text / console / network, assert an
effect within 2 s, and a scripted-click fallback that is labelled `runtime-js-click`.

| Tool | File | Declare in the binding |
|---|---|---|
| Playwright (MCP or library) | `adapters/ui/playwright.md` | `CAPABILITIES` keys `ui.trusted_clicks`, `ui.print_blocks`, `ui.select_driver` |
| Chrome DevTools (MCP) | `adapters/ui/chrome-devtools.md` | same keys |
| none | `adapters/ui/none.md` | features with no UI verify through the test adapter; §3 is `N/A — reason` |

## Test adapter

Must provide the test and typecheck commands and a way to read counts. Set `TEST_COMMAND` and `TYPECHECK_COMMAND`
in the binding; any runner that prints pass/fail counts works (`node --test`, `pytest`, `go test`, `cargo test`).
Evidence labels `unit` / `contract` cite the command and the counts, never "tests passed".

## No DB / no UI

A feature with neither (a CLI, a library, a batch job) still gets a spec. Mark §5 and §3 `N/A — reason` in §13B and
verify through the test adapter; evidence labels still apply.
