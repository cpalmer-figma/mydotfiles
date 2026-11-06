# mydotfiles

My personal dotfiles, managed with [GNU Stow](https://www.gnu.org/software/stow/).

## Contents

| Package | Files | Description |
| ------- | ----- | ----------- |
| `codex` | `.codex/AGENTS.md`, `.codex/config.toml`, `.agents/skills/` | Shared instructions, default settings, and personal skills for Codex. `config.toml`'s settings are written into `~/.codex/config.toml` rather than linked (see below). |
| `git`   | `.gitconfig` | User identity, performance settings, and a few aliases (`st`, `co`, `br`, `pullff`). |
| `tmux`  | `.tmux.conf`, `.tmux/scripts/` | tmux config: `C-a` prefix, vim-style pane navigation, custom status bar, and session persistence via tmux-resurrect/continuum. |
| `zsh`   | `.zshrc` (sourced from a local file) | `wait-minifig` helper with the active profile, elapsed time, and ready counts. Requires `jq` and a checkout at `~/figma/figma`. |

Each top-level directory is a Stow package whose contents mirror their location in `$HOME`.

## Install

```sh
git clone https://github.com/cpalmer-figma/mydotfiles.git ~/mydotfiles
cd ~/mydotfiles
./install.sh
```

The installer:

1. Installs missing `stow`, `tmux`, `git`, and `gh` dependencies via `apt-get` on Linux or Homebrew on macOS. Install [Homebrew](https://brew.sh/) first if needed.
2. Applies and verifies the Codex defaults before Stow, skill linking, or plugin setup can fail. It copies `codex/.codex/config.toml` into a `# BEGIN mydotfiles` / `# END mydotfiles` block at the top of `~/.codex/config.toml`, replacing that block on each run and preserving the rest. The repo config must contain only top-level settings, such as `model`. Existing copies of those settings outside the block are removed to avoid duplicate TOML keys. Codex rewrites that file when it saves a setting, which would replace a symlink, so stow skips it (`codex/.stow-local-ignore`). This repo's values win, so change them here rather than on a machine.
3. Keeps `~/.zshrc` as a regular local file and adds a single `source` line at the top pointing to this checkout's `zsh/.zshrc`. Local settings (including Databox additions) stay below it and can override shared defaults. Reruns recognize that exact source line and leave the file unchanged. Symlinks, directories, and duplicate shared source lines are reported as errors and left untouched; old symlinks are no longer migrated. Stow skips `.zshrc` (`zsh/.stow-local-ignore`) and symlinks the other package files with `--no-folding`. Each Codex skill directory is linked separately because Codex skips symlinked `SKILL.md` files.
4. Installs the [GitHub CLI stack extension](https://github.com/github/gh-stack) if it isn't already installed.
5. Clones [TPM](https://github.com/tmux-plugins/tpm) and installs the tmux plugins.

The installer prints the verified Codex defaults and reports whether they were installed if a later step fails. A successful run ends with `Dotfiles installation complete.`

When `~/figma/figma` exists, the installer also limits its `origin` fetch rules to `master` and `cpalmer/*`.

Stow won't overwrite existing files, so move any conflicting dotfiles out of the way first. The local `.zshrc` is managed separately as described above. Shared Zsh updates take effect in new shells or after `source ~/.zshrc`, without rerunning installation.

`~/.codex` must be a real directory. Unexpected layouts are reported as errors rather than migrated.

Run `python3 test-install.py` to check installation in temporary home directories using real Stow and stubbed network/plugin operations.

## Codex skills

`babysit-pr` helps work through a PR's feedback in an ongoing chat. Invoke it with `$babysit-pr` and a PR URL to see existing comments, relevant code, assessments, and proposed diffs. Discuss the recommendations, then ask “any updates?” to fetch and show changes since the previous check, including new feedback, commits, and resolved or reopened threads. Checks happen only on request. Babysitting does not authorize code edits or GitHub actions.

`consistency-checker-dev` applies whenever a task would add, edit, run, or verify a Figma consistency checker, including requests abbreviated as “CC.” It checks and repairs only the prerequisites needed by each operation, then continues the checker work. File edits can proceed without Databox, and synthetic verification does not need a production analytics manifest. A working environment is reused. You can also invoke it explicitly as `$consistency-checker-dev`.

`figma-sinatra-dev` applies to Figma Ruby/Sorbet, Sinatra backend, and internal AdminApp changes. It covers Ruby panels, authorization order, billing mutations, strict date handling, and tests, with separate references loaded as needed.

`figma-pr-prep` applies when preparing a Figma PR or writing its description. It covers screenshot evidence (including the Coder browser-testing entry point), product sign-off, boundary coverage, translation timing, and dictionary reordering. Ongoing feedback checks stay in `babysit-pr`.

Each skill directory is symlinked under `~/.agents/skills`. After pulling new skills, rerun `./install.sh`. Existing links to the matching skill directories are reused; conflicting files, directories, or links are reported as errors and must be corrected before rerunning. Restart Codex if a new skill does not appear in the skill picker.

## tmux highlights

- **Prefix:** `C-a`
- **Splits:** `prefix |` (horizontal), `prefix -` (vertical), both keeping the current directory
- **Pane navigation:** `prefix h/j/k/l` or `Alt+h/j/k/l` without the prefix
- **Resize panes:** `prefix H/J/K/L`
- **Reload config:** `prefix r`
- **Session persistence:** sessions autosave every 10 minutes and are restored on startup. Panes running Codex or Claude Code resume their own conversations (see `tmux/.tmux/scripts/`).

## Adding a new package

Create a directory named after the tool, put its dotfiles inside it at the same paths they'd have relative to `$HOME`, then re-run `./install.sh`.
