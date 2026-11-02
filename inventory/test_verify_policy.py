"""Read-only fixture tests for the pinned public OpenClaw scope policy."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

import verify_policy as policy

HERE = Path(__file__).resolve().parent
POLICY_PATH = HERE / "pinned-upstream-backup-policy.json"


class PinnedPublicScopeTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def rejected(self, mutation):
        modified = copy.deepcopy(self.document)
        mutation(modified)
        with self.assertRaises(policy.InventoryRejected):
            policy.validate_policy_shape(modified)

    def test_complete_public_inventory_is_well_formed_without_host_access(self):
        policy.validate_policy_shape(self.document)

    def test_rejects_wrong_upstream_commit(self):
        self.rejected(lambda x: x["upstream"].update(commit="0" * 40))

    def test_rejects_wrong_version(self):
        self.rejected(lambda x: x["upstream"].update(version="0.0.0"))

    def test_rejects_extra_unreviewed_source_category(self):
        self.rejected(lambda x: x["rules"].append(copy.deepcopy(x["rules"][0])))

    def test_rejects_missing_credentials_category(self):
        self.rejected(lambda x: x["rules"].__setitem__(slice(None), [
            r for r in x["rules"] if r["id"] != "credentials"
        ]))

    def test_rejects_private_capture_promoted_to_included(self):
        def change(x):
            next(r for r in x["rules"] if r["id"] == "private_update_captures")["category"] = "include_for_full"
        self.rejected(change)

    def test_rejects_config_only_claimed_as_complete(self):
        def change(x):
            next(r for r in x["rules"] if r["id"] == "only_config_mode")["category"] = "include_for_full"
        self.rejected(change)

    def test_rejects_unverified_real_restore_upgraded_to_pass(self):
        def change(x):
            next(g for g in x["acceptance_gates"] if g["id"] == "verified_real_restore")["status"] = "PASS"
        self.rejected(change)

    def test_rejects_s10_no_contact_claimed_proven(self):
        def change(x):
            next(g for g in x["acceptance_gates"] if g["id"] == "s10_no_contact_os_enforcement")["status"] = "PASS"
        self.rejected(change)

    def test_rejects_current_host_evidence_claimed_known(self):
        self.rejected(lambda x: x.update(current_host_evidence="PASS"))

    def test_rejects_production_go_claim(self):
        self.rejected(lambda x: x.update(production_decision="GO"))

    def test_rejects_permission_widening(self):
        self.rejected(lambda x: x.update(permission="READ_USER_MAC"))

    def test_rejects_changed_evidence_anchor(self):
        def change(x):
            x["evidence"][0]["contains"] = "unreviewed arbitrary claim"
        self.rejected(change)

    def test_rejects_missing_evidence(self):
        self.rejected(lambda x: x["evidence"].pop())

    def test_rejects_duplicate_evidence(self):
        def change(x):
            x["evidence"][0] = copy.deepcopy(x["evidence"][1])
        self.rejected(change)

    def test_rejects_unreviewed_evidence_path(self):
        def change(x):
            x["evidence"][0]["file"] = "personal/local-file"
        self.rejected(change)

    def test_rejects_missing_writer_gate(self):
        self.rejected(lambda x: x["acceptance_gates"].__setitem__(slice(None), [
            g for g in x["acceptance_gates"] if g["id"] != "writer_safety"
        ]))

    def test_rejects_silent_status_reclassification(self):
        def change(x):
            next(g for g in x["acceptance_gates"] if g["id"] == "inventory_source_drift")["status"] = "PASS"
        self.rejected(change)

    def test_rejects_mutated_scope(self):
        self.rejected(lambda x: x.update(schema="fake/v2"))

    def test_rejects_policy_disguised_as_more_complete(self):
        self.rejected(lambda x: x.update(unreviewed_local_evidence=True))


if __name__ == "__main__":
    unittest.main()
