# Sinatra backend changes

## Lessons from code review

**Authorize before eligibility checks, lookups, or locking performed by the procedure.** Otherwise an unauthorized caller can learn whether a trial is expired, overlapping, or at a limit from the rejection message. In the reviewed extension procedure, `check_admin_actor(actor_id:)` moved to the first line, ahead of `Plan.for_org(...).sole.with_lock`.

Test the ordering with a non-employee trying to extend an **expired** trial: expect `Errors::HttpPermissionError`, not the ongoing-trial eligibility rejection. Prove rejected calls make no writes.

**Include the rejected value in input errors** so failures can be diagnosed, for example `api_reject "Invalid trial end date: #{new_trial_end_date}"`. Assert the full message in the regression test.

## Observed billing conventions

These are local conventions, not requirements across Sinatra. Check nearby current code before applying them.

- Lock the parent first, then the child: `Plan.for_org(org_id).sole.with_lock`, then `billing_trial.with_lock`. Validate inside the locks. The parent lock serializes concurrent create/extend operations.
- Mutations write `BillingLog.log_billing_event!` with a dedicated `BillingLog::EventType`, recording previous and new values in `metadata`.
- Use named constants such as `BillingTrial::MAX_PRODUCT_TRIAL_DURATION_DAYS` for limits. Return relevant limits to the UI rather than maintaining frontend copies. Read the current constant and product requirements; do not copy an old numeric limit.
- For the trial end-date convention in these changes, `date.in_time_zone("UTC") + 1.day` means access lasts through the selected day. Confirm the same semantics apply before using this for another field.
- Compare `LicenseType` enum values directly, e.g. `license_type == LicenseType::FIGMAKE`. Stored `product_license_types` are strings, so compare them to `LicenseType::FIGMAKE.serialize.to_s`.
- A display rename should preserve stored identifiers unless a data migration is requested. The Make-to-AI change kept `"figmake"` in the database and billing logs; test the new label and old serialized value together.

Observed errors: `::Errors::HttpRejectError` (400) for invalid input/state, `::Errors::HttpConflictError` (409) for conflicts with records/limits, and `Errors::HttpPermissionError` from actor checks. Controllers use `api_reject "..."` and `api_require_found(record, "Trial not found")` (404). Match the current procedure's contract; panel flash errors are covered in [AdminApp](admin-app.md).

## Non-admin endpoint and generated artifacts

This is **not** a recipe to add admin routes. Build admin features as panels using [AdminApp](admin-app.md).

For an appropriate new non-admin route, inspect current equivalents and generators:

- Typed routes v2 use `typed_post` with `request:`/`response:` schema classes, `require_okta_groups:`, and `rollout: TypedRoute::RolloutState::Complete`. Older code uses `typed_post_route`; do not copy that merely because it is nearby.
- Schemas live under `sinatra/lib/typed_route/schemas/...`, with declarations such as `field :trial_id, string, required: true`. Include generated RBI files from `sinatra/sorbet/rbi/dsl/...`.
- Ownership entries in `sinatra/config/ownership/<team>.yml` include `priority` and the `all_queries_consistency_tagged: strict` guardrail. Generated outputs can include per-environment Envoy configs, `k8s/services/sinatra/waypoint_envoyfilter.yaml`, and `sinatra/generated_monitors/<team>/monitors.tf` (Spacelift runs a Terraform plan). Use the current generator to establish the actual output set; do not edit unrelated generated files by rote.
- Add new billing files to the respective `maintainers.yml` under `sinatra/lib/billing/` and `sinatra/test/libs/billing/` as applicable.
- When an admin JSON contract gains a protobuf-backed field, update the `.proto` and include regenerated `_pb.rb` and `_pb.rbi` files.

## Tests and audit discoverability

Both Minitest `def test_...` and `describe`/`it` (`SpecBase`) are used. Stubbing uses `Spy.on_instance_method(...)`; an Okta test stubs `get_all_okta_groups`. Pure-logic allowance tests use unsaved `BillingTrial.new(...)` records and return `true` from `setup_should_skip_persistent_data_reset?`. Use that optimization only for tests that need no persisted data.

`# SOX-relevant: ...` leading comments identify audit-relevant methods/classes, including admin routes and panels. **New methods do not require the tag.** Consider it for relevant billing mutations when consistent with current audit guidance; it is a discoverability aid, not proof of audit compliance. [Original audit discussion](https://figma.slack.com/archives/C04B79GSQLX/p1791475001331069).
