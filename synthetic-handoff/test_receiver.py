"""Black-box tests for the synthetic data-only handoff receiver.

Never import OpenClaw or use private data. No fake fixture escapes the runner.
"""
import base64
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
RECEIVER = HERE / "receiver.py"
SYNTHETIC_SECRET = b"UNSELECTED_SYNTHETIC_SOURCE_DO_NOT_IMPORT"


def entry(name: str, data: bytes) -> dict:
    return {
        "name": name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "content_b64": base64.b64encode(data).decode("ascii"),
    }


def envelope(*items: dict) -> dict:
    return {"format": "synthetic-data-only-handoff/v1", "files": list(items)}


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="synthetic-handoff-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.protected = self.root / "unselected-fixture"
        self.protected.mkdir()
        self.secret = self.protected / "fictional-protected.txt"
        self.secret.write_bytes(SYNTHETIC_SECRET)
        self.output = self.root / "fresh-target"

    def run_receiver(self, payload, target=None):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(RECEIVER), str(target or self.output)],
            input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def assert_refused_before_output(self, payload):
        proc = self.run_receiver(payload)
        self.assertEqual(proc.returncode, 2, proc.stdout.decode() + proc.stderr.decode())
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.is_symlink())

    def test_only_declared_bytes_are_materialised_and_digest_verified(self):
        original = b'{"agents":[],"test":true}\n'
        note = b"Only fictional fixture content"
        proc = self.run_receiver(envelope(
            entry("settings.json", original), entry("notes.txt", note)
        ))
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual((self.output / "settings.json").read_bytes(), original)
        self.assertEqual((self.output / "notes.txt").read_bytes(), note)
        self.assertEqual(sorted(x.name for x in self.output.iterdir()),
                         ["notes.txt", "settings.json"])
        self.assertNotIn(SYNTHETIC_SECRET, b"".join(x.read_bytes() for x in self.output.iterdir()))
        self.assertEqual(self.secret.read_bytes(), SYNTHETIC_SECRET)
        self.assertEqual(os.stat(self.output / "settings.json").st_nlink, 1)

    def test_rejects_source_path_even_if_alias_is_a_symlink(self):
        alias = self.root / "apparently-safe-link"
        alias.symlink_to(self.secret)
        item = entry("notes.txt", b"authorised fictional bytes")
        item["source_path"] = str(alias)
        self.assert_refused_before_output(envelope(item))
        self.assertEqual(self.secret.read_bytes(), SYNTHETIC_SECRET)

    @unittest.skipIf(os.name == "nt", "hardlink semantics differ on Windows")
    def test_rejects_source_path_even_if_alias_is_a_hardlink(self):
        alias = self.root / "apparently-safe-hardlink"
        os.link(self.secret, alias)
        self.assertEqual(alias.stat().st_ino, self.secret.stat().st_ino)
        item = entry("notes.txt", b"authorised fictional bytes")
        item["source_path"] = str(alias)
        self.assert_refused_before_output(envelope(item))
        self.assertEqual(self.secret.read_bytes(), SYNTHETIC_SECRET)

    def test_rejects_unsafe_names(self):
        for name in ("../notes.txt", "/tmp/notes.txt", "nested/notes.txt",
                     "something.json", "notes.txt\\x", "."):
            with self.subTest(name=name):
                self.assert_refused_before_output(envelope(entry(name, b"fixture")))

    def test_rejects_wrong_or_missing_digest(self):
        item = entry("notes.txt", b"fixture")
        item["sha256"] = "0" * 64
        self.assert_refused_before_output(envelope(item))

    def test_rejects_duplicate_names_before_any_write(self):
        item = entry("notes.txt", b"fixture")
        self.assert_refused_before_output(envelope(item, item))

    def test_rejects_second_invalid_item_before_first_is_written(self):
        item = entry("notes.txt", b"safe")
        invalid = entry("settings.json", b"safe")
        invalid["content_b64"] = "***"
        self.assert_refused_before_output(envelope(item, invalid))

    def test_rejects_unexpected_envelope_field(self):
        payload = envelope(entry("notes.txt", b"safe"))
        payload["directory_to_scan"] = str(self.protected)
        self.assert_refused_before_output(payload)

    def test_rejects_oversized_file(self):
        self.assert_refused_before_output(envelope(entry("notes.txt", b"a" * 65537)))

    def test_rejects_oversized_envelope(self):
        self.assert_refused_before_output(b"{" + b" " * 262145)

    def test_refuses_preexisting_symlink_output(self):
        self.output.symlink_to(self.protected, target_is_directory=True)
        before = sorted(x.name for x in self.protected.iterdir())
        proc = self.run_receiver(envelope(entry("notes.txt", b"safe")))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(sorted(x.name for x in self.protected.iterdir()), before)
        self.assertEqual(self.secret.read_bytes(), SYNTHETIC_SECRET)

    def test_refuses_preexisting_destination_directory(self):
        self.output.mkdir()
        (self.output / "existing.txt").write_text("keep me")
        proc = self.run_receiver(envelope(entry("notes.txt", b"safe")))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual((self.output / "existing.txt").read_text(), "keep me")


if __name__ == "__main__":
    unittest.main()
