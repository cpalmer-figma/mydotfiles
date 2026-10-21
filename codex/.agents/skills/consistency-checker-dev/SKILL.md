---
name: consistency-checker-dev
description: Use whenever a user's task would add, edit, run, or verify a Figma dbt consistency checker, sometimes abbreviated CC. First confirm the Coder box has working Databox and the other prerequisites for that task, complete missing setup, then carry out the checker work. Also use for checker development environment setup or repair.
---

# Consistency checker development

Use this skill for every task that adds, edits, runs, or verifies a Figma dbt
consistency checker, including requests phrased as working on a “CC.” Establish
environment readiness first, then continue the user's requested work. A request
to change this skill itself does not authorize running a checker or resuming a
previously paused setup.

## Confirm the environment first

Find the intended `figma/figma` checkout from the user's path or current project.
Read applicable `AGENTS.md` files and the current
`dbt/consistency_checks/README.md`. Check the existing setup before editing
checker SQL or running a checker:

- Databox exists and has the repository's required Python dependencies.
- The active configuration has the expected Snowflake user, role, warehouse,
  and development schema. The OAuth-aware `databox/dbt_wrapper` takes precedence
  over `databox/bin` on `PATH`.
- `./consistency-check doctor` reports ready. It checks local configuration,
  not the warehouse connection or permissions: also verify working
  authentication and the access needed by this task.
- Freshness validation has a usable production analytics manifest. Required
  checker skills and any MCP connections needed by this task are available.

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

- **Add a checker:** After setup, use the repository's existing
  `create-consistency-check` skill. Its checker-page intake and development
  workflow govern implementation; environment setup itself needs no checker
  page. If the skill was just installed, read its `SKILL.md` directly and follow
  it for this task rather than waiting for another turn.
- **Edit a checker:** Establish the intended invariant from the request,
  existing SQL, linked checker page, and relevant repository evidence. Preserve
  supported neighboring behavior. Update the mirrored synthetic verification
  specification where the behavior changes, then run the relevant validation
  and verification. Follow any stricter applicable repository requirements.
- **Run or verify a checker:** Resolve the requested checker and use
  `consistency-check run <checker_name>` or
  `consistency-check verify <checker_name>` as requested. Production inputs are
  the default for local `run`; staging requires explicit selection and checker
  eligibility. Inspect the actual result and report the relevant counts.
- **Investigate an assertion failure:** Once setup is ready, use the existing
  `investigate-consistency-check-failure` skill when the user asks to diagnose
  failed checker rows. Do not start an alert investigation merely because a
  requested local run returns violations. Dagster platform failures follow
  their own diagnostics workflow.

Use literal `table_relation('<schema>', '<relation>')` inputs and the checker
project's current conventions; do not introduce `ref()` or `source()` calls.
New or behaviorally changed checkers need meaningful synthetic passing and
violating examples. Use the narrowest relevant checks and extend verification
only when a change, failure, or unresolved concern warrants it.

Local execution must write only to the developer's Databox schema, without
Dagster or notifications. A raw SQL pass followed by failed triage enrichment
is an incomplete local run; preserve the raw result location and report the
access or configuration error. Do not change grants or substitute warehouse
relations to make a development command pass.

Finish with the requested checker outcome, relevant validation results, and any
remaining blocker. Mention setup changes only when they were needed, including
an activation command if the user's existing terminal needs one.
