# Production isolation admission gate — DESIGN ONLY (NO-GO)

**Scope:** OpenClaw backup and recovery engineering. This is a public, non-secret
acceptance contract, not a script, a grant of permission, a restoration guide,
or evidence that any real Mac has passed.

**Current disposition (2026-11-02): NO-GO.** No authorised production backup,
restore, upgrade, release, or writer activation. Historical protected evidence,
including **every name or alias and its ancestor chain**, is a **NO-CONTACT**
surface: no directory listing, existence check, LSTAT, STAT, READ, hashing,
REALPATH, copying, marker probing, write, or deletion. No production `~/.openclaw`
inspection or Hermes operations are authorised by this document.

## Grounded evidence to date

- Public test repository is `edwardchongjy/openclaw-backup-lab`. Its pinned
  upstream version is OpenClaw `2026.10.5`, commit
  `1b58cb9a1b4f4353e1add63c8506db4d890962e8`.
- GitHub Actions `41393710107`: 39/39 synthetic fixture tests on macOS,
  39/39 synthetic fixture tests on Linux, with a separate Linux UID fixture
  proving narrow direct / symlink / hardlink denial and successful staged
  handoff. These prove **only the test conditions on the runners**.
- GitHub Actions `41402913495`: 18 anchored **public upstream** backup
  source/policy facts and 20 policy-regression tests passed. This is **not**
  an inventory of any real user's sources or an assurance of complete
  restoration.
- GitHub Actions `41314455489`: negative synthetic tests reproduced
  attempted config reads through symlink and hardlink aliases. A green run in
  this diagnostic represents successful **detection of a bypass**, not a fix.
- Previous independent Mac runner on the user's host reported
  `sandbox_init: Operation not permitted`. The applicable host isolation
  boundary has **not** passed; cloud results cannot upgrade it.
- No independent evidence establishes which current production dataset roots
  are selected, whether linked aliases exist, or that any real source is
  isolated from protected history. Actual production recovery remains 0.

**Version warning:** Public findings are tied to the pinned upstream
revision; they are not proof of which version runs on the real host.

## Boundary: authorisation must precede every possible source operation

A backup-process allowlist is **not** sufficient if a config loader, plugin
discovery, SQLite snapshot, link resolver, logging hook, manifest builder, or
child process can access a forbidden source before the allowlist is checked.
An error such as `EACCES` says only access failed; it does not establish
whether a protected marker or file exists. Never reinterpret failure as
marker absence or silently skip it.

The design must have **two genuinely separate responsibilities**:

1. **Source authority / origin:** a trusted, independently reviewed component
   certifies a narrowly defined, positively approved recovery dataset
   *without* probing protected history. The certificate identifies the
   source *classes* and their restore obligations; it does not infer
   authorisation from path spelling, the ability to open a file, or file
   content hashes alone.
2. **Data processor:** a least-privilege process gets only authorised,
   immutable, bounded staging bytes on an isolated filesystem that cannot
   mount or otherwise access protected original data. It does not discover
   arbitrary paths, read the real configuration, follow source aliases, or
   call a privileged helper to widen its access.

If the trusted source authority cannot establish provenance for a file without
contacting protected history, **that file stays outside the recovery dataset
and completeness cannot be claimed**. This is a stop condition, not a
permission to omit a required file and still call the result a full backup.

### Why pathname-only controls do not pass

- A hardlink shares the same inode/bytes with an unapproved source even when
  its pathname is inside the allowlisted root.
- Symlinks, mount points, bind/volume aliases, ancestor traversal, generated
  or included config paths, managed skills and plugin references add further
  possible read entrances.
- Multi-link rejection is useful as a *defence in depth* but does not prove
  origin, exclude every alias form or prevent earlier data reads.
- A pathname sandbox on a GitHub Mac may deny a protected path yet allow its
  hardlink. This does not prove the real Mac is protected.
- A backup run as the normal broad-access account or root defeats the intent
  of separate-user least privilege. Do not compensate by changing protected
  permissions or introducing Full Disk Access.

**Strongly preferred design:** an independent recovery-processing machine or
VM that is **not provided** the protected disk, volume, share, mount or any
clone thereof. Only a separately approved, already-vetted immutable staging
dataset may be supplied to it. The still-unsolved part is how a trusted
least-privilege source authority creates that dataset from actual state
without prohibited contact. A separate VM does **not**, by itself, solve
that first-mile problem.

## Ordered gates — fail closed

| Gate | Required evidence (not just a claim or green CI icon) | Current |
| --- | --- | --- |
| G0 Source permission | Signed/recorded narrow source authority, explicit allowed and forbidden *classes*, operator, purpose and restore obligation, with **zero** forbidden-path probes | **OPEN** |
| G1 Host privilege | Actual host OS account/token, mounts, ACLs/entitlements and process tree independently verified; no fallback to broad-access/root | **OPEN** |
| G2 No-contact isolation | Independent OS-enforced access boundary for source and all aliases/ancestors; no direct, symlink, hardlink, volume or indirect preflight access; cannot rely on a fabricated denylist obtained by reading the forbidden tree | **OPEN** |
| G3 Source coverage | Every active config dependency, state/credential root, agent/workspace, plugin inclusion and canonical SQLite snapshot reconciled to approved recovery obligations; unknown or required-but-denied blocks completeness | **OPEN** |
| G4 Staging integrity | Restricted input, single-owner staging, immutable snapshot semantics, atomic publication/rollback, tamper and race checks proven in the *approved* environment | **OPEN** |
| G5 Independent recovery | Full archive/schema/database integrity, restore to distinct non-live target and application-level recovery checks with writers stopped; evidence of actual functionality, not just file counts | **OPEN** |
| G6 Writer controls | All 7 writer-control admission items independently approved before any live activation | **OPEN (0/7)** |
| G7 Safety blockers | Six outstanding P0 controls reviewed and closed by appropriate authority; explicit separate operational authorisation | **OPEN (6 P0)** |

**NO-GO dominates.** Success in one gate cannot auto-promote the other gates,
and GitHub Actions cannot substitute for evidence from the real OS and live
restore environment. Even completed G0–G5 would not automatically authorise
production operations without G6/G7 and explicit permission.

## Evidence rules (for a later separately authorised assessment)

Record: date/time, actual environment identifier, exact source-code revision,
account/process identity, independent examiner, tested scope, explicit
pass/fail per gate, evidence artefact(s), and known blind spots. Public CI
must receive **no private paths, protected names, secrets, personal data or
identifying host snapshots**. An absence of log messages is not proof of no
I/O; a real no-contact claim needs independent process/OS confinement evidence
established without forbidden reads.

### Stop immediately and retain NO-GO when

- an already-approved OS sandbox/entitlement model fails to initialise;
- any required check depends on accessing a forbidden source or ancestor;
- a path, mount, alias, plugin or config dependency has unknown origin;
- any child process has broader filesystem rights than the admitted worker;
- a source needed for functional recovery must be excluded without an
  approved omission and restore plan;
- backups fail closed on unreadable data, or user data must be exposed to
  public CI for testing.

Do **not** run exploratory `ls`, `stat`, `find`, `realpath`, ACL changes,
`chmod`, `chown`, mounted-volume probes, OpenClaw backup commands, or
production updates to resolve those conditions.

## One bounded next action

Choose and document the **host-independent access architecture** first:
which authorised actor could produce a source-origin certificate and stage a
strict subset without access to forbidden history, and how the eventual
processing environment is physically/logically disconnected from every
protected volume. Assess the design against G0–G2 **without using live-host
commands**. If no credible source-provenance mechanism exists, return
**BLOCKED** and pursue a separately authorised clean rebuild on a new
installation rather than falsely declaring a full recovery.

**Not done:** no production host isolation acceptance, source certificate,
real backup, real restore, official OpenClaw code merge, or permission to
proceed with live operations.
