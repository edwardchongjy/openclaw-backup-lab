"""Validate a pinned *public-source* OpenClaw backup scope inventory.

Never inspect local home directories, live OpenClaw state, or mounted files.
The only accepted upstream evidence files are constant public source paths.
All production gates are forced to NO_GO / OPEN or UNVERIFIED.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

VERSION = "2026.10.5"
PIN = "1b58cb9a1b4f4353e1add63c8506db4d890962e8"
SCHEMA = "edwrd-official-backup-scope-inventory/v1"
REPOSITORY = "openclaw/openclaw"

# These are code-reviewed expected assertions; editable JSON cannot silently
# change expected upstream text, categories or permission to claim readiness.
SOURCES = {
    "config_source_paths": ("src/commands/backup-shared.ts", '{ kind: "config" as const, sourcePath: path.resolve(configPath) }'),
    "includes_outside_state": ("docs/cli/backup.md", "including dependencies outside the state directory"),
    "state_candidate": ("src/commands/backup-shared.ts", '{ kind: "state", sourcePath: path.resolve(stateDir) }'),
    "oauth_candidate": ("src/commands/backup-shared.ts", '{ kind: "credentials" as const, sourcePath: path.resolve(oauthDir) }'),
    "workspace_candidate": ("src/commands/backup-shared.ts", '...workspaceDirs.map((workspaceDir) => ({'),
    "agent_candidate": ("src/commands/backup-shared.ts", '...agentRoots.map((root) => ({ kind: "agent" as const, sourcePath: root.sourcePath }))'),
    "global_database": ("docs/cli/backup.md", "Shared OpenClaw state"),
    "agent_database": ("docs/cli/backup.md", "One per-agent database"),
    "plugin_disposition": ("src/commands/backup-resource-inventory.ts", 'resource.disposition === "include"'),
    "managed_skill_candidate": ("src/commands/backup-shared.ts", 'kind: "managed skill"'),
    "private_update_captures": ("docs/cli/backup.md", "root is excluded from ordinary archives"),
    "regenerable_roots": ("src/commands/backup-resource-inventory.ts", 'exclude("managed state", path.join(stateDir, root))'),
    "plugin_modules_omitted": ("docs/cli/backup.md", "Plugin `node_modules` trees"),
    "config_only_limit": ("docs/cli/backup.md", "not** its `$include` dependencies"),
    "verify_gap": ("docs/cli/backup.md", "remain opaque during verification and restore"),
    "restore_not_in_place": ("docs/cli/backup.md", "It never restores in place and has no `--force` mode"),
    "nonatomic_snapshot": ("docs/cli/backup.md", "not one atomic snapshot across config and all databases"),
    "plain_local_copy": ("docs/cli/backup.md", "ordinary plaintext"),
}
CATEGORIES = {
    "active_config": ("include_for_full", "config_source_paths"),
    "config_include_dependencies": ("include_for_full", "includes_outside_state"),
    "state_tree": ("include_for_full", "state_candidate"),
    "credentials": ("include_for_full", "oauth_candidate"),
    "workspaces": ("optional_for_full", "workspace_candidate"),
    "agent_roots": ("include_for_full", "agent_candidate"),
    "global_sqlite": ("special_consistent_snapshot", "global_database"),
    "agent_sqlite": ("special_consistent_snapshot", "agent_database"),
    "plugin_resources": ("conditional_by_plugin_manifest", "plugin_disposition"),
    "managed_skill_resources": ("conditional_by_discovery", "managed_skill_candidate"),
    "private_update_captures": ("never_contact", "private_update_captures"),
    "volatile_and_regenerable": ("exclude_or_rebuild", "regenerable_roots"),
    "plugin_modules_and_generated_index": ("rebuild_after_restore", "plugin_modules_omitted"),
    "only_config_mode": ("insufficient_for_full_restore", "config_only_limit"),
    "archive_verification": ("required_but_not_sufficient", "verify_gap"),
    "restore_staging": ("fresh_target_only", "restore_not_in_place"),
    "cross_db_consistency": ("cannot_claim_atomic", "nonatomic_snapshot"),
    "offsite_and_plaintext": ("must_review_encryption", "plain_local_copy"),
}
GATES = {
    "inventory_source_drift": "UNVERIFIED",
    "source_origin_authorisation": "OPEN",
    "s10_no_contact_os_enforcement": "OPEN",
    "full_resource_coverage": "OPEN",
    "backup_integrity": "OPEN",
    "verified_real_restore": "OPEN",
    "writer_safety": "OPEN",
    "six_p0": "OPEN",
}


class InventoryRejected(ValueError):
    pass


def reject_if(condition: bool, reason: str) -> None:
    if condition:
        raise InventoryRejected(reason)


def validate_policy_shape(policy: dict) -> None:
    reject_if(not isinstance(policy, dict), "policy must be object")
    reject_if(set(policy) != {
        "schema", "upstream", "origin", "permission", "current_host_evidence",
        "production_decision", "rules", "evidence", "acceptance_gates"
    }, "policy unexpected or missing top-level fields")
    reject_if(policy["schema"] != SCHEMA, "schema mismatch")
    reject_if(policy["upstream"] != {
        "repository": REPOSITORY, "commit": PIN, "version": VERSION
    }, "upstream pin mismatch")
    reject_if(policy["permission"] != "READ_PUBLIC_UPSTREAM_ONLY", "permission scope widened")
    reject_if(policy["production_decision"] != "NO_GO", "unjustified production approval")
    reject_if(policy["current_host_evidence"] != "UNKNOWN_NOT_REQUESTED", "host evidence wrongly asserted")
    reject_if(not isinstance(policy["origin"], str) or
              "Not discovered from any user host" not in policy["origin"],
              "provenance warning missing")

    rules = policy["rules"]
    reject_if(not isinstance(rules, list) or len(rules) != len(CATEGORIES),
              "resource-category inventory incomplete")
    seen = set()
    for rule in rules:
        reject_if(not isinstance(rule, dict) or set(rule) != {
            "id", "category", "risk", "is_dynamic", "classification", "evidence_key"
        }, "unexpected category shape")
        ident = rule["id"]
        reject_if(not isinstance(ident, str) or ident not in CATEGORIES or ident in seen,
                  "unexpected or duplicate resource category")
        seen.add(ident)
        reject_if((rule["category"], rule["evidence_key"]) != CATEGORIES[ident],
                  "category silently changed")
        reject_if(rule["risk"] not in {"sensitive","secret","restricted","operational","incomplete","integrity"},
                  "invalid sensitivity classification")
        reject_if(type(rule["is_dynamic"]) is not bool, "dynamic flag must be bool")
        reject_if(not isinstance(rule["classification"], str) or len(rule["classification"]) < 15,
                  "classification explanation missing")
    reject_if(seen != set(CATEGORIES), "resource categories missing")

    evidence = policy["evidence"]
    reject_if(not isinstance(evidence, list) or len(evidence) != len(SOURCES),
              "source evidence incomplete")
    observed = set()
    for item in evidence:
        reject_if(not isinstance(item, dict) or set(item) != {"key","file","contains"},
                  "unexpected evidence shape")
        key = item["key"]
        reject_if(not isinstance(key, str) or key not in SOURCES or key in observed,
                  "unknown or duplicate source evidence")
        observed.add(key)
        reject_if((item["file"], item["contains"]) != SOURCES[key],
                  "source claim differs from pinned public-code assertion")
    reject_if(observed != set(SOURCES), "missing evidence keys")

    gates = policy["acceptance_gates"]
    reject_if(not isinstance(gates, list) or len(gates) != len(GATES),
              "production gates incomplete")
    seen = set()
    for gate in gates:
        reject_if(not isinstance(gate, dict) or set(gate) != {"id","status","condition"},
                  "invalid gate shape")
        ident = gate["id"]
        reject_if(not isinstance(ident, str) or ident not in GATES or ident in seen,
                  "unknown or duplicate gate")
        seen.add(ident)
        reject_if(gate["status"] != GATES[ident], "production readiness falsely upgraded")
        reject_if(not isinstance(gate["condition"], str) or len(gate["condition"]) < 15,
                  "missing acceptance condition")
    reject_if(seen != set(GATES), "missing required gate")


def check_public_upstream_only(upstream: Path) -> None:
    # The GitHub-hosted workflow checks out this exact public revision. The
    # validator still rejects any other checkout before opening the evidence.
    process = subprocess.run(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"],
        check=False, text=True, capture_output=True,
    )
    reject_if(process.returncode != 0 or process.stdout.strip() != PIN,
              "public upstream checkout not at approved commit")
    pkg = json.loads((upstream / "package.json").read_text(encoding="utf-8"))
    reject_if(pkg.get("version") != VERSION, "pinned package version unexpected")

    for relative, snippet in sorted(set(SOURCES.values())):
        content = (upstream / relative).read_text(encoding="utf-8")
        reject_if(snippet not in content, "public upstream scope evidence drift detected")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--policy", type=Path,
                        default=Path(__file__).with_name("pinned-upstream-backup-policy.json"))
    args = parser.parse_args()
    try:
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        validate_policy_shape(policy)
        check_public_upstream_only(args.upstream)
    except (InventoryRejected, OSError, ValueError) as exc:
        print(f"INVENTORY_REJECTED: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(f"PINNED_PUBLIC_SCOPE_PASS: {len(CATEGORIES)} categories, {len(SOURCES)} upstream checks")
    print("CURRENT_HOST=UNKNOWN; REAL_SOURCE_PROVENANCE=UNKNOWN; S10_ZERO_CONTACT=UNVERIFIED")
    print("PRODUCTION_BACKUP_RESTORE_UPGRADE=NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
