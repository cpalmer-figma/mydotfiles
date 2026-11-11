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
  local tool server uv_bin exit_code pixie_state
  if [[ "${FIGMA_CODER_INSTANCE_TYPE:-}" != devbox ]]; then
    print -u2 -- 'mcp-init must run inside a Coder devbox.'
    return 1
  fi
  for tool in codex jq python3; do
    command -v "$tool" >/dev/null || {
      print -u2 -- "mcp-init requires the existing $tool command."
      return 1
    }
  done
  uv_bin=$(command -v uv) || uv_bin="$HOME/.local/bin/uv"
  [[ -x "$uv_bin" ]] || { print -u2 -- 'Run the dotfiles installer to set up uv first.'; return 1; }
  cd "$HOME/figma/figma" || return

  pixie_state=$(./minifig service ls --json | jq -er '.[] | select(.name == "pixie") | .status') || return
  case "$pixie_state" in
    healthy) print -- 'Pixie is already running.' ;;
    pending|starting) print -- 'Pixie is already starting; waiting for it...' ;;
    *)
      print -- 'Starting Pixie with its current Minifig configuration (a local build may be needed)...'
      ./minifig service start pixie || return
      ;;
  esac
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
      # Stream output immediately, including prompts without a newline. Keep
      # stdin attached so Codex can accept a pasted redirect URL as usual.
      command python3 -c '
import base64
import os
import re
import subprocess
import sys

with subprocess.Popen(
    ["codex", "mcp", "login", sys.argv[1], "--no-browser"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
) as process:
    pending = b""
    copied = False
    try:
        while True:
            chunk = os.read(process.stdout.fileno(), 4096)
            if not chunk:
                break
            os.write(1, chunk)
            if copied or not os.isatty(1):
                continue
            pending = (pending + chunk)[-65536:]
            clean = re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", pending)
            for match in re.finditer(rb"https://[^\s<>\x22\x27]+(?=[\s<>\x22\x27])", clean):
                url = match.group(0)
                if b"client_id=" not in url or not (
                    b"response_type=code" in url or b"code_challenge=" in url
                ):
                    continue
                # OSC 52 reaches the laptop terminal over SSH; tmux forwards
                # it with the existing set-clipboard on configuration.
                os.write(1, b"\x1b]52;c;" + base64.b64encode(url) + b"\x07")
                os.write(1, b"\n[Authorization URL sent to terminal clipboard.]\n")
                copied = True
                break
        exit_code = process.wait()
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        sys.exit(130)
sys.exit(exit_code if exit_code >= 0 else 128 - exit_code)
' "$server" || {
        exit_code=$?
        print -u2 -- "Login for $server failed or was cancelled; stopping mcp-init."
        return "$exit_code"
      }
    fi
  done
  print -- '\nMCP setup complete. Restart Codex and run /mcp to verify the connections.'
)
