#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

missing=()
for dependency in stow tmux git gh; do
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

extensions="$(gh extension list)"
if ! printf '%s\n' "$extensions" | grep -qE '^gh stack[[:space:]]'; then
  gh extension install github/gh-stack
fi

# Keep downloaded plugins in the home directory, outside this repository.
mkdir -p "$HOME/.tmux/plugins"

codex_package="codex/.codex"
codex_config="$HOME/.codex/config.toml"

# BEGIN LEGACY MIGRATION: remove this entire block once all machines have
# upgraded from the installer that linked ~/.codex as a whole directory.
# Keep the variables above and the stow/config-merge steps below; those are
# part of normal installation, including fresh installs and future reruns.
#
# Earlier installs linked ~/.codex itself into this repository, so Codex kept
# its state here. Move the directory back to ~/.codex, then restore this
# repository's files and drop the moved copies of them so stow can link them.
# Codex's own config.toml stays in ~/.codex.
if [ -L "$HOME/.codex" ] && [ "$(cd "$HOME/.codex" && pwd -P)" = "$(pwd -P)/$codex_package" ]; then
  rm "$HOME/.codex"
  mv "$codex_package" "$HOME/.codex"
  git checkout -- "$codex_package"
  git ls-files "$codex_package" | while IFS= read -r file; do
    copy="$HOME/${file#codex/}"
    # A copy with changes of its own is kept, and stow reports the conflict.
    if [ "$file" != "$codex_package/config.toml" ] && cmp -s "$file" "$copy"; then
      rm "$copy"
    fi
  done
  # Codex saved some paths through the old link.
  if [ -f "$codex_config" ]; then
    rewritten="$(mktemp "$codex_config.XXXXXX")"
    sed "s|$(pwd -P)/$codex_package/|$HOME/.codex/|g" "$codex_config" > "$rewritten"
    mv "$rewritten" "$codex_config"
  fi
fi
# END LEGACY MIGRATION

for package in */; do
  [ -d "$package" ] || continue
  # Link each file rather than whole directories, so apps that write into a
  # directory such as ~/.codex don't write into this repository. Restowing
  # also replaces directory links made by earlier installs.
  stow --restow --no-folding -t "$HOME" "${package%/}"
done

# Codex follows skill-directory links but skips symlinked SKILL.md files.
mkdir -p "$HOME/.agents/skills"
for skill in "$(pwd -P)/codex/.agents/skills/"*/; do
  [ -f "$skill/SKILL.md" ] || continue
  skill="${skill%/}"
  target="$HOME/.agents/skills/${skill##*/}"
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$skill" ]; then
    continue
  fi
  # Migrate old file links. Stow removes only links to this skill, then
  # remove empty directories while preserving any unrelated files.
  if [ -d "$target" ] && [ ! -L "$target" ]; then
    stow --delete -d "${skill%/*}" -t "$target" "${skill##*/}"
    find "$target" -depth -type d -empty -delete
    if [ -e "$target" ]; then
      echo "Cannot migrate skill: $target contains other files. Move it aside and rerun this script." >&2
      exit 1
    fi
  fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    echo "Cannot link skill: $target already exists. Move it aside and rerun this script." >&2
    exit 1
  fi
  ln -s "$skill" "$target"
done

# Codex rewrites ~/.codex/config.toml when it saves settings, which would
# replace a link, so stow skips that file (see codex/.stow-local-ignore).
# Keep this repository's top-level settings in a marked block at the top.
codex_existing="$codex_config"
[ -e "$codex_existing" ] || codex_existing=/dev/null
merged="$(mktemp "$codex_config.XXXXXX")"
{
  echo '# BEGIN mydotfiles — edit in the dotfiles repo'
  cat "$codex_package/config.toml"
  echo '# END mydotfiles'
  awk '
    # Collect managed keys to remove old copies outside the marked block.
    FILENAME == ARGV[1] {
      if ($0 ~ /^[ \t]*[A-Za-z0-9_-]+[ \t]*=/) {
        key = $0
        sub(/[ \t]*=.*/, "", key)
        sub(/^[ \t]*/, "", key)
        managed[key] = 1
      }
      next
    }
    $0 == "# BEGIN mydotfiles — edit in the dotfiles repo" { block = 1; next }
    $0 == "# END mydotfiles" { block = 0; next }
    block { next }
    /^[ \t]*\[/ { tables = 1 }
    !tables && /^[ \t]*[A-Za-z0-9_-]+[ \t]*=/ {
      key = $0
      sub(/[ \t]*=.*/, "", key)
      sub(/^[ \t]*/, "", key)
      if (key in managed) next
    }
    { print }
    END { if (block) exit 1 }
  ' "$codex_package/config.toml" "$codex_existing"
} > "$merged"
mv "$merged" "$codex_config"

tpm_dir="$HOME/.tmux/plugins/tpm"
if [ ! -e "$tpm_dir" ] && [ ! -L "$tpm_dir" ]; then
  git clone https://github.com/tmux-plugins/tpm.git "$tpm_dir"
fi

"$tpm_dir/bin/install_plugins"
