# Stage 6 — Verification (after any remediation, before the draft)

Evidence is produced here, so it describes the code that will be tagged.

## 6a Automated
Run the project's test commands (from the binding / adapter). Record command, counts, duration. Contract tests that
need a database run against the test database named in the binding.

## 6b Behavioural (`UI_TOOL`, playbook §2)
- `TEST_ACCOUNTS` only; create only rows carrying `TEST_DATA_PREFIX` (non-prefixable tables: playbook §4-2b).
- Verbatim capture of user-facing strings, in their own language.
- **Silent click failure protocol:** assert the effect within 2 s → retry once → scripted `.click()` fallback →
  label the evidence `runtime-js-click` and add an anomaly row.
- Transient-capture recipe for toasts; optional negative-claim probes.
- Declared capability profile wins: if the binding says a flow wedges the driver (e.g. native print dialog), mark it
  `code-verified-only` with the reason and **do not exercise it**.
- Budget: ≤10 min cumulative; timestamps in §13B. No conflict path exists → `conflict: N/A`; never manufacture one.
- Unverifiable in budget → `code-verified-only` + reason.

## 6c Cleanup
Remove what you created, scoped by prefix/owner/time window (`gates/ddl-protocol.md`, X1 when ambiguous). Prove it
with a count query; record the statements and counts. Audit rows from interactive tests stay.

Each result becomes a dated, labelled entry (`gates/evidence.md`) in §13B.
