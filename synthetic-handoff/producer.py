"""Read only explicit, allowlisted files from an already-authorised synthetic staging directory.

This is NOT an OpenClaw exporter or a trusted origin attestor. Its source
directory must be prepared by a separately approved, OS-isolated selector.
No discovery of original source locations occurs here.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ALLOWED_NAMES = ("settings.json", "agent-inventory.json", "notes.txt")
MAX_FILE_BYTES = 65536
MAX_TOTAL_BYTES = 262144
FORMAT = "synthetic-data-only-handoff/v1"


class RefusedSource(Exception):
    pass


def open_staging_root(source_path: str) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(source_path, flags)
    root_stat = os.fstat(fd)
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or root_stat.st_uid != os.geteuid()
        or stat.S_IMODE(root_stat.st_mode) != 0o700
    ):
        os.close(fd)
        raise RefusedSource("staging directory not exclusively owned by producer identity")
    return fd


def read_selected_file(root_fd: int, name: str) -> bytes | None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(name, flags, dir_fd=root_fd)
    except FileNotFoundError:
        return None
    try:
        initial = os.fstat(fd)
        if (
            not stat.S_ISREG(initial.st_mode)
            or initial.st_nlink != 1
            or initial.st_uid != os.geteuid()
            or stat.S_IMODE(initial.st_mode) != 0o600
            or initial.st_size > MAX_FILE_BYTES
        ):
            raise RefusedSource("unsafe staged entry")
        with os.fdopen(os.dup(fd), "rb") as readable:
            data = readable.read(MAX_FILE_BYTES + 1)
        final = os.fstat(fd)
        if (
            len(data) > MAX_FILE_BYTES
            or len(data) != initial.st_size
            or (initial.st_dev, initial.st_ino, initial.st_nlink, initial.st_size,
                initial.st_mtime_ns, initial.st_ctime_ns) !=
               (final.st_dev, final.st_ino, final.st_nlink, final.st_size,
                final.st_mtime_ns, final.st_ctime_ns)
        ):
            raise RefusedSource("staged entry changed while reading")
        return data
    finally:
        os.close(fd)


def produce(staging_path: str) -> bytes:
    # Only the fixed allowlist is looked up; there is deliberately no readdir.
    root_fd = open_staging_root(staging_path)
    try:
        selected = []
        for name in ALLOWED_NAMES:
            data = read_selected_file(root_fd, name)
            if data is None:
                continue
            selected.append({
                "name": name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "content_b64": base64.b64encode(data).decode("ascii"),
            })
        if not selected:
            raise RefusedSource("no permitted staged files")
        envelope = json.dumps(
            {"format": FORMAT, "files": selected}, separators=(",", ":")
        ).encode("utf-8")
        if len(envelope) > MAX_TOTAL_BYTES:
            raise RefusedSource("envelope exceeds maximum")
        return envelope
    finally:
        os.close(root_fd)


def main() -> int:
    if len(sys.argv) != 2:
        print("REFUSED: expected one already-authorised synthetic staging directory",
              file=sys.stderr)
        return 2
    try:
        envelope = produce(sys.argv[1])
    except (RefusedSource, OSError) as exc:
        # Avoid printing paths or original file contents to public CI logs.
        print(f"REFUSED: {type(exc).__name__}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(envelope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
