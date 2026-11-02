# Strict data-only intake for wholly synthetic GitHub-runner fixtures.
#
# This is an isolated experiment, not an OpenClaw backup or a safe exporter.
# The caller must supply already-authorised bytes through stdin. This receiver
# never accepts source paths, symbolic-link references, or filesystem aliases.
# It does not establish OS-level non-access or the origin of supplied bytes.

import base64
import binascii
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys

ALLOWED_NAMES = frozenset(("settings.json", "agent-inventory.json", "notes.txt"))
MAX_INPUT_BYTES = 262144
MAX_FILE_BYTES = 65536
REQUIRED_ROOT_KEYS = frozenset(("format", "files"))
REQUIRED_ENTRY_KEYS = frozenset(("name", "sha256", "content_b64"))
FORMAT = "synthetic-data-only-handoff/v1"


class RefusedInput(ValueError):
    pass


def validate_envelope(raw: bytes) -> dict[str, bytes]:
    if len(raw) > MAX_INPUT_BYTES:
        raise RefusedInput("envelope too large")
    try:
        message = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise RefusedInput("invalid JSON envelope") from exc
    if not isinstance(message, dict) or frozenset(message) != REQUIRED_ROOT_KEYS:
        raise RefusedInput("unexpected envelope fields")
    if message["format"] != FORMAT:
        raise RefusedInput("unsupported envelope format")
    entries = message["files"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= len(ALLOWED_NAMES):
        raise RefusedInput("invalid file count")
    files = {}
    for item in entries:
        if not isinstance(item, dict) or frozenset(item) != REQUIRED_ENTRY_KEYS:
            raise RefusedInput("unexpected file fields (source paths are forbidden)")
        name, digest, content = item["name"], item["sha256"], item["content_b64"]
        if not isinstance(name, str) or name not in ALLOWED_NAMES or name in files:
            raise RefusedInput("disallowed or repeated file name")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise RefusedInput("invalid file digest")
        if not isinstance(content, str) or len(content) > MAX_FILE_BYTES * 2:
            raise RefusedInput("invalid or excessive encoded bytes")
        try:
            decoded = base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise RefusedInput("invalid base64") from exc
        if len(decoded) > MAX_FILE_BYTES:
            raise RefusedInput("file too large")
        if not hmac.compare_digest(hashlib.sha256(decoded).hexdigest(), digest):
            raise RefusedInput("digest mismatch")
        files[name] = decoded
    return files


def accept_to_fresh_directory(files: dict[str, bytes], target: Path) -> None:
    # The caller is responsible for choosing a trusted parent; this method
    # merely ensures the final destination is freshly created and cannot be a
    # preexisting link. All filenames are fixed by the schema.
    target.mkdir(mode=0o700)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    folder_fd = os.open(target, flags)
    try:
        for name, data in files.items():
            fd = os.open(
                name,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=folder_fd,
            )
            try:
                position = 0
                while position < len(data):
                    position += os.write(fd, data[position:])
            finally:
                os.close(fd)
    finally:
        os.close(folder_fd)


def main() -> int:
    if len(sys.argv) != 2:
        print("expected one destination directory argument", file=sys.stderr)
        return 2
    # Verify every item first. A malformed input cannot create an output tree.
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    try:
        files = validate_envelope(raw)
        accept_to_fresh_directory(files, Path(sys.argv[1]))
    except (RefusedInput, OSError) as exc:
        print(f"REFUSED: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(f"ACCEPTED: {len(files)} declared synthetic file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
