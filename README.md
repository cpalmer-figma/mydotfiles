# mydotfiles

My personal dotfiles, managed with [GNU Stow](https://www.gnu.org/software/stow/).

## Contents

| Package | Files | Description |
| ------- | ----- | ----------- |
| `codex` | `.codex/AGENTS.md`, `.codex/config.toml` | Shared instructions and default configuration for Codex. |
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

1. Installs missing `stow`, `tmux`, and `git` dependencies via `apt-get` on Linux or Homebrew on macOS. Install [Homebrew](https://brew.sh/) first if needed.
2. Symlinks every package into `$HOME` with `stow`.
3. Clones [TPM](https://github.com/tmux-plugins/tpm) and installs the tmux plugins.

Stow won't overwrite existing files, so move any conflicting dotfiles out of the way first.

## tmux highlights

- **Prefix:** `C-a`
- **Splits:** `prefix |` (horizontal), `prefix -` (vertical), both keeping the current directory
- **Pane navigation:** `prefix h/j/k/l` or `Alt+h/j/k/l` without the prefix
- **Resize panes:** `prefix H/J/K/L`
- **Reload config:** `prefix r`
- **Session persistence:** sessions autosave every 10 minutes and are restored on startup. Panes running Codex or Claude Code resume their own conversations (see `tmux/.tmux/scripts/`).

## Adding a new package

Create a directory named after the tool, put its dotfiles inside it at the same paths they'd have relative to `$HOME`, then re-run `./install.sh`.
