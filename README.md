# mydotfiles

My personal dotfiles, managed with [GNU Stow](https://www.gnu.org/software/stow/).

## Contents

| Package | Files | Description |
| ------- | ----- | ----------- |
| `codex` | `.codex/AGENTS.md`, `.codex/config.toml`, `.agents/skills/` | Shared instructions, default settings, and personal skills for Codex. `config.toml`'s settings are written into `~/.codex/config.toml` rather than linked (see below). |
| `git`   | `.gitconfig` | User identity and a few aliases (`st`, `co`, `br`, `pullff`). |
| `tmux`  | `.tmux.conf`, `.tmux/scripts/` | tmux config: `C-a` prefix, vim-style pane navigation, custom status bar, and session persistence via tmux-resurrect/continuum. |

Each top-level directory is a Stow package whose contents mirror their location in `$HOME`.

## Install

```sh
git clone https://github.com/cpalmer-figma/mydotfiles.git ~/mydotfiles
cd ~/mydotfiles
./install.sh
```

The installer:

1. Installs missing `stow`, `tmux`, `git`, and `gh` dependencies via `apt-get` on Linux or Homebrew on macOS. Install [Homebrew](https://brew.sh/) first if needed.
2. Installs the [GitHub CLI stack extension](https://github.com/github/gh-stack) if it isn't already installed.
3. Symlinks package files into `$HOME` with `stow --no-folding`, so apps that write into a directory such as `~/.codex` don't write into this repo. Each Codex skill directory is linked separately because Codex skips symlinked `SKILL.md` files.
4. Copies `codex/.codex/config.toml` into a `# BEGIN mydotfiles` / `# END mydotfiles` block at the top of `~/.codex/config.toml`, replacing that block on each run and preserving the rest. The repo config must contain only top-level settings, such as `model`. Existing copies of those settings outside the block are removed to avoid duplicate TOML keys. Codex rewrites that file when it saves a setting, which would replace a symlink, so stow skips it (`codex/.stow-local-ignore`). This repo's values win, so change them here rather than on a machine.
5. Clones [TPM](https://github.com/tmux-plugins/tpm) and installs the tmux plugins.

Stow won't overwrite existing files, so move any conflicting dotfiles out of the way first.

Earlier versions of the installer linked `~/.codex` itself into this repo, so Codex kept its sessions and other state here. The installer moves that directory back to `~/.codex` and restores this repo's files.

## Codex skills

`consistency-checker-dev` applies whenever a task would add, edit, run, or verify a Figma consistency checker, including requests abbreviated as “CC.” It checks and repairs only the prerequisites needed by each operation, then continues the checker work. File edits can proceed without Databox, and synthetic verification does not need a production analytics manifest. A working environment is reused. You can also invoke it explicitly as `$consistency-checker-dev`.

Each skill directory is symlinked under `~/.agents/skills`. After pulling new skills, rerun `./install.sh`. The installer migrates earlier file links to directory links and preserves unrelated files and skills; conflicting files must be moved aside before rerunning. Restart Codex if a new skill does not appear in the skill picker.

## tmux highlights

- **Prefix:** `C-a`
- **Splits:** `prefix |` (horizontal), `prefix -` (vertical), both keeping the current directory
- **Pane navigation:** `prefix h/j/k/l` or `Alt+h/j/k/l` without the prefix
- **Resize panes:** `prefix H/J/K/L`
- **Reload config:** `prefix r`
- **Session persistence:** sessions autosave every 10 minutes and are restored on startup. Panes running Codex or Claude Code resume their own conversations (see `tmux/.tmux/scripts/`).

## Adding a new package

Create a directory named after the tool, put its dotfiles inside it at the same paths they'd have relative to `$HOME`, then re-run `./install.sh`.
