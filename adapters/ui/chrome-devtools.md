# UI adapter — Chrome DevTools (MCP)

Same procedure and capability keys as `playwright.md`; what differs:

- Strengths: network inspection (request / response bodies), console messages, performance traces, device and network
  emulation. Use emulation for offline / slow-network flows and label them `runtime-synthetic`.
- Headless sessions often cannot take screenshots or accessibility snapshots reliably; read the DOM through an
  evaluate call instead.
- A headless instance with no display fails to launch headful ("Target closed"): the server must be started headless.
- Do not attach to the user's own browser session; open a separate page for the run.
- Close the page you opened when the run ends.
