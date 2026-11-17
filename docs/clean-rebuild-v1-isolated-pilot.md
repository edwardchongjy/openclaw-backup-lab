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

## Completed full-runtime container pilot — synthetic-only PASS (2026-11-17)

- [Actions #44062012816](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44062012816), commit `8b77a0d1753a4ab3740cbb90480f7697ce823c54`: actual pinned public OpenClaw `2026.10.5` Gateway, fictional Agent, and local deterministic fake model ran *inside the same full Docker container*. The real Agent received `FULL_CONTAINER_PING_20261117`, contacted the synthetic provider at 127.0.0.1:19042, and returned exactly `FULL_CONTAINER_FAKE_REPLY_20261117`.
- Runner-log PASS: `REAL_OPENCLAW_CONTAINER_NONROOT_UID`, `REAL_OPENCLAW_CONTAINER_HOST_MARKER_UNSEEN`, `REAL_OPENCLAW_CONTAINER_NO_DOCKER_SOCKET`, `REAL_OPENCLAW_CONTAINER_READ_ONLY_SOURCE`, `REAL_OPENCLAW_CONTAINER_IPV4_NO_EGRESS`, `REAL_OPENCLAW_CONTAINER_IPV6_NO_EGRESS`, `REAL_OPENCLAW_CONTAINER_AGENT_REGISTERED`, `REAL_OPENCLAW_CONTAINER_FAKE_PROVIDER_LOOPBACK`, `REAL_OPENCLAW_CONTAINER_GATEWAY_READY`, `REAL_OPENCLAW_CONTAINER_BAD_TOKEN_REJECTED`, `REAL_OPENCLAW_CONTAINER_GATEWAY_AGENT_VISIBLE`, `REAL_OPENCLAW_FULL_CONTAINER_FAKE_TURN`, `REAL_OPENCLAW_CONTAINER_NO_HOST_MOUNTS`, `REAL_OPENCLAW_CONTAINER_NO_EGRESS_NONROOT_READONLY`, `REAL_OPENCLAW_CONTAINER_LIMITS_AND_TMPFS`.
- Actual Docker inspect enforced: `NetworkMode=none`, no host bind mounts/volumes/devices, no port publication, read-only rootfs, nonroot UID, dropped all capabilities, no new privileges, process/memory/CPU limits, only isolated temporary writable state. Public base-image resolved to `node@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203`; image build ID `sha256:f84f26c5f322e45e3351bf8219020522a842f9d2043ac18f27e1a87e885b5ef2` is evidence only and not distributed or deployed.
- **Limits remain material:** build-time public dependency installation on network-enabled ephemeral runner; mutable image-tag resolution before digest recording; no full supply-chain attestation or adversarial plugin/subprocess execution tests; fake model only; no durable service, live channels, credentials, Mac mini, old data, personal data, backup integration inside this exact runtime container, or production G0–G7 acceptance. This is neither independent certification nor authority to touch the actual host.

## Completed isolated persistent-state restart pilot — PASS (2026-11-17)

- [Actions #44076015253](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44076015253), candidate commit `a5e7d2d1972f4ed5c748fc1b28b5970a850b862e`: actual pinned OpenClaw `2026.10.5` built from public sources, first booted inside a restricted full container. It created fictional workspace marker, registered `ci-contained` Agent, wrote its synthetic config and answered through a loopback fake model.
- Original container was **deleted**. A second new container using the **identical image** and **same newly created Docker-managed named volume** verified the existing marker, workspace and config, enumerated the existing Agent **without recreating it**, checked config, started the Gateway and repeated a successful fake model turn. Exact runner markers: `ORIGINAL_CONTAINER_REMOVED_BUT_NEW_VOLUME_RETAINED=PASS`, `RESTARTED_STATE_AND_WORKSPACE_PROVEN_SAME=PASS`, `RESTARTED_OPENCLAW_AGENT_RETAINED=PASS`, `RESTARTED_CONTAINER_FAKE_AGENT_TURN=PASS`, `FRESH_OPENCLAW_STATE_RESTORED_AFTER_CONTAINER_DELETION=PASS`.
- A separate newly created, labelled **corrupt synthetic volume** with a deliberately wrong fictional marker (and malformed synthetic config) was rejected **before Gateway startup**. `CORRUPTED_FICTIONAL_STATE_REFUSED_BEFORE_GATEWAY=PASS` is narrow: it proves denial on the explicit *fictional marker* integrity check, not full schema validation, all possible OpenClaw corruption classes, automatic repair, or a real backup/restore workflow.
- `docker inspect` after each container verified: exactly **one intentionally authorised Docker-managed named volume** mounted at `/home/ci`, **no host-path bind mount**, no host Docker socket, no published ports, `NetworkMode=none`, read-only container root, UID 10001, all Linux capabilities dropped, no-new-privileges, resource limits and a small isolated `/tmp`. Both named volumes were checked for newly created `local` type and this GitHub run's labels. Container names and volumes were disposed at job exit.
- **Important boundary distinction:** persistence *requires* a Docker-managed storage mount (the named volume); therefore this test intentionally differs from the earlier **zero-mount** proof. The named volume is on the **disposable GitHub runner host's Docker storage**; it is not a bind of a local Mac folder, not a guarantee of encryption or backup, and **must never be reused as permission to attach real historical data**. The runner and test volume are not a durable production environment.
- **Still NOT proven:** survival across destruction of the *GitHub runner/host* or VM, external backup and recovery under total host loss, encryption at rest, software supply-chain attestation, non-fictional AI/provider credentials and channels, full malicious-plugin/tool tests, actual Mac isolation and G0–G7 production safety. Production NO-GO dominates. No real system was touched.

## Formerly outstanding test — preserved acceptance criteria (now tested with fictional data)



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
