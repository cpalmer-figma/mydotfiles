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

# Codex rewrites ~/.codex/config.toml when it saves settings, which would
# replace a link, so stow skips that file (see codex/.stow-local-ignore).
# Instead, set this repository's top-level settings in it and keep the rest.
if [ ! -e "$codex_config" ]; then
  codex_existing=/dev/null
else
  codex_existing="$codex_config"
fi
merged="$(mktemp "$codex_config.XXXXXX")"
awk '
  function key_of(line) {
    sub(/^[ \t]*/, "", line)
    sub(/[ \t]*=.*/, "", line)
    return line
  }
  # Top-level keys must come before the first table.
  function add_missing(   i, added) {
    for (i = 1; i <= count; i++) {
      if (!(order[i] in found)) {
        print setting[order[i]]
        added = 1
      }
    }
    return added
  }
  # The first file holds the settings from this repository.
  FNR == NR {
    if ($0 ~ /^[ \t]*[A-Za-z0-9_-]+[ \t]*=/) {
      order[++count] = key_of($0)
      setting[key_of($0)] = $0
    }
    next
  }
  !tables && /^[ \t]*\[/ {
    if (add_missing()) print ""
    tables = 1
  }
  !tables && /^[ \t]*[A-Za-z0-9_-]+[ \t]*=/ && (key_of($0) in setting) {
    if (!(key_of($0) in found)) print setting[key_of($0)]
    found[key_of($0)] = 1
    next
  }
  { print }
  END { if (!tables) add_missing() }
' "$codex_package/config.toml" "$codex_existing" > "$merged"
mv "$merged" "$codex_config"

tpm_dir="$HOME/.tmux/plugins/tpm"
if [ ! -e "$tpm_dir" ] && [ ! -L "$tpm_dir" ]; then
  git clone https://github.com/tmux-plugins/tpm.git "$tpm_dir"
fi

"$tpm_dir/bin/install_plugins"
