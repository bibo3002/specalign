# Adapters

The core skill is stack-neutral. Everything that depends on a stack is declared in `binding.md` and performed
through an adapter: a short description of how to do four things with the project's tools.

| Adapter | Must provide | Status |
|---|---|---|
| **DB** | introspection (tables, columns, constraints, indexes, triggers, views, enums); read-only query; guarded write (D1 / X1 scope); a schema fingerprint | PostgreSQL via an MCP tool is documented in `references/verification-playbook.md` §1. MySQL, SQLite and "none" are planned. |
| **UI** | open a page, act with the declared capability profile, capture text/console/network, wait for effect ≤ 2 s, scripted-click fallback | Playwright and Chrome DevTools quirks are documented in `references/verification-playbook.md` §2. |
| **Test** | the test and typecheck commands, a way to read counts | any runner that prints counts; set `TEST_COMMAND` in the binding. |

**No DB / no UI:** a feature with neither (a CLI, a library, a batch job) still gets a spec. Mark §5 (data) and §7 (UI)
`N/A — reason` in §13B and verify through the test adapter; evidence labels still apply.
