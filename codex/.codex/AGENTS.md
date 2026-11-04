
## Branch Naming

- When creating a feature branch, use cpalmer/<descriptive-slug>.
- My branch prefix is cpalmer, even though my GitHub username is cpalmer-figma.
- Prefer descriptive slugs that start with the relevant Linear ticket identifier in lowercase, such as cpalmer/bscale-123-fix-billing-preview
- Follow repository rules for special branches, such as reverts.

## Fetching Figma Branches

- The Figma monorepo's automatic fetches are restricted to `master` and `cpalmer/*`.
- To check out a PR whose branch has another prefix, use `gh pr checkout <number-or-url>`. It fetches the PR branch directly; a generic `git fetch` will not discover it under the restricted fetch rules.
- Keep the fetch restrictions in place rather than enabling fetches of all branches.

## Linear

- Find and read the Linear ticket encoded in the machine's hostname to locate additional context for work
- Always consult the user and obtain explicit approval before editing or changing Linear tickets in any way

