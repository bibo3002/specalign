# Mode GENESIS — document an undocumented feature

Use when the registry row is `Undocumented` (or `Draft` with no spec file) and the feature exists in code.

Pipeline: the full stage list in SKILL.md, in order. Specifics:

- **Stage 2** builds the inventory from the code (there is no spec to start from). Name the registry row and
  confirm the F-id with the user.
- **Version** starts at `1.0.0` for the first approved spec; tag `<TAG_PREFIX>F{n}-{slug}-v1.0.0`.
- **Merged features:** when two registry rows describe one implementation (e.g. a create form and an edit form that
  are the same component), merge them into one spec; the absorbed row becomes `Merged → F{n}`, keeps no spec file,
  and is mentioned in the surviving spec's §1.
- **Legacy docs** (older architecture notes, prior executive specs) are *inputs* to read, not sources of truth;
  anything taken from them is re-verified, and their fate (kept as history / retired) is a Q in §13A.
- New feature discovered during the run → add its registry row with status `Undocumented` in the same change.
