
# Git

## Branches

- When creating a feature branch name it like "cpalmer/<descriptive-slug>",
- My branch prefix is cpalmer, even though my GitHub username is cpalmer-figma
- Prefer descriptive slugs that start with the relevant Linear ticket identifier in lowercase, such as cpalmer/bscale-123-fix-billing-preview
- To check out a PR whose branch that doesn't start with "cpalmer", use `gh pr checkout <number-or-url>`

## PRs

- Use `gh stack` for managing stacked PRs
- Do not push to branches associated with a PR without explicit user approval

# Project Context

- Assume work is being done in the context of a Linear ticket, the ticket id can be found encoded in the `hostname` of this Coder machine, use the Linear MCP to find additional context on this work
- Do not edit/write to this or any other Linear ticket unless given explicit user approval
