#!/usr/bin/env python3
"""SEC-03A disposable process-crash fault injection against SEC-02 commit_once.

Synthetic file content only. Simulates abrupt process death (os._exit), NOT
power loss, persistent queue recovery, real human approval, or Hermes.
Run with an isolated owner UID on a fresh GitHub-hosted macOS VM.
"""
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import uuid

BEFORE = "SYNTHETIC_ONLY:alpha\n"
AFTER = "SYNTHETIC_ONLY:beta\n"


def load_engine(source):
    spec = importlib.util.spec_from_file_location("sec02_broker_fixture", source)
    if not spec or not spec.loader:
        raise RuntimeError("Public SEC-02 fixture could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(root, label, before=BEFORE):
    vault = root / label
    vault.mkdir(mode=0o700)
    (vault / "claims").mkdir(mode=0o700)
    (vault / "MEMORY.md").write_text(before, encoding="utf-8")
    (vault / "MEMORY.md").chmod(0o600)
    return vault


def make_record(before=BEFORE, after=AFTER):
    return {"id": uuid.uuid4().hex, "before": before, "after": after}


def run_child(engine, vault, record, fault):
    """Exit 97 means deliberate crash, 0 successful commit, 11 refused, 98 error."""
    try:
        if fault == "before_claim":
            original = engine.os.open
            marker = vault / "claims" / (record["id"] + ".claimed")

            def crash_before_claim(path, flags, *args, **kwargs):
                if Path(path) == marker:
                    os._exit(97)
                return original(path, flags, *args, **kwargs)

            engine.os.open = crash_before_claim

        elif fault in {"after_claim_sync", "after_replace_before_dir_sync", "after_replace_dir_sync"}:
            original = engine.fsync_dir

            def fail_at_dir(path):
                if fault == "after_replace_before_dir_sync" and Path(path) == vault:
                    os._exit(97)
                original(path)
                if fault == "after_claim_sync" and Path(path) == vault / "claims":
                    os._exit(97)
                if fault == "after_replace_dir_sync" and Path(path) == vault:
                    os._exit(97)

            engine.fsync_dir = fail_at_dir

        elif fault == "before_replace":
            def crash_before_replace(*_args, **_kwargs):
                os._exit(97)
            engine.os.replace = crash_before_replace

        elif fault not in {"after_result", "normal"}:
            raise ValueError("Unexpected fault stage")

        result = engine.commit_once(vault, record)
        if fault == "after_result":
            if not result.get("ok"):
                os._exit(98)
            os._exit(97)
        if result.get("ok") is True:
            os._exit(0)
        if result.get("error") == "ALREADY_CLAIMED":
            os._exit(11)
        os._exit(98)
    except BaseException:
        os._exit(98)


def spawn_and_wait(engine, vault, record, stage):
    pid = os.fork()
    if pid == 0:
        run_child(engine, vault, record, stage)
    _, status = os.waitpid(pid, 0)
    if not os.WIFEXITED(status):
        raise AssertionError(f"{stage}: child died unexpectedly: {status}")
    return os.WEXITSTATUS(status)


def assert_claim(engine, vault, record, exists):
    path = vault / "claims" / (record["id"] + ".claimed")
    assert path.exists() is exists, f"claim expectation failed for {vault.name}"
    if exists:
        assert path.read_text(encoding="utf-8") == engine.fingerprint(record)
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def check_crash_stage(engine, root, stage, *, after_expected):
    vault = prepare(root, stage)
    record = make_record()
    exit_code = spawn_and_wait(engine, vault, record, stage)
    assert exit_code == 97, f"{stage}: expected controlled crash 97, got {exit_code}"
    assert vault.joinpath("MEMORY.md").read_text(encoding="utf-8") == after_expected

    has_claim = stage != "before_claim"
    assert_claim(engine, vault, record, has_claim)
    if has_claim:
        # Re-import the broker module to emulate a fresh owner-side process.
        fresh = load_engine(ENGINE_SOURCE)
        replay = fresh.commit_once(vault, record)
        assert replay == {"ok": False, "error": "ALREADY_CLAIMED"}, replay
        assert vault.joinpath("MEMORY.md").read_text(encoding="utf-8") == after_expected
        print(f"{stage.upper()}=PASS_CRASH_NO_AUTO_REPLAY", flush=True)
    else:
        # No durable claim yet: only prove that no write occurred.
        # A later human-authorized retry is not tested; automatic retry is forbidden by policy.
        print("BEFORE_CLAIM=PASS_NO_WRITE_NO_CLAIM_RETRY_NOT_TESTED", flush=True)


def check_stale(engine, root):
    vault = prepare(root, "stale", before="SYNTHETIC_ONLY:external-change\n")
    record = make_record()
    outcome = engine.commit_once(vault, record)
    assert outcome == {"ok": False, "error": "STALE_BEFORE"}, outcome
    assert_claim(engine, vault, record, True)
    assert vault.joinpath("MEMORY.md").read_text(encoding="utf-8") == "SYNTHETIC_ONLY:external-change\n"
    assert engine.commit_once(vault, record) == {"ok": False, "error": "ALREADY_CLAIMED"}
    print("STALE_BEFORE=PASS_REFUSED_AND_CLAIMED", flush=True)


def check_two_processes(engine, root):
    vault = prepare(root, "concurrent")
    record = make_record()
    pids = []
    for _ in range(2):
        pid = os.fork()
        if pid == 0:
            run_child(engine, vault, record, "normal")
        pids.append(pid)
    codes = []
    for pid in pids:
        _, status = os.waitpid(pid, 0)
        assert os.WIFEXITED(status)
        codes.append(os.WEXITSTATUS(status))
    assert sorted(codes) == [0, 11], codes
    assert_claim(engine, vault, record, True)
    assert vault.joinpath("MEMORY.md").read_text(encoding="utf-8") == AFTER
    print("CONCURRENT_PROCESSES=PASS_SINGLE_WINNER", flush=True)


def main():
    global ENGINE_SOURCE
    if len(sys.argv) != 3:
        raise SystemExit("usage: probe.py PATH_TO_SEC02_SOURCE SYNTHETIC_ROOT")
    ENGINE_SOURCE = Path(sys.argv[1]).resolve()
    root = Path(sys.argv[2]).resolve()
    assert sys.platform == "darwin", "macOS is required"
    assert os.geteuid() != 0, "Owner fixture must not run as root"
    assert root.is_dir() and root.name.startswith("hermes-sec03.")
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    engine = load_engine(ENGINE_SOURCE)
    assert callable(engine.commit_once)

    check_crash_stage(engine, root, "before_claim", after_expected=BEFORE)
    for stage in ["after_claim_sync", "before_replace"]:
        check_crash_stage(engine, root, stage, after_expected=BEFORE)
    for stage in ["after_replace_before_dir_sync", "after_replace_dir_sync", "after_result"]:
        check_crash_stage(engine, root, stage, after_expected=AFTER)
    check_stale(engine, root)
    check_two_processes(engine, root)
    print("SEC03A_RESULT=PASS_SYNTHETIC_PROCESS_CRASH_CLAIM_REPLAY", flush=True)
    print("NOT_VERIFIED=power_loss,hardware_fsync,real_human_approval,pending_persistence,macOS_27,Hermes_integration,production", flush=True)


if __name__ == "__main__":
    main()
