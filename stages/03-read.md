# Stage 3 — Read: code, data, UI, validation, permissions

Read-only. Cite everything (`file:function`, SQL, browser step). Findings become DFs (numbered once).

## 3a Code
Read every inventoried file: actual behaviour, error codes, verbatim user-facing messages, transactions, side
effects. Include the tests — they document intent and reveal gaps.

## 3b Data model (`DB_TOOL`, playbook §1)
Tables, columns, types, defaults, constraints, partial indexes, triggers, enums — as observed in the live database.
Also enumerate what the feature **consumes**: relevant triggers, materialized/aggregate views, DB functions
(calculators, notify hooks). Record a schema fingerprint (a hash of the introspection result) in §0 when the adapter
supports it.

## 3c UI and flows
Layout, visual states (loading / empty / error / **stale** / offline / read-only / conflict), flows with alternative
paths, accessibility as observed (names, roles, keyboard, focus). UI-heavy feature and binding `UI_REVIEW_SKILL` set
→ load it here.

## 3d Validation pairing
Client schema ↔ database constraint, field by field. Any mismatch is a DF; never silently pick a side.

## 3e Permissions — the isolation trio
Per action: **soft check** (UI) · **hard enforcement** (server) · **audit trail** (logging). Enforcement absent where
sibling features have it → DF.

Features with no database or no UI skip 3b / 3c and say so in §13B (`N/A — reason`), they do not invent content.
