# Pinned OpenClaw backup source inventory — public reference only

**Status: source-code classification, not a live host inventory and not recovery acceptance.**

Source: `openclaw/openclaw` version `2026.10.5`, pinned commit
`1b58cb9a1b4f4353e1add63c8506db4d890962e8`. All evidence is
from the public repository. This experiment must not open, hash, stat,
list, resolve, or otherwise access any historical private archive or its
aliases/ancestors, live OpenClaw installation, Mac mini or Hermes data.

The JSON file `pinned-upstream-backup-policy.json` identifies **18 resource
groups or backup limitations**, each paired with an exact text anchor in
pinned upstream public code/docs. These anchors are verified in GitHub
Actions by `verify_policy.py`. They are descriptions of the pinned
**software's potential behaviour**, not proof of what any individual's
installation contains.

## Recovery-relevant groups

| Group | Official archive semantics | Real-system evidence |
| --- | --- | --- |
| Active config and all `$include` dependencies | Full archive; includes may reside beyond state/workspace roots | UNKNOWN |
| OpenClaw state, sessions and credentials | Full archive, including separately configured credential roots | UNKNOWN |
| Configured workspaces and custom agent roots | Discovered based on runtime config; `--no-include-workspace` does not forbid config dependency reads | UNKNOWN |
| Global and per-agent SQLite | Require consistent, owned snapshots; copy completed snapshot output, **not live SQLite / WAL / SHM** | UNKNOWN |
| Managed skills and plugin resources | Conditional discovery and plugin resource dispositions; dynamic ownership | UNKNOWN |
| Private update captures and protected historical copies | Not authorised for reads; published name patterns and exclusions alone **do not prove zero-contact** | PROHIBITED |
| Volatile state and generated/plugin dependencies | Some omitted or regenerated after restore | UNKNOWN |
| Backup manifest, validation, encryption and restore staging | Necessary but not a complete application-level recovery guarantee | UNVERIFIED |

## Constraints that matter in practice

- `--only-config` excludes even necessary `$include` dependencies and is
  insufficient for a full modular-config restore.
- `--no-include-workspace` still includes required config dependencies,
  **including ones within an otherwise excluded workspace**.
- Separate SQLite captures and config are not one atomic recovery checkpoint.
  Only selected consistency and ownership guarantees have been demonstrated
  in the upstream implementation; there is no actual recovery evidence.
- Some plugin snapshots are opaque during archive verification. Missing
  plugin `node_modules` and generated indexes need rebuilding on recovery.
- A locally retained archive may be unencrypted plaintext even when offsite
  storage has encryption enabled. Configuration and SQLite data may contain
  sensitive credentials.
- The supported restore target is a fresh staging directory. Activation and
  safe resumption are separate operational decisions.
- Existing tests found config alias reads through symlinks/hardlinks before
  the proposed backup exclusions. This inventory **does not fix those bugs**.

## Acceptance gates (no automatic upgrade)

The inventory intentionally leaves every operational gate unapproved:
**no verified source provenance; no real OS-enforced forbidden-path isolation;
no complete resource coverage; no real restore; no approved writer gates;
and six outstanding P0 controls.** The pinned public facts are still to be
reconciled with whichever version is eventually deployed.

The verifier hardcodes the permitted evidence file set and expected
classification so the JSON cannot silently relabel private copies as
ordinary data, claim a live host scan took place, or change the final
production decision from **NO-GO**.

## Reproducibility

GitHub Actions workflow:
[`validate-pinned-backup-inventory.yml`](../.github/workflows/validate-pinned-backup-inventory.yml).

It checks out the exact publicly pinned upstream commit, validates the JSON
shape and evidence references, and runs negative tests that reject missing
categories, changed upstream pins, false approvals, removed writer gates and
expanded permissions.

**Next meaningful gate:** establish a separately reviewed and genuinely
enforced source-authorisation/identity boundary without contacting protected
historical assets. Until then: **no live backup, restore, upgrade or
automatic promotion of results.**
