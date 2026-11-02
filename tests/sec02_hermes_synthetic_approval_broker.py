#!/usr/bin/env python3
"""SEC-02 synthetic-only macOS peer-UID approval boundary fixture.

NOT Hermes integration, not a human-authentication system, not production.
The only accepted authority for review/approve is kernel-authenticated peer UID.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import uuid

MAX_MESSAGE = 4096
PREFIX = "SYNTHETIC_ONLY:"


def peer_euid(connection):
    if sys.platform != "darwin":
        raise RuntimeError("macOS getpeereid required; no fallback")
    libc = ctypes.CDLL(None, use_errno=True)
    fn = libc.getpeereid
    fn.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
    fn.restype = ctypes.c_int
    uid, gid = ctypes.c_uint(), ctypes.c_uint()
    if fn(connection.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0:
        code = ctypes.get_errno()
        raise OSError(code, "Cannot verify kernel socket peer identity")
    return int(uid.value)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(record):
    return hashlib.sha256(canonical(record).encode("ascii")).hexdigest()


def fsync_dir(path):
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def commit_once(vault, record):
    """Owner-only filesystem write; claim must be durable before replacing memory."""
    claims = vault / "claims"
    identity = record["id"]
    marker = claims / (identity + ".claimed")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    try:
        fd = os.open(marker, flags, 0o600)
    except FileExistsError:
        return {"ok": False, "error": "ALREADY_CLAIMED"}
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(fingerprint(record))
        stream.flush()
        os.fsync(stream.fileno())
    fsync_dir(claims)
    memory = vault / "MEMORY.md"
    if memory.read_text(encoding="utf-8") != record["before"]:
        return {"ok": False, "error": "STALE_BEFORE"}
    temporary = vault / (".new-" + identity)
    fd = os.open(temporary, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(record["after"])
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, memory)
    fsync_dir(vault)
    return {"ok": True, "applied": True}


def handle(request, uid, ai_uid, owner_uid, vault, pending):
    if not isinstance(request, dict):
        return {"ok": False, "error": "BAD_REQUEST"}
    op = request.get("op")

    if op == "propose":
        if uid != ai_uid:
            return {"ok": False, "error": "NOT_AI_PROPOSER"}
        after = request.get("after")
        if not isinstance(after, str) or not after.startswith(PREFIX) or len(after) > 256:
            return {"ok": False, "error": "BAD_SYNTHETIC_PROPOSAL"}
        before = (vault / "MEMORY.md").read_text(encoding="utf-8")
        record = {"id": uuid.uuid4().hex, "before": before, "after": after}
        pending[record["id"]] = record
        return {"ok": True, "id": record["id"], "fingerprint": fingerprint(record)}

    if op in {"review", "approve"}:
        # Do not inspect payload, claimed UID, alleged token, or fingerprint before
        # authenticating the *kernel-reported* identity on the live connection.
        if uid != owner_uid:
            return {"ok": False, "error": "UNAUTHORIZED_APPROVER"}
        identity = request.get("id")
        record = pending.get(identity) if isinstance(identity, str) else None
        if record is None:
            return {"ok": False, "error": "UNKNOWN_ID"}
        if op == "review":
            return {"ok": True, "record": record, "fingerprint": fingerprint(record)}
        if request.get("fingerprint") != fingerprint(record):
            return {"ok": False, "error": "FINGERPRINT_MISMATCH"}
        return commit_once(vault, record)

    return {"ok": False, "error": "UNKNOWN_OPERATION"}


def serve(root, ai_uid, owner_uid):
    if os.geteuid() != owner_uid or ai_uid == owner_uid:
        raise RuntimeError("Refuse to start without separate authenticated owner")
    root = Path(root)
    vault = root / "vault"
    endpoint = root / "endpoint" / "broker.sock"
    if not (vault.is_dir() and (vault / "claims").is_dir()):
        raise RuntimeError("Missing owner-only synthetic vault")
    pending = {}
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(endpoint))
    os.chmod(endpoint, 0o777)  # Both identities may CONNECT; UID authorisation is in broker.
    server.listen(8)
    server.settimeout(60)
    print("SEC02_BROKER_READY", flush=True)
    while True:
        with server.accept()[0] as connection:
            connection.settimeout(5)
            try:
                uid = peer_euid(connection)
                payload = b""
                while not payload.endswith(b"\n"):
                    data = connection.recv(1024)
                    if not data:
                        break
                    payload += data
                    if len(payload) > MAX_MESSAGE:
                        raise ValueError("Request too large")
                req = json.loads(payload.decode("utf-8"))
                reply = handle(req, uid, ai_uid, owner_uid, vault, pending)
            except (ValueError, OSError, UnicodeError, TypeError, KeyError) as exc:
                reply = {"ok": False, "error": "FAIL_CLOSED"}
            connection.sendall((canonical(reply) + "\n").encode("ascii"))


def call(endpoint, payload):
    if len(payload) > MAX_MESSAGE:
        raise RuntimeError("Request too large")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(8)
    sock.connect(endpoint)
    with sock:
        sock.sendall(payload.encode("utf-8") + b"\n")
        result = b""
        while not result.endswith(b"\n"):
            chunk = sock.recv(1024)
            if not chunk:
                raise RuntimeError("Broker returned no response")
            result += chunk
            if len(result) > MAX_MESSAGE:
                raise RuntimeError("Response too large")
    response = json.loads(result.decode("utf-8"))
    print(canonical(response))
    if not isinstance(response, dict):
        raise RuntimeError("Invalid broker response")


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "serve":
        serve(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif len(sys.argv) == 4 and sys.argv[1] == "call":
        call(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit("Use: serve ROOT AI_UID OWNER_UID | call SOCKET JSON")
