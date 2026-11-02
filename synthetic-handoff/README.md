# Synthetic data-only handoff experiment

This directory is a **separate, public GitHub-runner experiment**. It is not
the official OpenClaw backup utility, a production backup/exporter or a
real-data restore procedure.

## Question being tested

Can an independently running receiver accept **only authorised bytes already
selected by a separate trusted producer**, with no filesystem source-path
inputs, symlink or hardlink references? The receiver takes a small JSON
envelope from standard input, checks an exact schema, named-file allowlist,
byte-size limits and SHA-256 hashes, then creates a fresh destination
directory containing only those declared bytes.

`receiver.py` has **no path-based source discovery**. Its only path argument
is an **output destination** supplied by the test. The tests deliberately
create independent fake protected bytes and alias names, and confirm that
source-path fields, traversal, corrupt digests and existing linked output
destinations are refused.

## Security and scope limits

- GitHub-hosted macOS ARM64 and **fictional test bytes only**.
- A process accepting supplied bytes **cannot establish where those bytes came
  from**. If an untrusted producer reads a forbidden file and passes those
  bytes, the receiver cannot detect the source. This experiment does **not**
  solve safe extraction/export from a live OpenClaw installation.
- This is a strict **application input contract**, **not OS-enforced filesystem
  isolation**, not a proof that the runtime cannot access another path, and
  not a real S10 zero-contact result.
- The output parent must be **trusted and controlled**. This is not a
  concurrency-safe general-purpose filesystem installer. In particular, a
  later failure during writing is not currently an atomic rollback.
- Tests are **not** a production backup, official OpenClaw verify, full
  OpenClaw restore, upgrade, writer-gate validation or secret-handling audit.
- No real OpenClaw data, S10 archive, Mac mini files, Hermes data, credentials
  or private system locations are ever inputs to this experiment.

## Local command (on a disposable environment only)

```sh
python3 -B -m unittest discover -s synthetic-handoff -p 'test_*.py' -v
```

The actual recorded validation runs on a GitHub-hosted macOS ARM64 Actions
runner. **Do not run this experiment against personal files or a live
OpenClaw profile.**

Production backup/restore/upgrade remains **NO-GO** pending independently
proven isolation, approved source acquisition, real restore verification,
writer control gates and outstanding P0 safety checks.
