# Ruby, Rails, and Sorbet

## Lessons from code review

**Express exact cardinality.** Use `.sole` when exactly one row must exist, e.g. `Plan.for_org(org_id).sole.with_lock { ... }`. Unlike `first!`, it rejects multiple rows as well as no rows (`ActiveRecord::SoleRecordExceeded` / `ActiveRecord::RecordNotFound`). Prefer `find_sole_by` over a `find_by` lookup when exact cardinality is the intended invariant; do not change optional or intentionally multi-row lookups indiscriminately.

**Validate strict dates once and explain library leniency.** `Date.iso8601` accepts timestamps and other ISO forms. When the input contract is exactly `YYYY-MM-DD`, parse and round-trip in one block:

```ruby
end_date =
  begin
    parsed_date = Date.iso8601(new_trial_end_date)
    # Date.iso8601 accepts timestamps; this API accepts only YYYY-MM-DD.
    unless new_trial_end_date.length == 10 && parsed_date.iso8601 == new_trial_end_date
      raise Date::Error
    end
    parsed_date
  rescue Date::Error
    api_reject "Invalid trial end date: #{new_trial_end_date}"
  end
```

This example assumes the request schema already requires a string. Keep the reason for an apparently redundant check visible. Test accepted dates, timestamps, alternate forms, and invalid dates according to the actual input contract.

**Build optional hash fields with `merge({...}.compact)`** when nil means omission, rather than mutating a response after construction:

```ruby
as_json.merge(
  {
    status: status.serialize,
    max_product_trial_duration_days: (MAX_PRODUCT_TRIAL_DURATION_DAYS if is_product_trial?),
  }.compact,
)
```

A modifier `if` as a hash value needs parentheses. `.compact` drops every nil in that literal; do not use it when explicit nulls carry meaning.

**Represent time spans as `ActiveSupport::Duration`.** Subtracting two `TimeWithZone` values returns a float of seconds; `.seconds` converts it back to a duration. A duration adds directly to a `TimeWithZone`, and a Sorbet return type records the intent. For example:

```ruby
[BillingTrial::MAX_PRODUCT_TRIAL_DURATION_DAYS.days.to_f - used_duration, 0.0].max.seconds
```

Use `.returns(ActiveSupport::Duration)` for that contract. Compare against `20.days` or `0.seconds` in tests, and assert the instance type when the return type is part of the regression.

## Observed local conventions

These are local conventions, not repository-wide rules. Prefer current scoped instructions and surrounding code.

- New strict files start with `# typed: strict` and `# frozen_string_literal: true`. Classes extend `T::Sig`; methods have signatures. Long signatures use multiline `sig do ... end` with parameters on separate lines.
- Sorbet types hash lookups as nilable even for `Hash.new(0.0)`. For that pattern, declare `T.let(Hash.new(0.0), T::Hash[String, Float])` and use `T.must(...)` when the invariant justifies it.
- Use keyword arguments and shorthand such as `org_id:` when the local name matches.
- Mutating or raising procedure methods in these examples end in `!`, e.g. `extend_product_trial!` and `check_creation!`. Private procedure helpers use `private def`.
- Spell out block variables (`license_type`, not `lt`); use `&.` for nilable columns where appropriate.
- Separate plain-data construction from queries for testability: accept records in `initialize`, with a `self.for_org` query factory, as in `Billing::ProductTrialAllowance`.
- Name tests after behavior. Use `assert_no_difference -> { ... }` / `assert_no_changes -> { ... }` for rejected mutations, and capture `error = assert_raises(...)` to assert the exact message.
