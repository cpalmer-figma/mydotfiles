#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if ! command -v stow >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y stow
fi

for package in */; do
  [ -d "$package" ] || continue
  stow -t "$HOME" "${package%/}"
done
