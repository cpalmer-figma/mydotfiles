# AdminApp changes

## Choose the supported surface

Build internal admin features as `AdminApp::Panels` under `sinatra/lib/admin_app/panels/`. The React views under `web/js/admin_app/views/` are deprecated: do not add features, fixes, copy changes, or label tweaks there merely because the old feature still exists. Shared Open Truss components under `web/js/admin_app/open_truss/` still render the Ruby panels and can be changed.

Do not add a new admin API route for a panel action. Read `go/build-admin` and the checkout's panel guidance. `sinatra/linters/admin/no_new_admin_routes.rb` reports “New admin routes are not allowed. See: go/build-admin”. An inline suppression in an old route is not a precedent to copy. The extension panel called its procedure directly; an observed route was used by the deprecated React UI.

Follow the target checkout's panel instructions, including its referral to `.claude/plugins/admin-app-tooling/skills/admin-app-panels/SKILL.md` when available.

## Panel actions and inputs

An action can call a procedure directly and refresh its parent:

```ruby
action :extend_trial do
  extend_org_trial!(
    actor_id: current_user.id,
    billing_trial: billing_trial,
    extension_days: extension_days,
  )
  refresh_parent(flash: "Extended trial for #{org.name}")
end
```

Raise `Errors::Http422Error` with a useful message to reject a panel action; the message appears as a flash. Keep the procedure's authorization and validation intact.

Multiselect options can be `{ value:, label: }` hashes. For example, an enum's serialized value can remain `"figmake"` while its displayed label is `"AI"`. Check for an existing shared label helper before duplicating a mapping in a second panel.

Keep a `date_input!`'s `min:` and `max:` aligned with the procedure's enforced limit. Test the exact boundary day; an old React form accepted a day beyond the backend's limit.

## Regression checks from review

- Check labels both inside an open dropdown and in the collapsed selection summary. In #994398, `MultiselectInput` built the summary from stored values instead of labels; the Ruby panel alone could not fix that shared component bug.
- If changing the shared component, add a frontend regression test for the summary behavior.
- Panel tests subclass `AdminApp::SpecBase`: render, inspect the inputs, submit the form, and check persisted state. Assert both the displayed label and unchanged serialized value for a rename.

```ruby
render(panel_class, panel_inputs:, context:) do
  input = T.must(find_input("MultiselectInput", :product_license_types))
  options = T.must(input.props)[:inputProps][:options]
  assert_includes options, { value: LicenseType::FIGMAKE.serialize.to_s, label: "AI" }

  submit_form(:create, valid_form_data.merge(product_license_types: [LicenseType::FIGMAKE.serialize]))
end
```
