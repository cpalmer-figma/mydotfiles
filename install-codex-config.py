#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["tomlkit==0.15.1"]
# ///
"""Apply shared Codex settings without replacing unrelated TOML content."""
import os
from pathlib import Path
import stat
import sys
import tempfile

import tomlkit
from tomlkit.items import Comment


LEGACY_MARKERS = {
    "# BEGIN mydotfiles — edit in the dotfiles repo",
    "# END mydotfiles",
}


def update(source, destination, coder_checkout=None):
    if destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise ValueError(f"{destination}: expected a regular local file")
    defaults = tomlkit.parse(source.read_text()) if coder_checkout is None else {}
    if destination.exists():
        original = destination.read_text()
    else:
        original = source.read_text() if coder_checkout else ""
    document = tomlkit.parse(original)
    # Remove only actual legacy comments, never matching text inside strings.
    for index in range(len(document.body) - 1, -1, -1):
        _, item = document.body[index]
        if isinstance(item, Comment) and item.as_string().strip() in LEGACY_MARKERS:
            del document.body[index]
    document = tomlkit.parse(tomlkit.dumps(document))
    for key, value in defaults.items():
        document[key] = value
    expected = tomlkit.parse(original).unwrap()
    if coder_checkout is None:
        expected.update(defaults.unwrap())
    else:
        configure_coder_statsig(document, coder_checkout)
        expected = document.unwrap()
    rendered = tomlkit.dumps(document)
    if tomlkit.parse(rendered).unwrap() != expected:
        raise ValueError("Updated TOML did not preserve the expected settings")
    if rendered == original and destination.exists():
        return
    fd, temporary = tempfile.mkstemp(prefix="config.toml.", dir=destination.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        if destination.exists():
            os.chmod(temporary, stat.S_IMODE(destination.stat().st_mode))
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configure_coder_statsig(document, checkout):
    wrapper = checkout / "devex/mcp-support/statsig-mcp-server"
    if not wrapper.is_file():
        raise ValueError(f"Statsig wrapper is missing: {wrapper}")
    servers = document.setdefault("mcp_servers", tomlkit.table())
    server = servers.setdefault("statsig", tomlkit.table())
    if (server.get("url") not in (None, "https://api.statsig.com/v1/mcp") or
            server.get("command") not in (None, "devex/mcp-support/statsig-mcp-server", str(wrapper))):
        raise ValueError("Statsig has a custom connection; update it manually")
    # Preserve tool policies and timeouts; remove HTTP-only fields for stdio.
    for key in ("url", "auth", "oauth", "scopes", "bearer_token_env_var",
                "http_headers", "env_http_headers", "http_headers_helper"):
        server.pop(key, None)
    server["enabled"] = True
    # Absolute commands are preserved by Figma's legacy-to-OAuth migration.
    server["command"] = str(wrapper)
    server["args"] = []
    server["cwd"] = str(checkout)
    environment = server.setdefault("env", tomlkit.table())
    environment["DEVCONTAINER"] = "1"
    environment["INSTANCE_TYPE"] = "devbox"


if __name__ == "__main__":
    try:
        if sys.argv[1] == "--coder-statsig":
            checkout = Path(sys.argv[2]).resolve()
            destination = checkout / ".codex/config.toml"
            update(checkout / ".codex/config.toml.example", destination, checkout)
            print(f"Configured managed Statsig MCP in {destination}")
        else:
            update(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception as error:
        sys.exit(f"Cannot configure Codex: {error}")
