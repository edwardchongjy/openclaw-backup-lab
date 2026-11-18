# Synthetic cross-date native OpenClaw retention — evidence

**Result:** PASS for the exact synthetic test scope; **production remains NO-GO**.

- Date: 2026-11-18 UTC
- Pinned upstream: OpenClaw 2026.10.5 @ `1b58cb9a1b4f4353e1add63c8506db4d890962e8`
- Test commit (actual checked-out source): `ce96aa905a078f3f1fc0d85b8d8c0f7549a1f4ab`
- [GitHub Actions run #44377563926](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44377563926) — completed success
- Job `135060692482` — completed success
- Scope: disposable GitHub-hosted Linux runner, Docker named volumes, mock fictional OpenClaw state, publicly known dummy key and local filesystem storage (not Cloudflare R2). Test branch PR #2 remains draft and unmerged.

## Direct log markers

```text
FICTION_CROSSDATE_CIPHERTEXT_SEEDED=PASS total=39 kept=19 deleted=20
Retention: 19 kept, 21 deleted.
NATIVE_CROSSDATE_EXACT_7D_4W_12M_AND_FOREIGN_PRESERVATION=PASS kept=19 deleted=20
NATIVE_CROSSDATE_HISTORICAL_CIPHERTEXT_RESTORE=PASS
NATIVE_CROSSDATE_RETENTION_AND_RESTORE=PASS
NATIVE_OFFSITE_WRONG_PASSPHRASE_REFUSED=PASS
NATIVE_ENCRYPTED_OFFSITE_RESTORED_TO_NEW_SCRATCH=PASS
NATIVE_AUTHENTICATED_OFFSITE_TAMPER_REJECTED=PASS
ENCRYPTED_PUBLIC_FICTIONAL_BACKUP_PILOT=PASS
```

39 timestamp-named encrypted test objects were staged (a genuine fresh encrypted backup plus copies of the *same* authenticated ciphertext under fabricated historic UTC dates). A subsequent new real OpenClaw backup with `--keep-daily 7 --keep-weekly 4 --keep-monthly 12` brought the total to 40. The native retention engine kept the exact 19 expected objects and removed 21. It preserved namespace ownership data, an unrelated namespace and a non-backup marker. The latest and a retained historically named ciphertext object passed verification; the historically named object could be restored to disposable scratch. Wrong-password and tampering refusal checks also passed. Generated dates span UTC days, Monday-start weeks, calendar months and a year boundary.

## What this does not prove

- Historical filenames are artificial: this is **not** evidence of 12 months of independently created, evolving backups.
- The historically named objects are copies of one ciphertext, not distinct period-specific content.
- No live Cloudflare R2 API, bucket, authentication, write/read, locking or price verification took place.
- No production Mac mini, old OpenClaw, Hermes, real credentials or external messaging was accessed.
- No complete second-host Agent activation was added in this run. Existing separate synthetic cross-runner evidence has its own scope.
- Long-term scheduled execution, real secrets custody, actual disk failure recovery and production admission gates remain unverified.

**Decision:** Leave PR #1 / PR #2 unmerged; keep old OpenClaw and Hermes at **NO-GO**. The smallest next independent gate is a fake-only live R2 storage test after separate authorization, without installing or changing the production host.
