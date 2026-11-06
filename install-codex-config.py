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


def update(source, destination):
    if destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise ValueError(f"{destination}: expected a regular local file")
    defaults = tomlkit.parse(source.read_text())
    original = destination.read_text() if destination.exists() else ""
    document = tomlkit.parse(original)
    # Remove only actual legacy comments, never matching text inside strings.
    for index in range(len(document.body) - 1, -1, -1):
        _, item = document.body[index]
        if isinstance(item, Comment) and item.as_string().strip() in LEGACY_MARKERS:
            del document.body[index]
    document = tomlkit.parse(tomlkit.dumps(document))
    for key, value in defaults.items():
        document[key] = value
    rendered = tomlkit.dumps(document)
    expected = tomlkit.parse(original).unwrap()
    expected.update(defaults.unwrap())
    if tomlkit.parse(rendered).unwrap() != expected:
        raise ValueError("Updated TOML did not preserve the expected settings")
    if rendered == original:
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


if __name__ == "__main__":
    try:
        update(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception as error:
        sys.exit(f"Cannot configure Codex: {error}")
