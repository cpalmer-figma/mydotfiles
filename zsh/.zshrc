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

  for server in figma-coderbox figma-admin-coderbox figma-mcp-staging statsig hex figma-admin-prod acryl resolve vantage; do
    print -- "\n=== $server ==="
    if [[ "$server" == statsig ]]; then
      "$uv_bin" run --no-project --script "$dotfiles_root/install-codex-config.py" --coder-statsig "$PWD" || return
    fi
    # Deliberately foreground: do not begin the next server until this exits.
    # Stream output immediately, including prompts without a newline. Keep
    # stdin attached so Codex can accept a pasted redirect URL as usual.
    command python3 -c '
import base64
import json
import os
import re
import signal
import subprocess
import sys

server = sys.argv[1]

def toml(value):
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k) + "=" + toml(v)
                              for k, v in value.items() if v is not None) + "}"
    if isinstance(value, list):
        return "[" + ",".join(map(toml, value)) + "]"
    return json.dumps(value)

def timed_out(*_):
    raise TimeoutError("MCP status check timed out")

def connected():
    config = json.loads(subprocess.check_output(
        ["codex", "mcp", "get", server, "--json"], timeout=15))
    if not config.get("enabled", True):
        raise RuntimeError("MCP is disabled in the Codex configuration")
    # app-server does not load project MCPs for an unscoped status request.
    # Supply the effective transport, including managed credentials and timeouts.
    spec = {k: v for k, v in config["transport"].items() if k != "type"}
    for key in ("startup_timeout_sec", "tool_timeout_sec", "enabled_tools", "disabled_tools"):
        spec[key] = config.get(key)
    process = subprocess.Popen(
        ["codex", "app-server", "-c", "mcp_servers=" + toml({server: spec})],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, start_new_session=True,
    )
    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
    def response(request_id):
        for line in process.stdout:
            message = json.loads(line)
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError("Codex rejected the MCP status request")
                return message["result"]
        raise RuntimeError("Codex closed the MCP status connection")
    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(60)
    try:
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "mcp_init", "version": "1"}}})
        response(1)
        send({"method": "initialized", "params": {}})
        send({"id": 2, "method": "mcpServerStatus/list", "params": {
            "serverName": server, "detail": "toolsAndAuthOnly"}})
        statuses = response(2)["data"]
        status = next((s for s in statuses if s["name"] == server), None)
        if status is None:
            raise RuntimeError("Codex returned no status for this MCP")
        return (status.get("serverCapabilities") is not None
                and status.get("authStatus") != "notLoggedIn"
                and status.get("runtimeStatus") in (None, "connected")
                and not status.get("toolsError"))
    finally:
        signal.alarm(0)
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        process.stdin.close()
        process.stdout.close()

print("Checking connection and authentication...", flush=True)
try:
    if connected():
        print(server + " is connected and authenticated; skipping login.", flush=True)
        sys.exit(0)
except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
    print("Could not check " + server + ": " + str(error), file=sys.stderr)
    sys.exit(1)
if server == "statsig":
    print("Statsig did not connect with its managed credentials; check /mcp in Codex.", file=sys.stderr)
    sys.exit(1)
print("Connection was not authenticated and ready; starting browser login.", flush=True)

with subprocess.Popen(
    ["codex", "mcp", "login", server, "--no-browser"],
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
      print -u2 -- "Setup for $server failed or was cancelled; stopping mcp-init."
      return "$exit_code"
    }
  done
  print -- '\nMCP setup complete. Restart Codex and run /mcp to verify the connections.'
)
