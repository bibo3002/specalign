# Stage 1 — Scope and tier → status Draft

1. State **in scope / out of scope** explicitly (recorded in §1 of the spec).
2. Propose a **tier** with reasoning (table in SKILL.md). Micro is forbidden when the change touches the data model,
   permissions, security or an API contract, or makes any new behavioural claim.
3. Propose, now rather than at the end: the **version** (see `gates/versioning.md`), the **tag slug**, the **files /
   specs the run may need to patch** (ripple), and the **verification channel**.
4. ⚠️ **Gate T1** (`gates/approval-statements.md`): explicit tier decision before anything else. Record it in §13B and
   in the run state. Open questions on version/tag/scope are resolved here, not after the draft.

Forbidden at every tier: skipping discussion · executing without a tier decision · relaxing Rule 4 citations ·
using Micro to rush a behavioural change · inventing evidence.
