# Spec Binding — Sanad (سنَد) — EXAMPLE (placeholders; real credentials live in the project's own binding)
PROJECT_MAP: AGENTS.md
SPEC_DIR: docs/specs
REGISTRY: docs/specs/INDEX.md
DB_TOOL: postgres MCP (read-only in this project)
UI_TOOL: playwright MCP
TAG_PREFIX: spec/
TEST_DATA_PREFIX: __TEST_
BASELINE_DATE: 2026-08-15
GOVERNING_SKILL: .opencode/skills/specalign

TEST_ACCOUNTS: <placeholders only — never store credentials inside the portable skill>

CONVENTIONS:
  prose: English primary; technical identifiers as in code; canonical Arabic domain
         terms kept where they are the name of record
  ui_strings: verbatim Arabic from runtime, quoted exactly
  dates: ISO 8601 (YYYY-MM-DD) in all spec/skill metadata

PROJECT_PITFALLS:
  - «طباعة السجل» triggers window.print() → native dialog wedges Playwright.
    Recovery: about:blank → re-login → re-navigate; mark print flows code-verified-only.
  - GET /api/auth/me is a 501 stub → always re-login after any browser recovery.
  - postgres MCP is read-only → cleanup runs via user-executed SQL or UI soft-delete, then verified read-only.
  - Some lookup tables have no UI delete → SQL cleanup only.
  - Tests run on the live DB: only rows prefixed __TEST_ may be created or deleted;
    non-prefixable tables follow playbook §4-3.
