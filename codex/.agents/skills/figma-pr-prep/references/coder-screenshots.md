# Browser verification and screenshots on Coder

Use the current checkout's browser-testing workflow rather than copying machine-specific URLs or MCP settings. Paths here are relative to the Figma monorepo.

## Preferred entry point

Read `.claude/plugins/browser-testing/skills/agent-browser-testing/SKILL.md`. It owns setup, environment detection, login, and browser interaction. Reuse a working environment; run its setup only when needed. Check the current skill before using these entry points:

```bash
.claude/plugins/browser-testing/skills/agent-browser-testing/setup.sh
.claude/plugins/browser-testing/skills/agent-browser-testing/detect-environment.sh
```

Detection reports `MODE` and `URL`. Use that detected workspace URL, not a guessed staging/production URL:

```bash
agent-browser open "<URL from environment detection>"
agent-browser snapshot
# Interact using current element references from the snapshot.
agent-browser screenshot /tmp/figma-screenshot.png
```

Use seeded development accounts for the workspace and test accounts for staging, following the current skill; do not default to personal Okta SSO. For staging with a Coder frontend, follow the skill's “Coder workspace” recipe (`X-Figma-Local-Web`) and verify the assets actually come from the workspace. A screenshot of a different deployed build is not verification of the local change.

Inspect and display the saved screenshots in chat. Capture the affected surfaces and boundary/error state where it explains the change. Add screenshots to a PR when that publication is authorized. Interactive verification does not create a repeatable automated test suite or CI job.

If the repository skill is missing, locate the current repository instructions for browser tooling and report the unavailable entry point. Continue independent PR preparation and state any missing screenshot evidence; do not guess replacement setup commands.

## Playwright MCP alternative

If using `playwright-dev`, compare the checkout's `.codex/config.toml` with its **current** `.codex/config.toml.example`. Ensure the working directory points to the Coder checkout and preserve the example's Coder environment-variable forwarding. Historical failures came from stripped environment variables causing incorrect Coder detection and local-network access failures. Restart the Codex session after changing MCP configuration if required. Do not replace the user's entire configuration or copy stale machine paths.

## Troubleshooting references

- [Screenshot workflow](https://figma.slack.com/archives/C08ESKNPUCA/p1778076321385119).
- [Coder browser verification report](https://figma.slack.com/archives/C08TL5U762Z/p1777428998054899).
- [Coder Playwright configuration fix](https://figma.slack.com/archives/C0ADYJQDM47/p1777387466596399).
- [Working Codex/Coder configuration discussion](https://figma.slack.com/archives/C09K8SVMQD6/p1778086709070429).
