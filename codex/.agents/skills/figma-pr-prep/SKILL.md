---
name: figma-pr-prep
description: Prepare a Figma monorepo pull request or write its description with relevant test evidence, UI screenshots, product sign-off, and generated diff context. Use for PR authoring and readiness, not ongoing feedback polling, a general code review, or Figma design-file work.
---

# Figma PR preparation

Use the current diff, linked ticket, repository instructions, and PR template. Apply the points relevant to this change; do not turn past trial-specific questions into a checklist for every PR. Preparing a PR does not itself authorize posting messages, replying to reviewers, resolving threads, or editing tickets. Complete whatever authoring or publication the user has authorized.

## Evidence and description

- **UI changes:** include screenshots of the affected supported UI, ideally before and after, and inspect them. For Coder setup and workspace verification, read [Browser screenshots on Coder](references/coder-screenshots.md). Do not capture a deprecated admin React view as evidence of a Ruby panel change.
- **Behavior questions:** point to the test that exercises the case. For limits, align the UI and backend and cover the exact boundary. For overlapping or multi-product trials, point to a test showing how allowances combine. If authorization or rejection is involved, include relevant failure coverage.
- **Product decisions:** link existing PM sign-off for behavior, limits, exceptions, or wording when available. Do not invent approval or start a new Slack conversation merely to fill the description. State any decision still unresolved.
- **Integrations:** if a new endpoint or billing flow could involve Mulesoft/Salesforce, establish whether those callers need changes. The historical trials flowed through Admin and did not require SFDC changes; that answer is not reusable for a different flow without checking its callers.
- **Copy and rollout:** explain how many user-facing strings change and whether delayed translations affect the rollout. English can ship at deploy while other languages arrive later; check the current localization process instead of promising a fixed delay. Address ambiguity in new wording with actual product context.
- **Generated/formatter noise:** dictionary files in `config/dict/en/web/dictionaries/*.json` enforce key ordering. Keep unrelated reordering distinguishable and explain it in the description. When committing is authorized, put dictionary ordering noise in a separate commit, such as “Apply dictionary key ordering”; do not rewrite existing history just to separate it.

Lead the description with the problem and resulting behavior. Add relevant validation and links, explaining meaningful generated changes. Report tests and screenshots actually obtained, with any material gaps; do not claim a proposed check passed.

## Review follow-through

Evaluate substantive bot findings against the code even when marked “low severity.” A low-severity ReviewBot finding can identify a real display bug. When an authorized fix is made, prepare a concise reply explaining the change with a test or screenshot. Send it only when the user has explicitly authorized replies. For ongoing feedback checks, use the `babysit-pr` skill; do not start polling as part of PR preparation.
