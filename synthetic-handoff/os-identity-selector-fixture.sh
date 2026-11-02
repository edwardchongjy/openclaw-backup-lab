#!/usr/bin/env bash
# Only Linux GitHub runner, wholly fictional test bytes, and /tmp scratch data.
set -euo pipefail
test "${RUNNER_OS}" = "Linux"
test "$(id -u)" -ne 0
command -v sudo >/dev/null
sudo -n true
id nobody >/dev/null
test -x /usr/bin/python3

work="$(mktemp -d /tmp/oc-selector-uid-fixture-XXXXXXXX)"
case "$work" in /tmp/oc-selector-uid-fixture-*) ;; *) exit 4 ;; esac
trap 'sudo -n rm -rf -- "$work"' EXIT
chmod 0711 "$work"
cp synthetic-handoff/selector.py synthetic-handoff/producer.py "$work/"
chmod 0644 "$work/selector.py" "$work/producer.py"

mkdir -m 0700 "$work/approved-source" "$work/staging-parent" "$work/root-protected"
sudo -n chown nobody:nogroup "$work/approved-source" "$work/staging-parent"
sudo -n chown root:root "$work/root-protected"
sudo -n chmod 0700 "$work/root-protected"

sudo -n /usr/bin/python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_bytes(b"ROOT_OWNED_FICTIONAL_UNSELECTED_BYTES"); p.chmod(0o600)' "$work/root-protected/fixture.txt"
sudo -n -u nobody /usr/bin/python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_bytes(b"{\"fictional\":true}"); p.chmod(0o600)' "$work/approved-source/settings.json"

# Root can place both forbidden aliases in the synthetic allowlist before
# the unprivileged selector starts. The selector must publish no staged tree.
sudo -n ln -s "$work/root-protected/fixture.txt" "$work/approved-source/notes.txt"
sudo -n ln "$work/root-protected/fixture.txt" "$work/approved-source/agent-inventory.json"

if sudo -n -u nobody /bin/cat "$work/root-protected/fixture.txt" >/dev/null 2>&1; then
  echo "DIRECT_PROTECTED_READ=WRONGLY_ALLOWED"; exit 1
fi
if sudo -n -u nobody /bin/cat "$work/approved-source/notes.txt" >/dev/null 2>&1; then
  echo "SYMLINK_PROTECTED_READ=WRONGLY_ALLOWED"; exit 1
fi
if sudo -n -u nobody /bin/cat "$work/approved-source/agent-inventory.json" >/dev/null 2>&1; then
  echo "HARDLINK_PROTECTED_READ=WRONGLY_ALLOWED"; exit 1
fi
echo "FAKE_PROTECTED_UID_ACCESS_DENIED=PASS"

if sudo -n -u nobody /usr/bin/python3 -B "$work/selector.py" "$work/approved-source" "$work/staging-parent" > "$work/rejected.out" 2> "$work/rejected.err"; then
  echo "MALICIOUS_ALIAS_STAGE=WRONGLY_PUBLISHED"; exit 1
fi
test ! -s "$work/rejected.out"
sudo -n -u nobody /usr/bin/python3 -c 'import pathlib,sys; assert list(pathlib.Path(sys.argv[1]).iterdir()) == []' "$work/staging-parent"
echo "BAD_STAGED_ALIASES_NO_OUTPUT=PASS"

# Remove only the two synthetic attacks; now select and reconstruct authorised
# bytes. No real project data is read or passed to this fixture.
sudo -n rm -f -- "$work/approved-source/notes.txt" "$work/approved-source/agent-inventory.json"
staged_name="$(sudo -n -u nobody /usr/bin/python3 -B "$work/selector.py" "$work/approved-source" "$work/staging-parent")"
case "$staged_name" in staged-*) ;; *) echo "BAD_STAGED_NAME"; exit 1 ;; esac
sudo -n -u nobody /usr/bin/python3 -B "$work/producer.py" "$work/staging-parent/$staged_name" > "$work/fictional-envelope.json"
python3 -B synthetic-handoff/receiver.py "$work/receiver-output" < "$work/fictional-envelope.json"
python3 -c 'import pathlib,sys; assert pathlib.Path(sys.argv[1]).read_bytes()==b"{\"fictional\":true}"' "$work/receiver-output/settings.json"
test "$(find "$work/receiver-output" -type f | wc -l)" -eq 1
echo "UNPRIVILEGED_SELECTOR_PRODUCER_RECEIVER_CHAIN=PASS"
echo "LIMITS: synthetic Linux UID test only; no source provenance or real Mac isolation established"
