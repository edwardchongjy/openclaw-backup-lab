# Synthetic data-only handoff experiment

This directory is a **separate, public GitHub-runner experiment**. It is not
the official OpenClaw backup utility, a production backup/exporter or a
real-data restore procedure.

## Question being tested

Can an independently running receiver accept **only authorised bytes already
selected by a separately authorised provider**, with no filesystem source-path
inputs, symlink or hardlink references? The receiver takes a small JSON
envelope from standard input, checks an exact schema, named-file allowlist,
byte-size limits and SHA-256 hashes, then creates a fresh destination
directory containing only those declared bytes.

`receiver.py` has **no path-based source discovery**. Its only path argument
is an **output destination** supplied by the test. The tests deliberately
create independent fake protected bytes and alias names, and confirm that
source-path fields, traversal, corrupt digests and existing linked output
destinations are refused.

## Experimental staged-data provider

`producer.py` is a **synthetic staged-data provider**, not an approved live
OpenClaw source selector. It opens only three fixed, optional filenames in an
already prepared directory. It requires a directory owned by its process with
mode `0700`, and only regular files owned by that same process with mode
`0600` and exactly one hard-link name. It does not enumerate source entries.
All accepted bytes are packaged with checksums and passed to `receiver.py`.
A faulty entry causes the entire envelope to be rejected.

Two GitHub-hosted systems run 24 fictional tests each: macOS ARM64 and Ubuntu.
A separate Ubuntu test creates a **root-owned, 0600, completely fictional**
protected inode and a **`nobody`**-owned staged source. It verifies that the
unprivileged provider identity cannot read those protected bytes directly,
through a symlink, or through a hardlink made ahead of time by root. It also
checks that permitted staged bytes can reach the receiver without change.
This is a **specific Linux POSIX user-permission proof on synthetic fixtures**,
not the sandbox, account or permissions on the actual Mac mini.

## Security and scope limits

- GitHub-hosted macOS ARM64 and Ubuntu runners with **fictional test bytes only**.
- A process accepting supplied bytes **cannot establish where those bytes came
  from**. If an untrusted producer reads a forbidden file and passes those
  bytes, the receiver cannot detect the source. This experiment does **not**
  solve safe extraction/export from a live OpenClaw installation.
- The receiver protocol is an **application input contract**. The Ubuntu
  separate-user check adds one OS-enforced example, but neither proves that a
  Mac mini process cannot read another path or that any real protected path
  was never contacted. The staged root and its ancestors must be trusted;
  separately authorised provenance and production isolation are absent.
- The output parent must be **trusted and controlled**. This is not a
  concurrency-safe general-purpose filesystem installer. In particular, a
  later failure during writing is not currently an atomic rollback.
- Tests are **not** a production backup, official OpenClaw verify, full
  OpenClaw restore, upgrade, writer-gate validation or secret-handling audit.
- No real OpenClaw data, S10 archive, Mac mini files, Hermes data, credentials
  or private system locations are ever inputs to this experiment.

## Still missing for real recovery

1. An independently audited, least-privilege **staging selector** that cannot
   see any protected source or alias (and cannot promote such a source).
2. Evidence that the real host can enforce that constraint, including
   hard-link identity, symlink and mount/ancestor boundaries.
3. Reliable source provenance and atomic staging/rollback; this receiver's
   checksum detects corruption but cannot certify that bytes are permitted.
4. Complete backup coverage and real restoration checks, followed by approved
   writer gates and P0 controls. None is proven by these synthetic tests.

## Local command (on a disposable environment only)

```sh
python3 -B -m unittest discover -s synthetic-handoff -p 'test_*.py' -v
```

The recorded validation includes GitHub-hosted macOS ARM64 and Ubuntu
Actions runners. **Do not run this experiment against personal files or a live
OpenClaw profile.**

Production backup/restore/upgrade remains **NO-GO** pending independently
proven isolation, approved source acquisition, real restore verification,
writer control gates and outstanding P0 safety checks.
