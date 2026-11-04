---
name: figma-sinatra-dev
description: Implement or fix Figma monorepo Ruby/Sorbet, Sinatra backend, and internal AdminApp features, including Ruby panels and their Open Truss components. Use before choosing an admin implementation or changing billing procedures; not for unrelated Ruby projects or Figma design-file editing.
---

# Figma Sinatra development

Use the intended `figma/figma` checkout and its applicable `AGENTS.md` files. Follow current repository guidance and inspect the owning code and tooling before applying version-sensitive conventions or product limits. Paths below are relative to that checkout.

Load only the references needed by the change:

- **Admin UI, forms, actions, or Open Truss:** read [AdminApp](references/admin-app.md) before deciding which surface to edit. Features belong in Ruby panels, not deprecated React views or new admin API routes. Also follow the checkout's `.claude/plugins/admin-app-tooling/skills/admin-app-panels/SKILL.md` when available; the panels directory's current instructions govern its use.
- **Backend procedures, authorization, billing, or non-admin routes:** read [Sinatra backend](references/sinatra.md). For admin work, load the AdminApp reference first so the endpoint guidance is not misapplied.
- **Ruby implementation and tests:** read [Ruby and Sorbet](references/ruby.md) for record cardinality, strict date validation, duration types, and local coding conventions.

Before implementing, identify the procedure, callers, relevant UI, and tests. For a billing mutation, establish actor authorization, lock order, business limits, date semantics, persisted values, and billing-log behavior from current code. Keep display-label changes separate from stored-value changes.

Validate the behavior that could regress: authorization before eligibility, no writes on rejection, exact date/limit boundaries, and display labels versus serialized values where relevant. Use the checkout's supported test, generation, and lint commands. Commit required generated artifacts together with their sources when committing is in scope.
