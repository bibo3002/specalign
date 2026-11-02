# Executable Specifications Handoff — template (SpecAlign v1.0)

Skill version used for the specs in this folder: {X.Y.Z} (each spec's §0 Card records the version it was made with).

## How to read a spec
§0 Card first (status/version/tier/tag/commits/evidence legend) → §1–§12 top to bottom → §13A open questions and
deviation flags (answer the questions) → §13B verification evidence (incl. budget timestamps, anomaly rows, decision
records) → §13C evolution history → §13D approval history → §14 the self-check it passed.

## Statuses
Undocumented → Draft → Verifying → Approved → Stale.
"Stale" = code changed without a spec update; untrustworthy until SYNC.
Legacy-format specs stay Approved; they normalise to the SpecAlign template at their next SYNC.

## The sync rule (binding)
Any change to a documented feature updates its spec in the SAME commit/PR (SpecAlign SYNC). A change to a shared
component also patches every other spec that documents it (ripple patch).

## Versioning
patch: wording, evidence upgrades, ripple patches · minor: behaviour added or hardened without breaking a contract ·
major: contract or data-model break (owner approval). Version bump only at approval; every version gets an Evolution
entry (§13C); superseded wording stays visible there.

## Tags / baselines
`<TAG_PREFIX>F{n}-{slug}-vX.Y.Z` at the finalization commit — the tag IS the frozen baseline. Tags, pushes, live
schema changes and data deletion each need their own recorded approval (§13D).

## Registry
`INDEX.md` lists every feature: status, version, tag, verification coverage (code/DB/behaviour) and the next-pilot
note. Its rows must agree with each spec's §0 Card and with the git tags.

## Checks you can run
```
python -m specalign registry check .     # INDEX ↔ spec ↔ tag consistency (CI blocks on this)
python -m specalign drift .              # source changes since each release tag (informational)
```
