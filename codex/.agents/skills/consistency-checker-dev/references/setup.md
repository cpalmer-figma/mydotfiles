# Databox setup and verification

Read this reference when the initial readiness check finds missing setup,
configuration, authentication, or tooling required by the next operation.
Read only the sections needed for that gap. File edits need no environment
setup; synthetic verification needs no analytics manifest. Reuse working
components and run relevant smoke checks after setup or repair.

## Discover and reuse

Find the checkout from the user's path, current repository, or existing saved
checkout. Verify that it contains `consistency-check`, `dbt/consistency_checks`,
and `dbt/scripts/databox`. Respect applicable `AGENTS.md` instructions.

Read the current `dbt/consistency_checks/README.md`, its `AGENTS.md`, and the
Databox setup scripts before changing the environment. The checkout's scripts,
profiles, and dependency pins are authoritative; do not copy versions or paths
from a previous machine. If freshness validation needs analytics artifacts,
also read `dbt/dbt_analytics/AGENTS.md`.

Inspect the current environment and any existing Databox runtime. Load existing
shell configuration when needed and try `./consistency-check doctor`. Reuse a
working installation, including a shared primary-checkout runtime when the
checkout's wrappers support it. Do not clone standalone `dbt_analytics` or make
an unrelated virtual environment.

## Configure Databox

Use `dbt/scripts/databox/setup.zsh` or its existing component scripts, choosing
the smallest work needed for the observed gaps. Read them first: the full
setup can install Python tooling, rewrite shell configuration, and reset a
development schema. In particular:

- Back up configuration that needs changing and preserve unrelated settings.
  Reuse the repository's username, profile, and schema conventions. Prefer an
  existing Snowflake username; a Coder owner or Git identity can suggest a
  candidate, but verify it through Snowflake before declaring setup complete.
- In Coder, use the role and authenticator selected by the current setup
  scripts, normally `SNOWFLAKE CODER` and `oauth`. If
  `FIGMA_CODER_WORKSPACE_NAME` is absent, derive it from
  `CODER_WORKSPACE_NAME` before computing the workspace-specific schema.
- An existing supported Python interpreter does not need a new pyenv
  installation. For a missing Databox runtime, use the repository's
  `setup_venv.zsh` and `setup_bins.zsh` components. The former deletes an
  existing `databox` directory: never use it just to refresh dependencies.
  Refresh existing dependencies with the repository's uv installer and
  `uv pip install --python <databox>/bin/python 'scripts/databox[dev]'` from
  `dbt/`, retaining the working runtime. Do not independently upgrade pins.
- Install or refresh command wrappers from `shared_utils/` as needed. Keep
  `databox/dbt_wrapper` ahead of `databox/bin` on `PATH`, including after
  activation. This preserves Coder OAuth refresh. Fusion is optional; its
  absence alone does not block checker development.
- Persist the non-secret `DATABOX_*` variables, Databox profile location,
  command paths, and activation entry point using the current setup scripts
  as the template. Make repeated setup reuse or update its own configuration
  rather than appending duplicate blocks. Verify in a fresh shell; existing
  Codex shell snapshots may still need explicit activation or sourcing.
- Some helpers assume the primary checkout is at
  `$FIGMA_ROOT/figma/figma`. Check the actual paths before using them. Use the
  checkout's worktree support or checkout-relative activation when needed.
- Skip destructive initial schema reset: use `SKIP_DEFER_SETUP=1` with the
  full setup and prepare the manifest separately. Do not run
  `reset_dev_schema` or `reset_project` as a setup smoke test. A local dbt test
  can create its development schema without dropping existing work.

Check Coder Snowflake authentication without printing the token:

```sh
coder external-auth access-token snowflake >/dev/null
```

Use the repository's OAuth-aware dbt wrapper or existing investigation
`scripts/sf_helper.py` for connections. Never save OAuth tokens in dotfiles,
skill files, command arguments, or logs. Confirm `current_user()`,
`current_role()`, and `current_warehouse()` through a small read-only query.
Coder OAuth is role-pinned; do not switch to another role to bypass a missing
grant. On a laptop, preserve the supported external-browser authentication.

## Make the checker workflows available

Use this section only for a workflow that needs these skills or integrations.
Reuse already-discoverable skills. If absent, locate these existing skill
directories in the checkout and link them into the user's Codex skill directory,
normally `~/.agents/skills`:

```text
.claude/plugins/create-consistency-check/skills/create-consistency-check
.claude/plugins/investigate-consistency-check-failure/skills/investigate-consistency-check-failure
```

Link the complete directories so their references and scripts remain available.
Do not overwrite a conflicting installation or edit the upstream skills.
Explain that the links follow this checkout, and suggest restarting Codex only
if the new skills do not appear.

Check the Notion, Slack, and Linear MCP configuration needed by those workflows.
Prefer the repository's current MCP wrappers and preserve unrelated client
configuration. In Coder, check Notion OAuth through
`coder external-auth access-token notion`, capturing its output: print only a
success status or the sign-in URL returned on failure, never a successful token.
If sign-in is missing, give the user that URL and continue independent setup.
Recheck after they connect; do not equate their acknowledgement with a verified
grant. A configured MCP may need reconnecting after authentication succeeds.

Do not invoke the creation or investigation skill just to install it. After
setup, return to the requested task: checker creation follows the creation
skill's checker-page intake, and alert investigation follows the investigation
skill's workflow.

## Prepare freshness validation

Use this section only when the selected validation requires manifest-based
freshness resolution under the current CLI's rules. Skip it for local runs,
synthetic verification, and validations exempt from freshness gating.

Check the current CLI's accepted analytics manifest locations and reuse a valid
production `dbt_analytics` manifest. If missing, install the analytics project's
declared packages with the Databox `dbt deps`, then run `reset_defer` from
`dbt/dbt_analytics`. This parses metadata; it does not require building models.
Set `DBT_STATE` to the resulting production artifact directory as expected by
the current wrappers. Do not build upstream or downstream models for setup.

The first analytics parse can take several minutes. Follow it to completion
and verify the resulting artifact. Do not claim freshness validation is ready
while the manifest is missing or parsing is incomplete.

## Verify capabilities

Use a small existing checker fixture, not a newly authored production checker
or a full warehouse verification suite. Choose the checks that exercise the
capabilities being set up or repaired; reuse checks already completed in this
session. Inspect the checkout's fixtures before choosing names. These commands
are examples for different capabilities, not a required sequence; run only
those relevant to the repair:

```sh
consistency-check doctor
consistency-check check
consistency-check verify test_verification_fixture_branches
consistency-check run test_success
consistency-check validate test_ai_credit_limit_active_status
```

When testing synthetic verification, confirm it executes both an expected
violation and an expected pass, with zero false positives or false negatives.
When testing a local run, confirm it writes only to the configured development
schema and completes its triage enrichment. Local runs must not invoke Dagster
or notifications.

For compile/debug support, this uses the configured Databox profile and avoids
analytics deferral; substitute the discovered checkout path:

```sh
dbt --debug compile --project-dir <checkout>/dbt/consistency_checks \
  --profile databox --target databox --no-defer --select test_success
```

For an alert investigation, follow the current investigation skill to identify
the required tables and permitted columns. Use zero-row queries for access
checks; never access `DIAGNOSTICS_SENSITIVE`.

If local execution fails during triage, inspect the current
`macros/local/create_local_triaged_results.sql` and its documented source. One
observed setup blocker was missing schema USAGE or table SELECT access for
`FIGLYTICS.TESTING.CONSISTENCY_CHECKER_TRIAGED` under `SNOWFLAKE CODER`.
Report the exact failing relation and error. Do not substitute another triage
table, change checker code, or alter grants to make a setup test pass. A raw SQL
pass followed by failed triage is an incomplete `consistency-check run`.

Once setup is ready, return to `SKILL.md` and continue the user's checker task.
When reporting setup changes or blockers, include the runtime and development
destination, available skills, and completed checks. Separate local
configuration failures from authentication and warehouse authorization
prerequisites. Include the short activation command for an existing terminal.
Keep machine-specific setup notes local rather than committing credentials,
usernames, or workspace paths into the reusable skill.
