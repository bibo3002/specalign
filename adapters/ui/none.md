# UI adapter — none

For features without a user interface (services, libraries, batch jobs, CLIs).

- §3 of the spec is `N/A — no UI`, recorded in §13B.
- Behaviour is verified through the test adapter (`unit` / `contract`) and, for CLIs, by running the command and
  quoting its real output (`runtime`).
- The 10-minute budget applies to the cumulative time of those runs, if any.
- Accessibility and visual-state rows of the template are removed with that justification in §13A.
