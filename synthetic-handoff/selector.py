"""Stage only explicitly named files from a pre-authorised *synthetic* source.

This is a narrow, test-only selector. Caller must independently establish
source provenance and OS-enforced access isolation before this could ever
be used on non-synthetic content. The selector cannot make that decision.

A private, trusted destination parent (0700, current user owned) is required.
The final staged name is generated internally; no user-controlled output name.
The output directory is not published until all selected bytes are written.
"""
import os
from pathlib import Path
import secrets
import stat
import sys

from producer import ALLOWED_NAMES, RefusedSource, open_staging_root, read_selected_file


def _open_private_parent(directory: str) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(directory, flags)
    observed = os.fstat(fd)
    if (
        not stat.S_ISDIR(observed.st_mode)
        or observed.st_uid != os.geteuid()
        or stat.S_IMODE(observed.st_mode) != 0o700
    ):
        os.close(fd)
        raise RefusedSource("destination parent must be private and caller owned")
    return fd


def _write_file(staging_fd: int, name: str, payload: bytes) -> None:
    if name not in ALLOWED_NAMES:
        raise RefusedSource("file name outside fixed allowlist")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(name, flags, 0o600, dir_fd=staging_fd)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:])
            if written <= 0:
                raise OSError("staged file short write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)


def stage_selected(source_root: str, private_parent: str) -> str:
    # Resolve no user-controlled file name. Source root is an already
    # authorised *synthetic* fixture; all specific entries are fixed.
    source_fd = open_staging_root(source_root)
    try:
        selected = {}
        for name in ALLOWED_NAMES:
            content = read_selected_file(source_fd, name)
            if content is not None:
                selected[name] = content
        if not selected:
            raise RefusedSource("no eligible staged source files")
    finally:
        os.close(source_fd)

    # Important: source bytes are fully validated before any output exists.
    parent_fd = _open_private_parent(private_parent)
    pending_name = None
    final_name = None
    staging_fd = None
    pending_created = False
    try:
        token = secrets.token_hex(16)
        pending_name = ".pending-" + token
        final_name = "staged-" + token
        # Parent is private; unique 128-bit name avoids colliding with other
        # cooperative jobs. This is NOT cross-process hostile-writer proof.
        os.mkdir(pending_name, 0o700, dir_fd=parent_fd)
        pending_created = True
        staging_fd = os.open(
            pending_name,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
            getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        for name, data in selected.items():
            _write_file(staging_fd, name, data)
        os.fsync(staging_fd)

        # Never overwrite an existing final directory. A compromised same-UID
        # writer could still race this check; that threat is out of scope.
        try:
            os.stat(final_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise RefusedSource("staged destination already exists")

        os.rename(
            pending_name, final_name,
            src_dir_fd=parent_fd, dst_dir_fd=parent_fd,
        )
        pending_name = None
        # Directory rename durability across sudden power loss is unproven.
        # Do not raise after publication and misreport an already-published tree.
        return final_name
    finally:
        if staging_fd is not None:
            if pending_name is not None:
                # Remove only names created by this invocation; no traversal.
                for name in selected:
                    try:
                        os.unlink(name, dir_fd=staging_fd)
                    except FileNotFoundError:
                        pass
            os.close(staging_fd)
        if pending_created and pending_name is not None:
            os.rmdir(pending_name, dir_fd=parent_fd)
        os.close(parent_fd)


def main() -> int:
    if len(sys.argv) != 3:
        print("REFUSED: expected synthetic source and private destination parent", file=sys.stderr)
        return 2
    try:
        name = stage_selected(sys.argv[1], sys.argv[2])
    except (RefusedSource, OSError) as exc:
        # No absolute input locations or source bytes in public logs.
        print(f"REFUSED: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
