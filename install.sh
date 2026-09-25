#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

missing=()
for dependency in stow tmux git; do
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

# Keep downloaded plugins in the home directory, outside this repository.
mkdir -p "$HOME/.tmux/plugins"

for package in */; do
  [ -d "$package" ] || continue
  stow -t "$HOME" "${package%/}"
done

tpm_dir="$HOME/.tmux/plugins/tpm"
if [ ! -e "$tpm_dir" ] && [ ! -L "$tpm_dir" ]; then
  git clone https://github.com/tmux-plugins/tpm.git "$tpm_dir"
fi

"$tpm_dir/bin/install_plugins"
