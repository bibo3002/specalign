# Releasing SpecAlign

The version lives in four places that must agree (`tests/test_skill_docs.py::test_one_version_everywhere` fails
otherwise): `VERSION`, `tools/specalign/__init__.py`, the title of `SKILL.md`, and a `## [x.y.z]` section of
`CHANGELOG.md`. An adopting project records the version it uses as `SKILL_VERSION` in its `binding.md`.

## 1.0.0 criteria and where they stand

| Criterion | Status |
|---|---|
| All tool-level evals green on Linux and Windows, Python 3.10 and 3.12 | **met** — CI matrix, `python -m specalign eval` |
| Behavioural evals (17 matrix rows) graded on recorded transcripts | **not met** — graders and the recording procedure exist (`evals/README.md`); no transcripts recorded yet. Rows 3–7, 9–11, 13–15, 21–24, 26, 27 are "not exercised" |
| Linter clean on the reference corpus (Sanad, 14 specs) | **met with a baseline** — 0 new errors; 6 known SPEC-F4 findings baselined (`docs/specs/lint-baseline.json`), 84 legacy traceability warnings |
| Three dry-run adoptions | **met** — Sanad (real: Postgres, Vue/Fastify, migrated and CI-green), a Python service with decorator routes and SQLite, a no-DB no-UI library (`tests/test_adoption.py`) |
| Golden finalization replay | **met** — F6's real finalization edits replayed with `finalize` give byte-identical spec and registry, and a second apply changes nothing |
| Documented install / update / rollback | **met** — `README.md`, `install.py --check`, section below |

Release the version as `1.0.0` only when the behavioural row is met or the owner accepts it explicitly in the
release notes. Until then the build is `1.0.0-dev`; a release candidate may be tagged `v1.0.0-rc.N`.

## Cutting a release

1. `python -m unittest discover -s tests -p "test_*.py"` and `cd tools && python -m specalign eval` are green; CI is
   green on the branch.
2. Set the four version places; move `[x.y.z] — unreleased` to a dated heading; update the criteria table above.
3. Merge to `main` (reviewed), then tag `vX.Y.Z` on the merge commit and push the tag. Tagging and pushing are
   owner-approved actions.
4. In each adopting project: `python install.py --project <repo>` from the tagged checkout, run the project's gates
   (`preflight`, `registry check`, `lint`, `drift --own-only`), commit the refreshed skill copy.

## Updating an installed copy

`python install.py --project <repo> --check` compares the installed copy with the source: hand edits, missing and
out-of-date files are listed, and a CRLF checkout is not a hand edit. An update refuses to overwrite a hand-edited
file unless `--force`. Files shipped by releases before 1.0 that no longer exist are pruned.

## Rolling back

The skill copy is tracked in the adopting project, so `git revert` of the update commit restores the previous copy.
Run records, specs and tags are not touched by an update. The tools only read specs and the registry; the only
commands that write are `docedit`, `finalize apply`, `finalize tag`, `finalize push --execute`, `manifest` and
`schema snapshot`, and the finalize commands refuse without the matching recorded approval.
