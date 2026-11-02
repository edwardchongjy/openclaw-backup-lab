# ADR-001: Clean-room baseline first; no live-source migration

- **Decision status:** SELECTED FOR DESIGN ONLY (2026-11-02).
- **Production disposition:** **NO-GO**.
- **Authority:** This is a public engineering recommendation, **not** authority
  to inspect, copy, back up, restore, modify, start or upgrade any real service.
- **Applies to:** OpenClaw independent recovery planning only. Hermes is
  outside this project. All protected historical archive material, its aliases
  and ancestors remain NO-CONTACT, including any `exists`, list, stat,
  realpath, hash, marker or other query.

## Verified disposable cloud baseline experiment — 2026-11-02

GitHub Actions run **41520391394** completed successfully using **two independent
GitHub-hosted Ubuntu 24.04 runner jobs**. This is evidence for a **cloud
prototype only**, not acceptance of the production Mac's isolation.

**Preflight job (PASS):**
- Identified a GitHub-hosted, unprivileged Linux runner.
- Confirmed none of a defined set of OpenClaw, Hermes, provider or channel
  credential **environment variable names** were present. This is a bounded
  check; it does not prove that the runner has no credential or network access.
- Created a fresh private empty HOME/state/workspace scratch tree, with no
  user-supplied data sources or existing setup.

**Baseline job (PASS):**
- Checked out only public OpenClaw source pinned to
  `1b58cb9a1b4f4353e1add63c8506db4d890962e8` (version
  `2026.10.5`) using a checkout that does not persist credentials.
- Used Node `24.16.0`, pnpm `12.9.0`, frozen dependencies.
- Executed **`setup --baseline --skip-bootstrap`** in a separately generated
  scratch HOME via an environment allowlist. Did **not** execute onboarding,
  imports, real channel setup, Gateway activation or a restore.
- Verified a fresh config was created, the fresh workspace existed,
  `skipBootstrap: true` was saved, and no explicit auth/channel config
  keys were generated. After the command exited, the default local Gateway
  port did not have a listening service.

**Limits and open gates:**
- Port not listening **after** setup does not prove there was never a
  transient Gateway or network connection. No kernel-level no-egress
  sandbox or process audit was performed.
- Running in a public GitHub-hosted Linux runner is not proof about the
  actual Mac, its filesystems, user credentials, mounted volumes, or
  access via alias/inode. The repository checkout and package-manager
  dependencies used normal internet connectivity.
- C0–C2 may be marked **CLOUD_TEST_PASS within this one disposable run only**.
  All production C0–C4 gates remain **UNVERIFIED / NOT AUTHORISED**.
- This is a **clean installation baseline**. No user OpenClaw data, agent
  memory, sessions, credentials or workflows were transferred; real
  backup/restore remains 0; writer gates 0/7 and six P0 remain open.

[See the exact GitHub Actions run](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/41520391394).

**One next meaningful decision:** whether to treat fresh-install-only
reconstruction as a distinct recovery objective, rather than imply that
migrating existing state is now safe. The missing first-mile source
authorisation and real Mac zero-contact isolation remain independent
blockers. No production activation should follow automatically.

## The engineering choice

**Choose:** Build an independently provisioned **clean-room, zero-import**
OpenClaw baseline on a separately controlled machine or fully isolated
environment with separate storage. This would establish a future *fresh
installation* path **without importing any live configuration, credentials,
backup, workspace, agent database, plugins, model access or channel identity**.

**Do not choose yet:** Copying a live Mac OpenClaw tree into an allowlisted
directory, asking the current full-access user to stage files, changing
protected permissions, taking a volume snapshot, mounting existing disks,
running native `openclaw backup` on the Mac, or promoting current GitHub
synthetic fixtures to an accepted real restore.

**Why:** The preceding public CI reproduces pre-plan config alias reads, and
the earlier Mac sandbox admission reported `sandbox_init: Operation not
permitted`. Path-only filtering is not a proven safe boundary for aliases
or early source reads. New environment with no original storage is a
stronger *environment separation* decision, but it does **not** solve the
first-mile provenance problem of moving existing data.

## Selected clean-room boundary

1. **Storage:** new independently provisioned storage. No Mac mini disk,
   APFS snapshot, attached volume, synced home directory, network filesystem,
   drive clone, host bind mount, or mount of any private history. Do not
   reconstruct historical data via public CI or fixtures.
2. **Identity:** dedicated non-privileged account, fresh home directory,
   isolated project state, no inherited Mac login, SSH agent, browser
   profile, keychain, cloud token, VPN mesh endpoint, or credentials.
3. **Connectivity:** do not connect to the production Gateway, Discord,
   messaging channels, webhook targets, production databases, automation
   endpoints or Mac mini. No public-facing Gateway, remote bind, tunnels,
   or real channel or provider credentials.
4. **Startup:** phase 0 should **not** start a service, agent, Gateway,
   provider completion, onboarding with account discovery, or auto-import.
   No `openclaw gateway install`, `start`, `onboard`, `--import-from`,
   or generic install command that implicitly onboards.
5. **Code provenance:** after independent environment admission, fetch
   only approved public upstream code from an exact commit/tag with a
   recorded Node/toolchain revision and package-lock integrity. Do not
   execute `latest` without a separate version/security review.
6. **First installation step (future, NOT authorised here):** use a verified
   installer **without automatic onboarding**, then the officially
   documented baseline-only config/workspace flow where suitable.
   `openclaw setup --baseline` is the documented configuration-only
   entrypoint; it must be executed strictly inside the approved empty
   isolated environment and never against a discovered existing home.
7. **No inherited access:** never give the new environment the production
   filesystem, token, app network, secrets, plugin external credentials,
   or unreviewed backup archive even temporarily.
8. **Audit:** record environment ID, source image identity and mounts,
   identity and permissions, actual running process tree, code/toolchain
   revision, zero imported files/credentials, and independent observer.
   If any part cannot be established, FAIL CLOSED.

### Evidence needed to admit phase 0 (not currently obtained)

| Gate | Exact requirement | Current status |
| --- | --- | --- |
| C0 independent storage | A new storage identity and mount map show no protected or production source was attached, with no forbidden-path probe | **UNVERIFIED** |
| C1 independent account | A fresh restricted identity has no production secret, home, keychain or inherited environment | **UNVERIFIED** |
| C2 offline service | No live channel, real provider credential, production Gateway, service install or writer process can be contacted or started | **UNVERIFIED** |
| C3 pinned code | Reviewed public source and matching toolchain identified before installation | **DESIGNED, not provisioned** |
| C4 safe baseline | Config-only baseline can be created on entirely new storage without importing or activating anything | **NOT EXECUTED** |

**Do not call C0–C4 PASS based on GitHub tests.** In particular, a VM
on the Mac is not admitted just because it is called a VM; source disks,
host shares, bridged networking, cloud drive sync and inherited tokens
must be independently excluded. A container with host mounts or a
full-privilege Gateway is not an acceptable substitute.

## Source migration remains separately blocked

**Zero-import baseline** and **full recovery of the user's existing
OpenClaw identity/state** are different objectives. Never interpret
successful clean install, successful synthetic restore, or even database
integrity as complete recovery of actual agent behavior.

To consider migration later, G0–G3 of
[`production-isolation-admission.md`](./production-isolation-admission.md)
must have independent evidence:

- a trusted data authority that can establish each original data source
  without any operation on protected history (even indirectly);
- a genuinely enforced privilege/mount separation between permitted
  data and every prohibited inode/alias/ancestor;
- an explicit schema and restore responsibility for active config and
  includes, runtime state, per-agent state and SQLite, workspaces,
  external plugin assets, credentials, secrets and sessions;
- a fail-closed completeness statement: if required assets cannot be
  lawfully attested, full restoration must remain **BLOCKED**, not
  silently become a partial backup with a `verify` green tick.

If the source authority cannot solve this, present the user with a
future *new identity/new state* rebuild and a clear list of what would
be lost, instead of proposing an unverified full migration. This
decision **does not authorise discarding or altering the original**.

## Stage and stop rule

- **Now:** research/design only; the chosen architecture and phase-0
  acceptance conditions are recorded. No new private access is granted.
- **Next independently actionable stage:** verify that a **wholly fresh
  off-host environment** with no shared data, service integration, or
  credentials can be provisioned by an authorised operator under C0–C2.
  Once evidenced, agree to a separate baseline-only setup attempt.
- **Stop:** any request for Mac mini access, protected archive
  operations, private data copy, credential reuse, channel pairing,
  gateway activation, install daemon, restore, upgrade or writer opening
  before required gates and explicit authority are met.

## Official public references

- [OpenClaw setup CLI](https://docs.openclaw.ai/cli/setup):
  `openclaw setup --baseline` initializes config/workspace without
  running onboarding or a Gateway. The bare setup command does not.
- [OpenClaw install](https://docs.openclaw.ai/install):
  the supported installer can start onboarding; `--no-onboard` is
  documented for installation without the wizard.
- [OpenClaw security trust model](https://docs.openclaw.ai/gateway/security/trust-model):
  separate trust boundaries by OS account/host; broad host tool
  execution is not a strict boundary.
- [OpenClaw onboarding](https://docs.openclaw.ai/start/onboarding-overview):
  normal guided activation can select existing inference credentials,
  start a Gateway and configure channels.
- [OpenClaw container/network storage docs](https://docs.openclaw.ai/install/docker/networking-and-storage):
  host volumes and service networking are separate trust decisions.

**Related completed public evidence:** synthetic selector tests at
GitHub Actions run `41393710107`; public inventory test `41402913495`;
config alias diagnostic `41314455489`. None of these are real host
acceptance or real application recovery.

**Real backup = 0; real restore = 0; writer gates = 0/7; six P0 remain
open. Production backup, restore, upgrade and activation: NO-GO.**
