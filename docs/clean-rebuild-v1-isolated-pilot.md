# Clean Rebuild v1: independent new-install pilot — design, not deployment

**State (2026-11-17):** PUBLIC FICTION-ONLY LAB. No migration, restoration, deployment, release approval, or contact with the existing OpenClaw/Hermes host. This document is not a full security certification.

## Operator model and goal

This project is jointly operated by the repository owner and ChatGPT. No external human reviewer is a required *participant in the design or experimentation*; however, self-review must never be described as independent certification. The existing GitHub `main` protection (1 independent approval) remains untouched and may block merge until an explicitly authorised governance decision is made later.

**Goal:** start a brand-new OpenClaw, with a brand-new fictional Agent, that cannot read files belonging to another installation and cannot call outside networks during its first validation. No old state or credentials will be imported. Prove real runtime behaviour *before* asking the owner to approve a separately isolated use environment.

## Boundary choice

- Prefer a distinct machine/VM or disposable hosted test runner where the previous system's volumes were **never made available**. The first pilot takes place only on GitHub-hosted Linux.
- For the actual full Gateway use an *entire-container boundary*: OpenClaw Gateway, config, workspaces, and fictional model server run inside the constrained runtime. **Agent tool sandboxing alone is insufficient** because the Gateway and native plugins remain outside the tool sandbox.
- Runtime policy for first pilot: `--network none`, no published ports, `--read-only`, distinct non-root UID, `--cap-drop ALL`, `no-new-privileges`, limited processes/memory/CPU, no privileged mode, no host volumes/bind mounts, no host Docker socket. Writable test state is temporary and explicitly scoped; only loopback is permitted for the fake provider.
- No real AI keys, Discord/Telegram credentials, outside messaging, plugins, browser control, system-shell privileges, or real personal/brand data.
- Public source is pinned to OpenClaw `2026.10.5` @ `1b58cb9a1b4f4353e1add63c8506db4d890962e8`, the version already functionally tested. Re-evaluate pin and dependency provenance in a separate, explicit change, not silently on pilot creation.
- Resolve/dependency installation is a **build-time** stage with different privileges and network properties, not a runtime security proof. Obtain provenance and inspect scripts; only a frozen built image is allowed in the no-egress test. No claim of zero build-time network activity.

## Completed, strictly limited evidence

- [Actions #43987555046](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/43987555046): pinned public OpenClaw successfully backed up and restored **fictional** data across two disposable runners, and the restored Agent answered through a local fake model.
- [Actions #43986070013](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/43986070013): actual OpenClaw CLI/Gateway/fake turn under a low-privilege user and Linux no-route network namespace, but **not a complete filesystem sandbox**.
- [Actions #44060787130](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44060787130): full Docker boundary with a **small synthetic proof executable only**: non-root, host-only fictional marker unseen, immutable root, bounded scratch, only local message, no IPv4/IPv6 egress, and independent `docker inspect` verified no host mounts, read-only filesystem, no network, no privilege. This is **not** a real OpenClaw-in-container test.

## Next lab acceptance: real OpenClaw in the strict full-container boundary

1. Build a disposable image from *only* pinned public source and publicly downloaded dependencies; record source and image digests. The build host stays disposable and contains no private data. No host volume may be attached to the candidate.
2. Start the complete OpenClaw Gateway and synthetic fake provider **within one container** using a dedicated UID and fresh temporary state/workspace. No host bind, socket, protected or home directory mount. Do not connect a real provider.
3. Inspect actual container settings **and** process/user identity: assert exact no-network/no-bind/read-only/non-privileged policy. Abort if any check fails.
4. Verify loopback Gateway listener; wrong credential is rejected; fictional Agent registration; fake model actually receives one known test question and Agent returns the exact predetermined response.
5. Prove outside IPv4/IPv6 connections fail, host-only synthetic marker cannot be read, and writes cannot reach the container's immutable root. Check no hidden host Docker socket. Record failure cases; do not relax the policy to force a green result.
6. Exit and discard the entire container, temporary state and synthetic data, keeping only nonsensitive test output and image digest for the review trail.

**Gate outcome:** a PASS here certifies only a controlled *test-container run* of the pinned OpenClaw build. It cannot certify a Mac mini installation, independent source authority, production secrets/channels, full filesystem safety on every host, or G0–G7 production approval.

## Explicit future decision, not performed now

Only if the full-container pilot passes, discuss a separately isolated environment for a **fresh installation**, with a narrow first real use case. Choosing hosting, credentials, access/network permissions, backup retention, monitoring and shutdown behaviour is a later authorised phase. Do not infer consent to operate on the existing Mac mini or import old OpenClaw/Hermes content.

**STOP / NO-GO:** Any need to inspect historic paths or aliases; host volume exposure; unexpected network egress; unsigned provenance; running as root; missing isolation; unreviewed new privileges; real secret in public CI; or failure of any negative test.

**Main branch:** keep PR #1 draft/unmerged, preserve branch protection until a deliberate owner-approved governance revision, with any lack of independent review reported honestly.
