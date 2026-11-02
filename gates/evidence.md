# Evidence vocabulary and traceability

Every behavioural claim in a spec carries an evidence label from this list, defined once in the spec header
(§0 legend) and used verbatim. Specs may add a short note per label (test file names) but not new labels.

| Label | Meaning | Strength |
|---|---|---|
| `code` | read in source, cited as `file:function` (Rule 4) | citation only |
| `db` | result of an introspection or query against the live database, query shown | observed |
| `static` | typecheck, lint, grep, schema diff | mechanical |
| `unit` | unit test, no I/O | tested |
| `contract` | in-process API / integration test against a real database or equivalent | tested |
| `runtime` | real driver run (browser/CLI/device) with natural interaction | observed |
| `runtime-js-click` | `runtime`, but the control needed a scripted click (trusted input unavailable); an anomaly row explains why | observed, weaker |
| `runtime-synthetic` | `runtime` under injected conditions (offline emulation, delayed route, forced error) | observed, constructed |
| `historical-log` | evidence from an earlier version, carried forward and dated; not re-run | stale-capable |
| `code-verified-only` | **not exercised**; reason required (print dialog, budget, destructive, no UI path) | weakest |

Aliases kept for legacy specs: `inject` = `contract`, `DB` = `db`.

## Rules

1. A behaviour claim without a label is invalid; `code-verified-only` is the honest default, never `runtime`.
2. A label names a **real artefact**: test file + count, query text, browser step with timestamp. "Looked fine" is not
   evidence.
3. `runtime` evidence comes from the *current* version; carrying older evidence forward uses `historical-log` and a
   date.
4. Do not manufacture conditions that the product cannot produce (no invented conflict paths); record `N/A` instead.

## Traceability chain

```
DF-n ──resolves──▶ AC-m ──cites──▶ V-k (evidence entry in §13B) ──labelled──▶ one label above
              └─ flow F{n}-x  (the user/system path the AC lives in)
```

- Every `Resolved` DF has ≥1 AC; every AC has a flow and ≥1 V-entry; every V-entry has a label and a date.
- §13D (approval history) rows reference the D-entries in §13B that record the decisions.
- `specalign lint` (planned, P1) enforces these links; until it ships, the self-check (stage 10) walks them by hand
  and lists any break as ✗.
