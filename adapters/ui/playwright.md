# UI adapter — Playwright

Works with the Playwright MCP tools or a Playwright script. Read the project's `CAPABILITIES` first; the defaults
below hold when the binding is silent.

| Capability key | Meaning | Typical value for a headless run |
|---|---|---|
| `ui.trusted_clicks` | a natural click / key press reaches the page | `false` if the runtime ignores trusted input; clicks then need the scripted fallback (`runtime-js-click`) |
| `ui.print_blocks` | a print / save dialog wedges the browser | `true` in headless runs: never trigger `window.print()` or a download dialog; those steps are `code-verified-only` |
| `ui.select_driver` | how to drive custom `Select` widgets | `js` (dispatch through the DOM) or `keyboard` |

## Procedure
1. Navigate to the app; if the session is gone, log in with `TEST_ACCOUNTS` only.
2. After every state-changing action assert the effect within 2 s (element appears, request fires). On failure:
   retry once, then a scripted `.click()` — label the evidence `runtime-js-click` and add an anomaly row to §13B.
3. Prefer reading `document.body.innerText` / the DOM through an evaluate call over screenshots and accessibility
   snapshots when they time out or come back empty (web fonts, large single-page apps). Do not retry them.
4. Verify the result of a data mutation in the database through `DB_TOOL`, not by navigating back through the UI.
5. Transient text (toasts): trigger the action and read the DOM in **one** evaluate call. If still missed, the string
   is `code-verified-only`; never paraphrase.
6. Forced conditions (offline emulation, delayed or failed routes) are `runtime-synthetic`, not `runtime`.
7. Console / network: list both after each flow; a 4xx on a deliberate conflict path is expected and noted.

Recovery after a wedge: navigate to `about:blank`, log in again, re-navigate; the affected steps become
`code-verified-only` with the reason.
