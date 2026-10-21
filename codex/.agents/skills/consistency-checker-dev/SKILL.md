---
name: consistency-checker-dev
description: Use whenever a user's task would add, edit, run, or verify a Figma dbt consistency checker, sometimes abbreviated CC. Check and repair only the prerequisites needed by the task, then carry out the checker work. Also use for checker development environment setup or repair.
---

# Consistency checker development

Use this skill for every task that adds, edits, runs, or verifies a Figma dbt
consistency checker, including requests phrased as working on a “CC.” Establish
readiness for each operation before performing it, then continue the user's
requested work. A request to change this skill itself does not authorize
running a checker or resuming a previously paused setup.

## Check prerequisites for the task

Find the intended `figma/figma` checkout from the user's path or current project.
Read applicable `AGENTS.md` files and the current
`dbt/consistency_checks/README.md`. Use the current CLI and repository guidance
to identify what each operation needs:

- **Read or edit files:** Begin with repository evidence. Missing Databox,
  warehouse authentication, or analytics artifacts must not block SQL or
  verification-spec edits. Complete the required validation when its own
  prerequisites are available; report any checks that remain blocked.
- **Run local tooling:** Check the runtime and dependencies needed by the
  command. Use `./consistency-check doctor` when diagnosing configuration;
  it is optional and does not verify warehouse authentication or permissions.
- **Execute a checker or synthetic verification:** Confirm the Databox
  configuration, development destination, authentication, and access needed
  by that command. In Coder, keep the OAuth-aware `databox/dbt_wrapper` ahead
  of `databox/bin` on `PATH`. Synthetic verification uses fixture inputs and
  does not require a production analytics manifest or live checker-input access.
- **Validate freshness providers:** Prepare an analytics manifest only when
  the selected validation requires it. Follow the CLI's target and freshness
  gate rules; local runs and synthetic verification do not need this artifact.
- **Use a specialized workflow:** Make its skill and the MCP connections
  needed for the requested operation available. Do not require unrelated
  integrations.

Reuse recent verified setup evidence from this session when the checkout,
runtime, configuration, and authentication have not changed. Do not reinstall a
working runtime, repeat the full smoke suite before each task, or require a
Notion sign-in for a run that only needs Snowflake.

If a prerequisite is missing or uncertain, read
[Databox setup and verification](references/setup.md) and complete the relevant
setup or repair before the dependent checker work. This includes configuring a
new Coder box, activating an existing Databox, installing missing dependencies
or wrappers, preparing the analytics manifest, and making the checker workflows
available. Continue independent work while awaiting a required sign-in or
approved grant; report the exact blocker without bypassing it. Do not stop at a
setup report when the user's requested checker task can proceed.

## Carry out the checker task

Follow the current repository's checker contract and supported CLI. Discover
existing checker SQL, metadata, and verification specifications before choosing
what to change or execute. Treat “CC” as a consistency checker when supported by
the task context, not every unrelated use of those initials.

- **Add a checker:** Use the repository's existing
  `create-consistency-check` skill. Its checker-page intake and development
  workflow govern implementation; environment setup itself needs no checker
  page. If the skill was just installed, read its `SKILL.md` directly and follow
  it for this task rather than waiting for another turn.
- **Edit a checker:** Establish the intended invariant from the request,
  existing SQL, linked checker page, and relevant repository evidence. Preserve
  supported neighboring behavior. Follow the repository's current SQL,
  metadata, verification-specification, and validation requirements.
- **Run or verify a checker:** Resolve the requested checker and use
  `consistency-check run <checker_name>` or
  `consistency-check verify <checker_name>` as requested. Follow the current
  CLI's environment-selection rules. Inspect the actual result and report
  the relevant counts.
- **Investigate an assertion failure:** Use the existing
  `investigate-consistency-check-failure` skill when the user asks to diagnose
  failed checker rows. Do not start an alert investigation merely because a
  requested local run returns violations. Dagster platform failures follow
  their own diagnostics workflow.

Treat the checkout's documentation and specialized skills as authoritative for
checker contracts. Use the narrowest relevant checks and extend verification
only when a change, failure, or unresolved concern warrants it.

Local execution must write only to the developer's Databox schema, without
Dagster or notifications. A raw SQL pass followed by failed triage enrichment
is an incomplete local run; preserve the raw result location and report the
access or configuration error. Do not change grants or substitute warehouse
relations to make a development command pass.

Finish with the requested checker outcome, relevant validation results, and any
remaining blocker. Mention setup changes only when they were needed, including
an activation command if the user's existing terminal needs one.
