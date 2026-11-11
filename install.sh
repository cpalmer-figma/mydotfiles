#!/usr/bin/env bash
set -e

codex_defaults_installed=no
trap 'status=$?; if [ "$status" -ne 0 ]; then
  echo "Dotfiles installation incomplete (exit $status). Codex defaults installed: $codex_defaults_installed. Resolve the error above and rerun ./install.sh." >&2
fi' EXIT

cd "$(dirname "$0")"

missing=()
for dependency in stow tmux git gh curl; do
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
# Reuse uv from PATH or its usual user installation before bootstrapping it.
if ! command -v uv >/dev/null 2>&1 && [ -x "$HOME/.local/bin/uv" ]; then
  PATH="$HOME/.local/bin:$PATH"
  export PATH
fi
if ! command -v uv >/dev/null 2>&1; then
  uv_installer="$(mktemp)"
  if ! curl -LsSf https://astral.sh/uv/install.sh -o "$uv_installer" ||
     ! UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 sh "$uv_installer"; then
    rm -f "$uv_installer"
    echo "Cannot install uv. Resolve the error above and rerun ./install.sh." >&2
    exit 1
  fi
  rm -f "$uv_installer"
  PATH="$HOME/.local/bin:$PATH"
  export PATH
fi
# uv manages and caches the script's environment from its inline dependencies.
mkdir -p "$HOME/.codex"
uv run --no-project --script install-codex-config.py "$codex_package/config.toml" "$codex_config"
codex_defaults_installed=yes
echo "Verified Codex defaults in $codex_config:"
cat "$codex_package/config.toml"

# Configure the project entry so its hosted URL cannot merge with stdio settings.
if [ "${FIGMA_CODER_INSTANCE_TYPE:-}" = devbox ] && [ -e "$HOME/figma/figma/.git" ]; then
  uv run --no-project --script install-codex-config.py --coder-statsig "$HOME/figma/figma"
fi

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

# Configure the Figma checkout and select the Billing service profile.
if [ -e "$HOME/figma/figma/.git" ]; then
  git -C "$HOME/figma/figma" remote set-branches origin master 'cpalmer/*'
  (
    cd "$HOME/figma/figma"
    # Coder runs dotfiles alongside Minifig startup. Retry only a refused
    # connection; profile/configuration errors should still fail immediately.
    minifig_deadline=$((SECONDS + 120))
    while true; do
      if minifig_output=$(./minifig profile set team/billing --wait 2>&1); then
        printf '%s\n' "$minifig_output"
        break
      else
        minifig_status=$?
      fi
      printf '%s\n' "$minifig_output" >&2
      case "$minifig_output" in
        *"Failed to connect to Minifig server:"*"connect: connection refused"*) ;;
        *) exit "$minifig_status" ;;
      esac
      minifig_remaining=$((minifig_deadline - SECONDS))
      if ((minifig_remaining <= 0)); then
        echo "Timed out after 120 seconds waiting for Minifig to accept connections. Start Minifig and rerun ./install.sh." >&2
        exit "$minifig_status"
      fi
      minifig_delay=5
      if ((minifig_remaining < minifig_delay)); then
        minifig_delay=$minifig_remaining
      fi
      echo "Minifig is still starting; retrying in $minifig_delay seconds..." >&2
      sleep "$minifig_delay"
    done
  )
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
