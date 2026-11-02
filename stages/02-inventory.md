# Stage 2 — Meta-discovery inventory

Build the table, then cross-check it against reality.

| Variable | Source |
|---|---|
| FEATURE_NAME | spec §0 (SYNC) / user + PROJECT_MAP (GENESIS) |
| ROUTE_PATH(S) | router files |
| FRONTEND_FILES | grep on the frontend tree |
| API_ENDPOINTS **+ CONSUMER** | server grep; CONSUMER = the frontend caller of each endpoint |
| DB_TABLES / CONSTRAINTS | code grep + `DB_TOOL` |
| STATE_MODULES | stores / composables / hooks |
| TYPE_SCHEMAS | validation schema files |
| TESTS | unit / contract tests that exercise the feature |

SYNC: extract from the spec first, then cross-check the code — the table reflects what the code actually has, not what
the spec claims. Run `python -m specalign drift <repo> <F-id>` and list **dead sources** (patterns matching no tracked
file). Mismatches → §13A. Cross-check `PROJECT_MAP` too.

Let the tool do the mechanical part: `python -m specalign inventory <repo> <F-id> [--tables-file t.json]` lists
endpoints registered in code that no spec documents, endpoints a spec lists that no source file registers, and (with
the live table list from `DB_TOOL`) tables used by SQL that no spec names. It is advisory and static: routes built at
run time (`/lookups/${name}`) are reported as a note, not listed. Paste its output into the inventory message.

Every endpoint needs an in-scope CONSUMER, or §6 records the owning feature — silent drops are forbidden.

⚠️ **Gate:** present the table and wait for the user's confirmation.
