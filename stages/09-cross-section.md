# Stage 9 — Internal consistency and cross-section → status Verifying

Cross-check flows ↔ API ↔ data model ↔ validation. Then the **cross-section pass** (mandatory at Core, recommended
at Standard) over section pairs:

- flows ↔ API · roles ↔ UI · validation ↔ DB · errors ↔ edge cases
- **terminology**: one concept = one meaning across sections (catches a label backed by two different data fields)
- every inventoried endpoint shows an in-scope CONSUMER, or §6 names the owning feature
- every AC has a flow and an evidence entry; every Resolved DF has an AC (`gates/evidence.md`)

Fix inconsistencies in the draft; unresolved ones go to §13A as questions. Spec and registry status move to
**Verifying**.
