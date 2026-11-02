# Versioning

`MAJOR.MINOR.PATCH` of a **spec**. The tag `<TAG_PREFIX>F{n}-{slug}-vX.Y.Z` marks the finalization commit and is the
immutable baseline. Every version has a §13C entry. Version and tag are set only at approval.

## What bumps what

| Bump | Use when | Examples |
|---|---|---|
| **PATCH** | wording, corrections to the document, evidence upgrades, registry metadata, **ripple patches** (below) | a code-verified claim gets runtime evidence; a Sources line is fixed |
| **MINOR** | behaviour added or hardened without breaking any documented contract | new field, extra validation that previously-valid input still passes, a new endpoint |
| **MAJOR** | a documented contract or data model changes incompatibly — **needs V1** | response shape changes, an input that used to succeed is now refused, a column/constraint redefinition |
| **1.0.0** | first SpecAlign-normalized approval (GENESIS, or SYNC of a legacy spec) | — |

Decision tree for a SYNC that also fixes behaviour: *Could a client written against the previous spec break?*
Yes → MAJOR (V1). No, and behaviour changed → MINOR. Otherwise → PATCH.

Normalising a legacy spec to the template is MINOR unless it also fixes behaviour as above.

## Ripple patches

When a run changes something that another approved spec documents (a shared component, an endpoint another tab
uses), that spec is **patched in the same run**, not left stale:

1. PATCH bump of the other spec; its §13C row says *what changed, caused by which spec/version*, and keeps the
   superseded wording visible ("Superseded wording: …", Rule 9).
2. One §13D row per patched spec pointing at the approving run (the same W1/G1 approval, listed explicitly).
3. A tag per patched spec (`G1` must list them) and an updated INDEX row for each.
4. The patched spec's `Last verified` date is the run date **only** for the claims actually re-checked.

## Rules

- Never edit the version of an Approved INDEX row without a matching tag and spec change.
- A major bump, any tag and any push need explicit approval (V1, G1, P1).
- `specalign registry check` fails when INDEX, the spec's §0 Card and the tag disagree about version.
