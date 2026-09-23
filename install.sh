#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

missing=()
for dependency in stow tmux git; do
  command -v "$dependency" >/dev/null 2>&1 || missing+=("$dependency")
done

if ((${#missing[@]})); then
  sudo apt-get update
  sudo apt-get install -y "${missing[@]}"
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
