#!/usr/bin/env python3
"""SEC-03B-S: synthetic, offline, owner-verified ECDSA approval fixture.

No iPhone, Secure Enclave, Face ID, real human or Hermes here.
Never treats a merely asserted authorized=True or supplied public key as authority.
Uses a pinned owner-owned public key and SEC-02's one-use commit_once() function.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid

PREFIX = "SYNTHETIC_ONLY:"
PURPOSE = "SEC03B_SYNTHETIC_MEMORY_APPROVAL_V1"
MAX_BYTES = 4096
CASE_NAMES = (
    "valid", "tampered", "id_swap", "expired", "too_future",
    "wrong_audience", "wrong_target", "stale", "forged", "missing",
)


def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_broker(path):
    spec = importlib.util.spec_from_file_location("sec02_fixture", str(path))
    if not spec or not spec.loader:
        raise RuntimeError("SEC-02 public fixture unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(root):
    vault = root / "vault"
    requests = root / "requests"
    if os.geteuid() == 0 or vault.stat().st_uid != os.geteuid():
        raise RuntimeError("Owner-only fixture preparation required")
    assert requests.is_dir() and vault.is_dir()
    now = int(time.time())
    for name in CASE_NAMES:
        case_vault = vault / name
        case_vault.mkdir(mode=0o700)
        (case_vault / "claims").mkdir(mode=0o700)
        initial = PREFIX + ("external\n" if name == "stale" else "alpha\n")
        (case_vault / "MEMORY.md").write_text(initial, encoding="utf-8")
        (case_vault / "MEMORY.md").chmod(0o600)

        payload = {
            "version": 1,
            "purpose": PURPOSE,
            "target": "MEMORY.md",
            "id": uuid.uuid4().hex,
            "before": PREFIX + "alpha\n",
            "after": PREFIX + "beta\n",
            "issued_at": now,
            "expires_at": now + 180,
        }
        if name == "expired":
            payload["issued_at"] = now - 900
            payload["expires_at"] = now - 600
        if name == "too_future":
            payload["expires_at"] = now + 86400
        if name == "wrong_audience":
            payload["purpose"] = "OTHER_SERVICE"
        if name == "wrong_target":
            payload["target"] = "ANOTHER_FILE"

        signable = requests / (name + ".signed.json")
        request = requests / (name + ".json")
        signable.write_bytes(canonical(payload))
        if name == "tampered":
            payload["after"] = PREFIX + "evil\n"
        if name == "id_swap":
            payload["id"] = uuid.uuid4().hex
        request.write_bytes(canonical(payload))
        signable.chmod(0o644)
        request.chmod(0o644)
    print("SYNTHETIC_APPROVAL_CASES_PREPARED=PASS", flush=True)


def result(ok, **kwargs):
    return {"ok": ok, **kwargs}


def verify_signature(raw, signature, pubkey, directory):
    # Read once; verify these exact bytes, never an attacker-modifiable path.
    fd, name = tempfile.mkstemp(dir=directory, prefix=".sig-", suffix=".bin")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(signature)
            stream.flush()
            os.fsync(stream.fileno())
        proc = subprocess.run(
            ["/usr/bin/openssl", "dgst", "-sha256", "-verify", str(pubkey),
             "-signature", name],
            input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=8, check=False,
        )
        return proc.returncode == 0
    finally:
        os.unlink(name)


def check_and_apply(root, name, broker):
    if name not in CASE_NAMES or not re.fullmatch("[a-z_]+", name):
        return result(False, error="BAD_CASE")
    vault = root / "vault" / name
    request = root / "requests" / (name + ".json")
    signature = root / "requests" / (name + ".sig")
    pubkey = root / "vault" / "public.pem"

    # All these paths are fixed within the disposable synthetic fixture.
    if not signature.exists():
        return result(False, error="MISSING_SIGNATURE")
    raw = request.read_bytes()
    sig = signature.read_bytes()
    if not (0 < len(raw) <= MAX_BYTES and 0 < len(sig) <= 256):
        return result(False, error="BAD_LENGTH")
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict) or raw != canonical(payload):
            return result(False, error="NONCANONICAL")
    except (ValueError, TypeError, UnicodeError):
        return result(False, error="BAD_JSON")

    if not verify_signature(raw, sig, pubkey, vault):
        return result(False, error="INVALID_SIGNATURE")

    expected_keys = {
        "version", "purpose", "target", "id", "before", "after",
        "issued_at", "expires_at",
    }
    if set(payload) != expected_keys:
        return result(False, error="INVALID_FIELDS")
    if payload["version"] != 1 or type(payload["version"]) is not int:
        return result(False, error="INVALID_VERSION")
    if payload["purpose"] != PURPOSE or payload["target"] != "MEMORY.md":
        return result(False, error="WRONG_SCOPE")
    identity = payload["id"]
    if not isinstance(identity, str) or re.fullmatch("[0-9a-f]{32}", identity) is None:
        return result(False, error="INVALID_ID")
    before, after = payload["before"], payload["after"]
    if not all(isinstance(x, str) and x.startswith(PREFIX) and len(x) <= 256 for x in [before, after]):
        return result(False, error="INVALID_CONTENT")
    issued, expires = payload["issued_at"], payload["expires_at"]
    now = int(time.time())
    if type(issued) is not int or type(expires) is not int:
        return result(False, error="INVALID_TIME")
    if issued > now + 30 or expires <= issued or expires - issued > 300:
        return result(False, error="INVALID_VALIDITY_WINDOW")
    if expires < now:
        return result(False, error="EXPIRED")

    # Already-used approvals return the same error even after broker restart.
    if (vault / "claims" / (identity + ".claimed")).exists():
        return result(False, error="ALREADY_CLAIMED")
    record = {"id": identity, "before": before, "after": after}
    return broker.commit_once(vault, record)


def main():
    if len(sys.argv) != 5 or sys.argv[1] not in {"prepare", "verify"}:
        raise SystemExit("usage: program.py prepare|verify ROOT CASE_OR_DASH SEC02_SOURCE")
    mode = sys.argv[1]
    root = Path(sys.argv[2]).resolve(strict=True)
    case = sys.argv[3]
    broker = load_broker(sys.argv[4])
    if sys.platform != "darwin" or os.geteuid() == 0:
        raise RuntimeError("Refuse non-macOS or root execution")
    if not root.name.startswith("hermes-sec03b."):
        raise RuntimeError("Refuse non-fixture path")
    if mode == "prepare":
        if case != "-":
            raise RuntimeError("Unexpected prepare argument")
        prepare(root)
    else:
        response = check_and_apply(root, case, broker)
        print(json.dumps(response, sort_keys=True, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
