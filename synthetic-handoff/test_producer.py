"""Fully fictional producer/receiver protocol tests; no private or live OpenClaw input."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import producer

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "producer.py"
RECEIVER = HERE / "receiver.py"
SECRET = b"FICTIONAL_OUT_OF_SCOPE_BYTES_DO_NOT_SELECT"


class SyntheticProducerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="producer-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / "stage"
        self.stage.mkdir(mode=0o700)
        self.denied = self.root / "unselected"
        self.denied.mkdir(mode=0o700)
        self.outside = self.denied / "fake-private.txt"
        self.outside.write_bytes(SECRET)
        self.outside.chmod(0o600)
        self.receiver_output = self.root / "restored"

    def put(self, name="settings.json", content=b'{"synthetic":true}', mode=0o600):
        p = self.stage / name
        p.write_bytes(content)
        p.chmod(mode)
        return p

    def run_producer(self, source=None):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(source or self.stage)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def test_end_to_end_only_authorised_bytes_are_restored(self):
        payload = b'{"completely_fictional":true}'
        self.put(content=payload)
        result = self.run_producer()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        envelope = json.loads(result.stdout)
        self.assertEqual([entry["name"] for entry in envelope["files"]], ["settings.json"])
        self.assertEqual(envelope["files"][0]["sha256"], hashlib.sha256(payload).hexdigest())
        receiver = subprocess.run(
            [sys.executable, "-B", str(RECEIVER), str(self.receiver_output)],
            input=result.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(receiver.returncode, 0, receiver.stderr.decode())
        self.assertEqual((self.receiver_output / "settings.json").read_bytes(), payload)
        self.assertEqual(list(self.receiver_output.iterdir()), [self.receiver_output / "settings.json"])
        self.assertEqual(self.outside.read_bytes(), SECRET)

    def test_cannot_discover_unselected_fake_protected_file(self):
        self.put(content=b"selected fixture")
        nonselected = self.stage / "unselected-secret.txt"
        nonselected.write_bytes(SECRET)
        nonselected.chmod(0o600)
        selected_opens = []
        actual_open = producer.os.open
        def observed_open(path, *args, **kwargs):
            selected_opens.append(str(path))
            return actual_open(path, *args, **kwargs)
        with mock.patch.object(producer.os, "open", side_effect=observed_open):
            result = producer.produce(str(self.stage))
        self.assertNotIn(SECRET, result)
        self.assertNotIn("unselected-secret.txt", selected_opens)
        self.assertEqual([e["name"] for e in json.loads(result)["files"]], ["settings.json"])

    def test_rejects_symlink_to_unselected_fake_source(self):
        (self.stage / "settings.json").symlink_to(self.outside)
        result = self.run_producer()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(self.outside.read_bytes(), SECRET)

    @unittest.skipIf(os.name == "nt", "hardlink semantics differ")
    def test_rejects_hardlink_to_unselected_fake_source(self):
        os.link(self.outside, self.stage / "settings.json")
        self.assertEqual(self.outside.stat().st_nlink, 2)
        result = self.run_producer()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(self.outside.read_bytes(), SECRET)

    def test_rejects_symlink_as_source_directory(self):
        alias = self.root / "stage-alias"
        alias.symlink_to(self.stage, target_is_directory=True)
        self.put()
        result = self.run_producer(alias)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_rejects_directory_as_allowed_file(self):
        (self.stage / "settings.json").mkdir()
        result = self.run_producer()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_rejects_bad_file_permissions(self):
        self.put(mode=0o644)
        result = self.run_producer()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_rejects_non_private_staging_permissions(self):
        self.stage.chmod(0o750)
        self.addCleanup(lambda: self.stage.chmod(0o700))
        self.put()
        result = self.run_producer()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_rejects_oversized_fixture(self):
        self.put(content=b"a" * 65537)
        result = self.run_producer()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_rejects_empty_staging_root(self):
        result = self.run_producer()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_any_bad_allowed_entry_blocks_complete_output(self):
        self.put(content=b"legitimate")
        (self.stage / "agent-inventory.json").symlink_to(self.outside)
        result = self.run_producer()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_file_descriptor_restricted_to_single_selected_file(self):
        allowed = self.put(content=b"good")
        forbidden = self.stage / "not-on-allowlist.txt"
        forbidden.write_bytes(SECRET)
        forbidden.chmod(0o600)
        with mock.patch.object(producer.os, "listdir", side_effect=AssertionError("listdir not allowed")):
            with mock.patch.object(producer.os, "scandir", side_effect=AssertionError("scandir not allowed")):
                result = producer.produce(str(self.stage))
        self.assertNotIn(SECRET, result)
        self.assertEqual(allowed.read_bytes(), b"good")


if __name__ == "__main__":
    unittest.main()
