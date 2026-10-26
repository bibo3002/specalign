# Executable Specifications Handoff — template

## How to read a spec
§0 Card first (status/version/tier/tag/commits) → §1–§12 top to bottom → §13A open questions
(answer them) → §13B verification evidence (incl. budget timestamps, anomaly rows, decision
records) → §13C evolution history → §13D approval history → §14 the self-check it passed.

## Statuses
Undocumented → Draft → Verifying → Approved → Stale.
"Stale" = code changed without a spec update; untrustworthy until SYNC.
Legacy-format specs stay Approved; they normalize to the SpecAlign template at their next SYNC.

## The sync rule (binding)
Any change to a documented feature updates its spec in the SAME commit/PR (SpecAlign SYNC).

## Versioning
patch wording · minor non-breaking behavior · major contract/data-model/breaking (owner approval).
Version bump only at approval; every version gets an Evolution entry (§13C).

## Tags / Baselines
`<TAG_PREFIX>F{n}-{slug}-vX.Y.Z` at the finalization commit — the tag IS the frozen baseline.
Tag and push require owner approval via the exact gate statements.

## Registry
INDEX.md lists every feature: status, version, tag, tier, verification coverage (code/DB/runtime),
and the current next-pilot recommendation.
