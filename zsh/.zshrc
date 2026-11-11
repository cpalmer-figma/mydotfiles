# Wait for Minifig services, showing elapsed time while they settle.
wait-minifig() (
  setopt pipefail
  cd "$HOME/figma/figma" || return

  ./minifig system info | jq -r '"Active Minifig profile: \(.active_profile)"' || return

  local SECONDS=0 counts ready total
  while true; do
    counts=$(./minifig service ls --json | jq -r '
      map(select(.desired_active or .status != "stopped"))
      | [(map(select(.status == "healthy" or .status == "completed" or .status == "stopped")) | length), length]
      | @tsv
    ') || {
      printf '\n'
      return 1
    }
    read -r ready total <<< "$counts"
    printf '\rWaiting for Minifig... %dm %02ds (%d/%d) Ready\033[K' "$(( SECONDS / 60 ))" "$(( SECONDS % 60 ))" "$ready" "$total"
    (( ready == total )) && break
    sleep 5 || return
  done

  printf '\rMinifig ready after %dm %02ds.\033[K\n' "$(( SECONDS / 60 ))" "$(( SECONDS % 60 ))"
)

# Start the local MCP gateway, then authenticate one server at a time.
mcp-init() (
  setopt pipefail
  local dotfiles_root="${${(%):-%x}:A:h:h}"
  local tool active_profile profile_source profile_target profile_tmp=""
  local server uv_bin exit_code
  if [[ "${FIGMA_CODER_INSTANCE_TYPE:-}" != devbox ]]; then
    print -u2 -- 'mcp-init must run inside a Coder devbox.'
    return 1
  fi
  for tool in codex jq yq; do
    command -v "$tool" >/dev/null || {
      print -u2 -- "mcp-init requires the existing $tool command."
      return 1
    }
  done
  uv_bin=$(command -v uv) || uv_bin="$HOME/.local/bin/uv"
  [[ -x "$uv_bin" ]] || { print -u2 -- 'Run the dotfiles installer to set up uv first.'; return 1; }
  cd "$HOME/figma/figma" || return

  active_profile=$(./minifig system info | jq -er '.active_profile | select(type == "string" and length > 0)') || return
  if [[ "$active_profile" == /* || "$active_profile" == *..* ]]; then
    print -u2 -- "Unexpected Minifig profile: $active_profile"
    return 1
  fi
  profile_source="devbox-profiles/$active_profile.yml"
  [[ -f "$profile_source" ]] || { print -u2 -- "Missing profile: $profile_source"; return 1; }
  profile_target=devbox-profiles/personal/cpalmer-mcp-init.yml
  if [[ -L "$profile_target" || ( -e "$profile_target" && ! -f "$profile_target" ) ]]; then
    print -u2 -- "Expected a regular profile file: $profile_target"
    return 1
  fi
  mkdir -p "${profile_target:h}" || return
  profile_tmp=$(mktemp "${profile_target}.XXXXXX") || return
  trap '[[ -z "$profile_tmp" ]] || rm -f -- "$profile_tmp"' EXIT
  # Keep the active profile's services and override only Pixie's image source.
  yq eval '.name = "cpalmer-mcp-init" | .service_groups = ((.service_groups // [] | map(select(.name != "pixie"))) + [{"name": "pixie", "image_source": "prebuilt"}])' \
    "$profile_source" > "$profile_tmp" || return
  if cmp -s "$profile_tmp" "$profile_target"; then
    rm -f -- "$profile_tmp" || return
  else
    mv -- "$profile_tmp" "$profile_target" || return
  fi
  print -- 'Starting prebuilt Pixie alongside your current profile services...'
  ./minifig profile set personal/cpalmer-mcp-init --wait || return
  ./minifig service start pixie || return
  ./minifig service wait pixie || {
    print -u2 -- 'Pixie did not become healthy. Inspect it with: ./minifig logs pixie'
    return 1
  }

  for server in figma-coderbox figma-admin-coderbox figma-mcp-staging statsig hex; do
    print -- "\n=== $server ==="
    if [[ "$server" == statsig ]]; then
      "$uv_bin" run --no-project --script "$dotfiles_root/install-codex-config.py" --coder-statsig "$PWD" || return
      command codex mcp get statsig || return
      print -- 'Statsig uses managed credentials; no browser login is needed.'
    else
      # Deliberately foreground: do not begin the next login until this exits.
      command codex mcp login "$server" --no-browser || {
        exit_code=$?
        print -u2 -- "Login for $server failed or was cancelled; stopping mcp-init."
        return "$exit_code"
      }
    fi
  done
  print -- '\nMCP setup complete. Restart Codex and run /mcp to verify the connections.'
)
