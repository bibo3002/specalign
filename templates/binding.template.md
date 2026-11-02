# Spec Binding — <Project name>
<!-- Top-level `KEY: value` lines are read by the tools (TAG_PREFIX, SPEC_DIR …). Indented blocks are for the agent. -->
PROJECT_MAP: AGENTS.md
SPEC_DIR: docs/specs
REGISTRY: docs/specs/INDEX.md
DB_TOOL: <postgres MCP | mysql MCP | sqlite file | none>
UI_TOOL: <playwright MCP | chrome-devtools MCP | none>
TEST_COMMAND: <e.g. npm test>
TYPECHECK_COMMAND: <e.g. npm run typecheck>
TAG_PREFIX: spec/
TEST_DATA_PREFIX: __TEST_
BASELINE_DATE: <YYYY-MM-DD>
SKILL_VERSION: 1.0.0
UI_REVIEW_SKILL:
DOCS_REVIEW_SKILL:

CAPABILITIES:
  ui.trusted_clicks: <true|false>        # false → scripted clicks are the norm; label runtime-js-click
  ui.print_blocks: <true|false>          # true → never exercise window.print() flows
  ui.select_driver: <how custom selects must be driven>
  db.shared_with_real_users: <true|false> # true → treat every write as production
  db.audit_table: <name>                 # immutable: never hand-delete (gates/ddl-protocol.md)

TEST_ACCOUNTS:
  <role>: { email: <…>, password: <…> }   # behavioural tests only; never real users

CONVENTIONS:
  prose: <language of the spec text>
  ui_strings: verbatim from runtime, quoted exactly, in their own language
  dates: ISO 8601 (YYYY-MM-DD) in spec metadata

PROJECT_PITFALLS:
  - <environment trap and its recovery>
