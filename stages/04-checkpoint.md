# Stage 4 — Anti-pattern scan and checkpoint (gate)

## Scan
Base checklist (extensible; cite the rationale for any addition):
1. endpoint error handling missing · 2. missing UNIQUE where logic implies one · 3. soft-delete column unfiltered ·
4. audit columns missing vs siblings · 5. N+1 / missing transaction · 6. hard-coded values vs config ·
7. client schema ≠ DB constraint · 8. shared component changed here but documented by another spec (ripple) ·
9. claims the tests do not pin (no test for a documented behaviour).

State the **E5 result** explicitly ("flags found: …" / "none found"). Zero findings → say "No anti-patterns detected".

## Checkpoint message
Numbered DFs with severity, claim + citation, **recommended disposition**, files each Fix would touch, and any live
DDL needed — the table format is in `gates/dispositions.md`.

⚠️ **Gate R1:** the user edits the table or accepts the recommendations. The reply, quoted verbatim, authorizes a
**remediating run** limited to the listed files (`gates/remediation.md`).

**No DF marked Fix → nothing to authorize.** The run is **documentation-only**: do not ask for R1 (it would authorize
nothing), show the table and the E5 result, and continue once the user acknowledges it (record the reply as a
`manifest add . note`). Stage 5 is skipped; the manifest's run type stays `documentation-only`.

Record in the run state: run type, dispositions, files in scope, whether DDL is pending.
