# SpecAlign

Executable-specification skill for AI agents: it extracts and maintains agent-readable specs for **existing**
features, validating every claim against a triple source of truth — **code, live database, runtime behaviour**.
GENESIS reverse-engineers undocumented features; SYNC realigns existing docs with reality. Supersedes
`brownfield-spec` (retired 2026-08-25).

> **Status: 1.0.0-dev** (branch `v1-production`). See `CHANGELOG.md` for what changed from 0.11.0 and what is still
> planned. The version flips to 1.0.0 only when the release criteria are met (evals green, three dry-run adoptions).

## Invocation

SpecAlign runs inside an agent conversation. Address the agent with:

| Command | Effect |
|---|---|
| `SpecAlign GENESIS <F-id>` | Reverse-engineer feature `<F-id>` into a new spec |
| `SpecAlign SYNC <F-id>` | Realign an existing spec with current reality |
| `SpecAlign list` | Read the registry, propose the next pilot |
| `SpecAlign selfcheck <F-id>` | Run the spec's §14 self-check; report only, change nothing |
| `SpecAlign drift [F-ids]` | Run the drift tool; propose registry `Stale` flips on confirmation |
| `SpecAlign init` / `rescan` | Bootstrap or maintain `binding.md` + `INDEX.md` |
| `abort` | Stop mid-run; summarise; write nothing further |

The agent proposes a **tier** (Micro / Standard / Core); you decide. Gates close on the filled approval statements
the agent shows — a bare "yes" to a shown statement counts, and your reply is recorded verbatim.

## Package shape

| Path | Purpose |
|---|---|
| `SKILL.md` | the router: invariants, tiers, the 14-stage pipeline table (read this first) |
| `stages/` `modes/` `gates/` | per-stage, per-mode and per-gate instructions, loaded on demand |
| `templates/` | 18-block spec template, binding template, rescan report, handoff README, adopter CI |
| `references/` | verification playbook (DB/UI protocols, cleanup, validation matrix), example binding |
| `adapters/` | what a DB / UI / test adapter must provide |
| `tools/specalign/` | stdlib-only Python CLI: `registry check`, `drift` (+ installer module) |
| `scripts/` | thin wrappers keeping the old `rescan_check.py` / `drift_probe.py` entry points |
| `install.py` | installs and verifies the skill in `~/.claude/skills` and `<project>/.opencode/skills` |
| `tests/` | `unittest` suite (fixtures are throwaway git repos); `python -m unittest discover -s tests` |

## Install and update

```
python install.py --project /path/to/project        # global + project copy, LF, with INSTALL-MANIFEST.json
python install.py --project /path/to/project --check   # exit 1 on hand edits, missing or out-of-date files
```
An update refuses to overwrite a file that was edited by hand since the last install (`--force` to override).

## Tools

```
python -m specalign registry check <repo>    # run from <skill>/tools; INDEX ↔ spec ↔ §0 Card ↔ exact tag
python -m specalign drift <repo> [F-ids]     # sources changed since each release tag
```
Exit codes: `registry check` 0 ok · 1 findings · 2 error. `drift` 0 clean · 1 drift · 2 error · 3 unverifiable with
`--strict`. `--json` output is a stable contract for CI (`templates/adopter-ci.yml`).

## Configuration (per adopting repository)

All project values live in `<SPEC_DIR>/binding.md` (template: `templates/binding.template.md`; example:
`references/binding-example-sanad.md`). A missing or incomplete binding stops the run — values are never guessed.

## Adopting SpecAlign in another repository

1. `python install.py --project <repo>`.
2. Create `docs/specs/binding.md` from the template and `docs/specs/INDEX.md` (one `Undocumented` row per feature).
3. Copy `templates/adopter-ci.yml` to `.github/workflows/specalign.yml`.
4. Invoke `SpecAlign list`, pick a small pilot (full CRUD + few lookups, ≤10 min to verify).

## Quality

Every stage transition is gated; evidence rules are tier-invariant. The mechanical checks (registry, drift) are
tool-run and pasted, never retyped. What is **not** yet validated: the behavioural gates have no executable evals
(playbook §5 rows 21–29 are "not exercised"), and `lint`/`finalize`/`manifest` are planned.

## Troubleshooting (day-one failures only)

- **"dirty tracked files"** — commit or stash changes under `SPEC_DIR` or the feature's code paths; unrelated untracked
  files are fine.
- **Browser wedged after a print dialog** — about:blank, re-login, re-navigate; affected steps become
  `code-verified-only`. Declare it in the binding's capability profile so it is never triggered.
- **Cleanup blocked by a read-only database tool** — scoped SQL with an X1 confirmation (`gates/ddl-protocol.md`).
- **Commit staged nothing** — check path case (`Skills/` vs `skills/`); verify the staged count (playbook §6).
- **`registry check` fails right after finalizing** — the tag is created after the commit; re-run it after the tag exists.
