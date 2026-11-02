"""Synthetic staging selector tests. Files are local throwaway fixtures only."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import selector

HERE = Path(__file__).resolve().parent
SELECTOR_SCRIPT = HERE / "selector.py"
PRODUCER_SCRIPT = HERE / "producer.py"
RECEIVER_SCRIPT = HERE / "receiver.py"
FAKE_FORBIDDEN_BYTES = b"THIS_IS_A_FICTIONAL_UNSELECTED_TEST_FILE"


class SelectorFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-selector-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.allowed = self.root / "authorised-fixture"
        self.allowed.mkdir(mode=0o700)
        self.private_parent = self.root / "private-stage-parent"
        self.private_parent.mkdir(mode=0o700)
        self.denied = self.root / "unselected"
        self.denied.mkdir(mode=0o700)
        self.secret = self.denied / "not-authorised.txt"
        self.secret.write_bytes(FAKE_FORBIDDEN_BYTES)
        self.secret.chmod(0o600)

    def add_allowed(self, name="settings.json", data=b'{"fictional":true}'):
        f = self.allowed / name
        f.write_bytes(data)
        f.chmod(0o600)
        return f

    def run_selector(self, source=None, parent=None):
        return subprocess.run(
            [sys.executable, "-B", str(SELECTOR_SCRIPT),
             str(source if source is not None else self.allowed),
             str(parent if parent is not None else self.private_parent)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def assert_no_staging(self, proc):
        self.assertEqual(proc.returncode, 2, proc.stderr.decode())
        self.assertEqual(proc.stdout, b"")
        self.assertEqual(list(self.private_parent.iterdir()), [])

    def test_complete_selector_producer_receiver_chain(self):
        data = b'{"fictitious_preferences":["no_real_data"]}'
        self.add_allowed("settings.json", data=data)
        self.add_allowed("notes.txt", data=b"entirely synthetic, not user data")
        proc = self.run_selector()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        basename = proc.stdout.decode().strip()
        self.assertTrue(basename.startswith("staged-"))
        self.assertNotIn("/", basename)
        staged = self.private_parent / basename
        self.assertEqual(sorted(p.name for p in staged.iterdir()),
                         ["notes.txt", "settings.json"])
        self.assertEqual(stat.S_IMODE(staged.stat().st_mode), 0o700)
        for file in staged.iterdir():
            self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)
            self.assertEqual(file.stat().st_nlink, 1)
            self.assertEqual(file.stat().st_uid, os.geteuid())
        produced = subprocess.run(
            [sys.executable, "-B", str(PRODUCER_SCRIPT), str(staged)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(produced.returncode, 0, produced.stderr.decode())
        self.assertNotIn(FAKE_FORBIDDEN_BYTES, produced.stdout)
        restored = self.root / "synthetic-reconstructed"
        accepted = subprocess.run(
            [sys.executable, "-B", str(RECEIVER_SCRIPT), str(restored)],
            input=produced.stdout, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr.decode())
        self.assertEqual((restored / "settings.json").read_bytes(), data)
        self.assertEqual((restored / "notes.txt").read_bytes(),
                         b"entirely synthetic, not user data")
        self.assertEqual(self.secret.read_bytes(), FAKE_FORBIDDEN_BYTES)

    def test_no_directory_discovery_or_unlisted_file_open(self):
        self.add_allowed()
        (self.allowed / "file-not-listed.txt").write_bytes(FAKE_FORBIDDEN_BYTES)
        attempted = []
        original = selector.os.open

        def recording_open(filename, *args, **kwargs):
            attempted.append(str(filename))
            return original(filename, *args, **kwargs)

        with mock.patch.object(selector.os, "open", side_effect=recording_open), \
             mock.patch.object(selector.os, "scandir",
                               side_effect=AssertionError("discovery forbidden")), \
             mock.patch.object(selector.os, "listdir",
                               side_effect=AssertionError("enumeration forbidden")):
            name = selector.stage_selected(str(self.allowed), str(self.private_parent))
        self.assertFalse(any("file-not-listed" in x for x in attempted))
        self.assertEqual((self.private_parent / name / "settings.json").read_bytes(),
                         b'{"fictional":true}')

    def test_symlink_file_to_unselected_location_is_refused(self):
        (self.allowed / "settings.json").symlink_to(self.secret)
        self.assert_no_staging(self.run_selector())
        self.assertEqual(self.secret.read_bytes(), FAKE_FORBIDDEN_BYTES)

    @unittest.skipIf(os.name == "nt", "Linux/macOS only hardlink case")
    def test_hardlink_to_unselected_file_is_refused(self):
        os.link(self.secret, self.allowed / "settings.json")
        self.assert_no_staging(self.run_selector())
        self.assertEqual(self.secret.read_bytes(), FAKE_FORBIDDEN_BYTES)

    def test_source_directory_symlink_is_refused(self):
        self.add_allowed()
        alias = self.root / "source-symlink"
        alias.symlink_to(self.allowed, target_is_directory=True)
        self.assert_no_staging(self.run_selector(source=alias))

    def test_destination_parent_symlink_is_refused(self):
        self.add_allowed()
        alias = self.root / "parent-symlink"
        alias.symlink_to(self.private_parent, target_is_directory=True)
        self.assert_no_staging(self.run_selector(parent=alias))

    def test_insecure_parent_permissions_are_refused(self):
        self.add_allowed()
        self.private_parent.chmod(0o755)
        self.assert_no_staging(self.run_selector())
        self.private_parent.chmod(0o700)

    def test_insecure_source_permissions_are_refused(self):
        self.add_allowed()
        self.allowed.chmod(0o755)
        self.assert_no_staging(self.run_selector())
        self.allowed.chmod(0o700)

    def test_insecure_source_file_is_refused(self):
        file = self.add_allowed()
        file.chmod(0o644)
        self.assert_no_staging(self.run_selector())

    def test_empty_source_is_refused(self):
        self.assert_no_staging(self.run_selector())

    def test_bad_second_allowed_entry_creates_no_partial_staging(self):
        self.add_allowed(data=b"first accepted bytes")
        (self.allowed / "notes.txt").symlink_to(self.secret)
        self.assert_no_staging(self.run_selector())

    def test_injected_second_write_failure_cleans_temporary_staging(self):
        self.add_allowed(data=b"first fictional file")
        self.add_allowed("notes.txt", b"second fictional file")
        original = selector.os.write
        calls = 0

        def fail_on_second_write(fd, payload):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("synthetic induced write failure")
            return original(fd, payload)

        with mock.patch.object(selector.os, "write", side_effect=fail_on_second_write):
            with self.assertRaises(OSError):
                selector.stage_selected(str(self.allowed), str(self.private_parent))
        self.assertEqual(list(self.private_parent.iterdir()), [])
        self.assertEqual((self.allowed / "notes.txt").read_bytes(),
                         b"second fictional file")

    def test_injected_rename_failure_cleans_temporary_staging(self):
        self.add_allowed()
        with mock.patch.object(selector.os, "rename",
                               side_effect=OSError("synthetic publish failure")):
            with self.assertRaises(OSError):
                selector.stage_selected(str(self.allowed), str(self.private_parent))
        self.assertEqual(list(self.private_parent.iterdir()), [])

    def test_preexisting_final_name_is_never_replaced(self):
        self.add_allowed()
        fixed = "a" * 32
        existing = self.private_parent / ("staged-" + fixed)
        existing.mkdir(mode=0o700)
        (existing / "keep.txt").write_text("do not replace")
        with mock.patch.object(selector.secrets, "token_hex", return_value=fixed):
            with self.assertRaises(selector.RefusedSource):
                selector.stage_selected(str(self.allowed), str(self.private_parent))
        self.assertEqual((existing / "keep.txt").read_text(), "do not replace")
        self.assertEqual([x.name for x in self.private_parent.iterdir()],
                         ["staged-" + fixed])

    def test_denied_fixture_is_not_modified_on_success(self):
        self.add_allowed()
        result = self.run_selector()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(self.secret.read_bytes(), FAKE_FORBIDDEN_BYTES)


if __name__ == "__main__":
    unittest.main()
