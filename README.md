# SpecAlign

Executable-specification skill for AI agents: it extracts and maintains agent-readable specs for
**existing** features, validating every claim against a triple source of truth — **code, live
database, runtime behavior**. GENESIS reverse-engineers undocumented features; SYNC realigns
existing docs with reality. Supersedes `brownfield-spec` (retired 2026-08-25).

## Invocation

SpecAlign runs inside an agent conversation — there is no CLI. Address the agent with:

| Command | Effect |
|---|---|
| `SpecAlign GENESIS <F-id>` | Reverse-engineer feature `<F-id>` into a new spec |
| `SpecAlign SYNC <F-id>` | Realign an existing spec with current reality |
| `SpecAlign list` | Read the registry (`docs/specs/INDEX.md`), propose the next pilot |
| `SpecAlign selfcheck <F-id>` | Run the spec's §14 self-check; report only, change nothing |
| `SpecAlign drift [F-ids]` | Run drift probe on all (or named) features; propose REGISTRY Stale flips on confirmation |
| `SpecAlign init` | Bootstrap `binding.md` + `INDEX.md` from zero via config scan (manual gate) |
| `SpecAlign rescan` | Update `binding.md` diffs + propose new `INDEX` rows (protected fields untouched) |
| `abort` | Stop mid-run; summarize; write nothing |

The agent proposes a **tier** (Micro / Standard / Core) at scope time; you decide. Gates close on
the exact approval statements printed by the agent — a bare "yes" to a shown statement counts.

## Package Shape

- `SKILL.md` — authoritative 14-stage workflow (binding gate → inventory → evidence → draft →
  verification → finalization), dynamic tiers, cross-section pass, approval statements.
- `references/verification-playbook.md` — DB introspection queries, UI behavioral protocol,
  cleanup pathways, the 17-trap validation matrix, commit hygiene.
- `templates/specification-template.md` — the 18-block executable spec format (§13A–§13D logs).
- `templates/handoff-readme-template.md` — seed for a project's `docs/specs/README.md`.
- `CHANGELOG.md` — version history; single home.

## Configuration (per adopting repository)

SpecAlign is project-agnostic; all project values live in `<SPEC_DIR>/binding.md`. Required keys:
`PROJECT_MAP`, `SPEC_DIR`, `REGISTRY`, `DB_TOOL`, `UI_TOOL`, `TAG_PREFIX`, `TEST_DATA_PREFIX`,
`BASELINE_DATE` (ISO 8601), `CONVENTIONS`, `PROJECT_PITFALLS`; optional: `TEST_ACCOUNTS`,
`GOVERNING_SKILL`, `UI_REVIEW_SKILL`, `DOCS_REVIEW_SKILL`. Missing/incomplete binding stops the
run — never guessed. Example: `references/binding-example-sanad.md`.

## Adopting SpecAlign in Another Repository

1. Copy this folder into your skills directory.
2. Create `docs/specs/binding.md` from the example, filling your tools and conventions.
3. Seed `docs/specs/INDEX.md` (one row per feature, status `Undocumented`).
4. Invoke `SpecAlign list` and pick a pilot (full CRUD + few lookups, ≤10 min verifiable).

## Quality

Every stage transition is gated (inventory confirmation, anti-pattern checkpoint, Socratic
questions, write permission). Evidence rules are tier-invariant: Micro compresses documentation
breadth, never citations or verification. Validation status: field-tested draft (v0.9.0) — RED
failures documented from two pilots; GREEN pressure scenarios pending first SpecAlign pilot
(see `SKILL.md` → Validation Status; flips to v1.0.0 after one clean run). Version history:
`CHANGELOG.md`.

## Troubleshooting (day-one failures only)

- **Run refuses to start: "dirty tracked files"** — commit or stash changes under `docs/specs/`
  or the feature's code paths first; unrelated untracked files are fine.
- **Browser wedged after a print dialog** — navigate to about:blank, re-login, re-navigate;
  affected steps become `code-verified-only`.
- **Read-only database tool blocks cleanup** — remove test rows via the app UI (soft-delete),
  or execute the generated SQL yourself; the agent verifies afterward.
- **Commit staged nothing** — check path case (`Skills/` vs `skills/`); verify staged count
  before committing (playbook §6).
