#!/usr/bin/env bash
set -e

codex_defaults_installed=no
trap 'status=$?; if [ "$status" -ne 0 ]; then
  echo "Dotfiles installation incomplete (exit $status). Codex defaults installed: $codex_defaults_installed. Resolve the error above and rerun ./install.sh." >&2
fi' EXIT

cd "$(dirname "$0")"

missing=()
for dependency in stow tmux git gh python3; do
  command -v "$dependency" >/dev/null 2>&1 || missing+=("$dependency")
done

if ((${#missing[@]})); then
  case "$(uname -s)" in
    Darwin)
      if ! command -v brew >/dev/null 2>&1; then
        for brew_dir in /opt/homebrew/bin /usr/local/bin; do
          if [ -x "$brew_dir/brew" ]; then
            PATH="$brew_dir:$PATH"
            export PATH
            break
          fi
        done
      fi
      if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew is required to install: ${missing[*]}. Install it from https://brew.sh/ and rerun this script." >&2
        exit 1
      fi
      brew install "${missing[@]}"
      ;;
    Linux)
      if ! command -v apt-get >/dev/null 2>&1; then
        echo "apt-get is required to install: ${missing[*]}. Install them manually and rerun this script." >&2
        exit 1
      fi
      sudo apt-get update
      sudo apt-get install -y "${missing[@]}"
      ;;
    *)
      echo "Unsupported operating system. Install ${missing[*]} manually and rerun this script." >&2
      exit 1
      ;;
  esac
fi

codex_package="codex/.codex"
codex_config="$HOME/.codex/config.toml"

if [ -L "$HOME/.codex" ] || { [ -e "$HOME/.codex" ] && [ ! -d "$HOME/.codex" ]; }; then
  echo "Cannot configure $HOME/.codex: expected a real directory. Correct it and rerun this script." >&2
  exit 1
fi

# Codex rewrites ~/.codex/config.toml when it saves settings, which would
# replace a link, so stow skips that file (see codex/.stow-local-ignore).
# Use a formatting-preserving TOML editor, isolated when it isn't available.
codex_python=python3
if ! "$codex_python" -c 'import tomlkit' >/dev/null 2>&1; then
  codex_venv="${XDG_CACHE_HOME:-$HOME/.cache}/mydotfiles/toml-editor"
  if [ ! -x "$codex_venv/bin/python" ]; then
    if ! python3 -m venv "$codex_venv"; then
      echo "Cannot create the TOML editor environment. On Debian/Ubuntu, install python3-venv and rerun ./install.sh." >&2
      exit 1
    fi
  fi
  codex_python="$codex_venv/bin/python"
  if ! "$codex_python" -c 'import tomlkit' >/dev/null 2>&1; then
    "$codex_python" -m pip install 'tomlkit==0.15.1'
  fi
fi
mkdir -p "$HOME/.codex"
"$codex_python" install-codex-config.py "$codex_package/config.toml" "$codex_config"
codex_defaults_installed=yes
echo "Verified Codex defaults in $codex_config:"
cat "$codex_package/config.toml"

# Tools such as Databox edit ~/.zshrc. Keep it local and source the shared
# configuration first, allowing machine-specific settings to override it.
zshrc="$HOME/.zshrc"
zsh_source="$(pwd -P)/zsh/.zshrc"
zsh_existing="$zshrc"
if [ -L "$zshrc" ] || { [ -e "$zshrc" ] && [ ! -f "$zshrc" ]; }; then
  echo "Cannot configure $zshrc: expected a regular local file, not a symlink or directory. Correct it and rerun this script." >&2
  exit 1
elif [ ! -e "$zshrc" ]; then
  zsh_existing=/dev/null
fi

# Bash's %q also produces valid Zsh quoting for paths with spaces or quotes.
printf -v zsh_source_line 'source %q' "$zsh_source"
if grep -Fxq -- "$zsh_source_line" "$zsh_existing"; then
  if [ "$(grep -Fxc -- "$zsh_source_line" "$zsh_existing")" -ne 1 ]; then
    echo "Cannot configure $zshrc: duplicate shared source lines. Remove the duplicates and rerun this script." >&2
    exit 1
  fi
else
  zsh_merged="$(mktemp "$HOME/.zshrc.XXXXXX")"
  {
    printf '%s\n' "$zsh_source_line"
    cat "$zsh_existing"
  } > "$zsh_merged"
  # Write in place to keep local permissions.
  cat "$zsh_merged" > "$zshrc"
  rm "$zsh_merged"
fi
echo "Configured $zshrc to source $zsh_source."

for package in */; do
  [ -d "$package" ] || continue
  # Link each file rather than whole directories, so apps that write into a
  # directory such as ~/.codex don't write into this repository.
  stow --restow --no-folding -t "$HOME" "${package%/}"
done

# Fetch only master and my branches in the Figma monorepo.
if [ -e "$HOME/figma/figma/.git" ]; then
  git -C "$HOME/figma/figma" remote set-branches origin master 'cpalmer/*'
fi

# Codex follows skill-directory links but skips symlinked SKILL.md files.
mkdir -p "$HOME/.agents/skills"
for skill in "$(pwd -P)/codex/.agents/skills/"*/; do
  [ -f "$skill/SKILL.md" ] || continue
  skill="${skill%/}"
  target="$HOME/.agents/skills/${skill##*/}"
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$skill" ]; then
    continue
  fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    echo "Cannot link skill: $target already exists. Move it aside and rerun this script." >&2
    exit 1
  fi
  ln -s "$skill" "$target"
done

extensions="$(gh extension list)"
if ! printf '%s\n' "$extensions" | grep -qE '^gh stack[[:space:]]'; then
  gh extension install github/gh-stack
fi

# Keep downloaded plugins in the home directory, outside this repository.
mkdir -p "$HOME/.tmux/plugins"

tpm_dir="$HOME/.tmux/plugins/tpm"
if [ ! -e "$tpm_dir" ] && [ ! -L "$tpm_dir" ]; then
  git clone https://github.com/tmux-plugins/tpm.git "$tpm_dir"
fi

"$tpm_dir/bin/install_plugins"

echo "Dotfiles installation complete."
