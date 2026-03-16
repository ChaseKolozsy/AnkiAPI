"""Cross-platform helpers for locating Anki collection paths."""

import os
import sys


def anki_base(username: str) -> str:
    """Return the base Anki2 profile directory for *username*."""
    if sys.platform == "win32":
        return os.path.join(os.environ["APPDATA"], "Anki2", username)
    elif sys.platform == "darwin":
        return os.path.expanduser(f"~/Library/Application Support/Anki2/{username}")
    return os.path.expanduser(f"~/.local/share/Anki2/{username}")


def collection_path(username: str) -> str:
    """Return the path to ``collection.anki2`` for *username*."""
    return os.path.join(anki_base(username), "collection.anki2")


def media_path(username: str) -> str:
    """Return the path to the ``collection.media`` directory for *username*."""
    return os.path.join(anki_base(username), "collection.media")
