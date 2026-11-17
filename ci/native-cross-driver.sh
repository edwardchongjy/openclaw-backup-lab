#!/usr/bin/env bash
set -euo pipefail
umask 077
mode="$1"
case "$mode" in produce|restore) ;; *) exit 2;; esac
test "$RUNNER_ENVIRONMENT" = github-hosted
test "$RUNNER_OS" = Linux
test "$GITHUB_REPOSITORY" = edwardchongjy/openclaw-backup-lab
test "$GITHUB_REF" = refs/heads/lab/native-encrypted-crossrunner-20261117
test "$(id -u)" -ne 0
test "$(git -C lab rev-parse HEAD)" = "$GITHUB_SHA"
test "$(git -C upstream rev-parse HEAD)" = 1b58cb9a1b4f4353e1add63c8506db4d890962e8
node --version | grep -Fx v24.16.0
node -e 'if(require("./upstream/package.json").version!=="2026.10.5")process.exit(1)'
test "$CI_FICTIONAL_PASSPHRASE" = PUBLIC_LAB_KEY_NOT_SECRET_DO_NOT_USE_FOR_REAL_OPENCLAW
npm install --global pnpm@12.9.0
pnpm -C upstream install --frozen-lockfile
env -i PATH="$PATH" HOME=/tmp CI=true pnpm -C upstream openclaw --version
test -f upstream/dist/entry.js -o -f upstream/dist/entry.mjs
cp lab/ci/clean-v1-crossrunner-fake-provider.mjs upstream/ci-fake-provider.mjs
cp lab/ci/clean-v1-crossrunner-pilot.mjs upstream/ci-container-pilot.mjs
cp lab/ci/clean-v1-offsite-config.mjs upstream/ci-offsite-config.mjs
cp lab/ci/native-cross-helper.mjs upstream/native-cross-helper.mjs
cp lab/ci/clean-v1-offsite.Dockerfile upstream/Dockerfile.ci-offsite
cat > upstream/.dockerignore <<'IGNORE'
.git
.github
**/.git
**/.cache
*.log
IGNORE
docker pull node:24.16.0-bookworm-slim@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203 >/dev/null
tag="clean-v1-native-cross:$GITHUB_RUN_ID-$mode"
docker build --network none --pull=false -f upstream/Dockerfile.ci-offsite -t "$tag" upstream
test -n "$(docker image inspect --format '{{.Id}}' "$tag")"
echo "PUBLIC_PINNED_OPENCLAW_WITH_NATIVE_STORAGE_ENCRYPTION_BUILT=PASS"
vol_state="native-cross-state-$GITHUB_RUN_ID-$mode"
vol_offsite="native-cross-store-$GITHUB_RUN_ID-$mode"
name="native-cross-$GITHUB_RUN_ID-$mode"
cleanup(){
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker volume rm "$vol_state" "$vol_offsite" >/dev/null 2>&1 || true
  docker image rm "$tag" >/dev/null 2>&1 || true
}
trap cleanup EXIT
for vol in "$vol_state" "$vol_offsite"; do
  if docker volume inspect "$vol" >/dev/null 2>&1; then exit 1; fi
  docker volume create --driver local --label ci.project=native-cross-fiction "$vol" >/dev/null
done
common=(--network none --read-only --user 10001:10001
  --cap-drop ALL --security-opt no-new-privileges
  --pids-limit 256 --memory 3g --cpus 2 --ipc private
  --mount "type=volume,source=$vol_state,target=/home/ci"
  --mount "type=volume,source=$vol_offsite,target=/home/offsite"
  --tmpfs /tmp:rw,nosuid,nodev,uid=10001,gid=10001,mode=1777,size=768m
  --env HOME=/home/ci --env TMPDIR=/tmp
  --env XDG_CONFIG_HOME=/home/ci/.config --env XDG_CACHE_HOME=/home/ci/cache
  --env OPENCLAW_HOME=/home/ci --env OPENCLAW_STATE_DIR=/home/ci/state
  --env OPENCLAW_CONFIG_PATH=/home/ci/state/openclaw.json
  --env OPENCLAW_DISABLE_BUNDLED_PLUGINS=1 --env NODE_DISABLE_COMPILE_CACHE=1
  --env "OPENCLAW_STORAGE_PASSPHRASE=$CI_FICTIONAL_PASSPHRASE"
  --env HOST_ONLY_FICTION_PATH=/never-mounted-fictional-marker
  --env CI_PILOT_MODE=first --env CI=true)
inspect_boundary(){
  docker inspect "$name" | python3 -c '
import json,sys
x=json.load(sys.stdin)[0]; h=x["HostConfig"]
assert h["NetworkMode"]=="none" and h["ReadonlyRootfs"] and not h["Privileged"]
assert x["Config"]["User"]=="10001:10001"
assert "ALL" in h["CapDrop"] and "no-new-privileges" in h["SecurityOpt"]
assert not h["Binds"] and not h["Devices"] and not h.get("PortBindings")
assert h["IpcMode"]=="private" and h["PidsLimit"]==256 and h["Memory"]==3221225472
assert {m["Destination"]:m["Name"] for m in x["Mounts"]}=={"/home/ci":sys.argv[1],"/home/offsite":sys.argv[2]}
assert all(m["Type"]=="volume" for m in x["Mounts"])
print("ACTUAL_CONTAINER_NO_NETWORK_NO_HOST_BIND_NONROOT_READONLY=PASS")
' "$vol_state" "$vol_offsite"
}
run_node(){
  docker create --name "$name" "${common[@]}" --entrypoint node "$tag" "$@" >/dev/null
  inspect_boundary
  docker start -a "$name"
  local code
  code=$(docker inspect --format '{{.State.ExitCode}}' "$name")
  docker rm "$name" >/dev/null
  return "$code"
}
cli(){ run_node /app/upstream/openclaw.mjs "$@"; }
helper(){ run_node /app/upstream/native-cross-helper.mjs "$@"; }
config(){ run_node /app/upstream/ci-offsite-config.mjs "$@"; }
transfer="$RUNNER_TEMP/native-transfer.tar"
if test "$mode" = produce; then
  run_node /app/upstream/ci-container-pilot.mjs
  echo "PRODUCER_FICTIONAL_GATEWAY_STOPPED=PASS"
  config configure
  cli storage init ciarchive
  cli storage test ciarchive
  helper seed
  cli backup create --to ciarchive --namespace ci-fresh-fiction
  cli backup verify --from ciarchive --namespace ci-fresh-fiction latest
  config assert-encrypted
  helper audit-export
  docker run --rm "${common[@]}" --entrypoint tar "$tag" -C /home/offsite -cf - . > "$transfer"
  test "$(stat -c %s "$transfer")" -lt 16777216
  sha=$(sha256sum "$transfer" | cut -d' ' -f1)
  printf 'sha256=%s\n' "$sha" >> "$GITHUB_OUTPUT"
  echo "ENCRYPTED_TRANSFER_SHA256=$sha"
  echo "NATIVE_ENCRYPTED_TRANSFER_CREATED=PASS"
else
  transfer="$RUNNER_TEMP/recovery-input/native-transfer.tar"
  python3 - "$transfer" <<'PY'
import hashlib,os,pathlib,sys,tarfile
p=pathlib.Path(sys.argv[1]); data=p.read_bytes()
assert 0<len(data)<16777216
assert hashlib.sha256(data).hexdigest()==os.environ['CI_EXPECTED_ARCHIVE_SHA']
with tarfile.open(p,'r:') as t:
  rows=t.getmembers(); assert 0<len(rows)<100
  names=set()
  for r in rows:
    n=r.name.removeprefix('./'); parts=pathlib.PurePosixPath(n).parts
    assert not n.startswith('/') and '..' not in parts and '\\' not in n
    assert r.isfile() or r.isdir()
    assert n not in names; names.add(n)
    assert r.size<8388608
print('SECOND_INDEPENDENT_RUNNER_TRANSFER_SHA256_MATCH=PASS')
print('TRANSFER_BOUNDED_REGULAR_FILES_ONLY_BEFORE_IMPORT=PASS')
PY
  docker run --rm -i "${common[@]}" --entrypoint tar "$tag" -C /home/offsite --no-same-owner --no-same-permissions -xf - < "$transfer"
  helper recovery-config
  cli config validate
  cli backup verify --from ciarchive --namespace ci-fresh-fiction latest
  echo "INDEPENDENT_RUNNER_OFFICIAL_VERIFY=PASS"
  # Wrong key test is an actual RESTORE, with rejection reason checked and empty target asserted.
  common+=(--env OPENCLAW_STORAGE_PASSPHRASE=WRONG_PUBLIC_FAKE_TEST_KEY)
  if cli backup restore --from ciarchive --namespace ci-fresh-fiction latest --target /home/ci/wrong-target > "$RUNNER_TEMP/wrong.log" 2>&1; then
    echo WRONG_KEY_ACCEPTED=FAIL; exit 1
  fi
  common+=(--env "OPENCLAW_STORAGE_PASSPHRASE=$CI_FICTIONAL_PASSPHRASE")
  python3 - "$RUNNER_TEMP/wrong.log" <<'PY'
import pathlib,re,sys
s=pathlib.Path(sys.argv[1]).read_text(); assert re.search(r'authenticat|decrypt|passphrase|password|key',s,re.I),s[-1000:]
print('WRONG_PASSPHRASE_NATIVE_RESTORE_REFUSED=PASS')
PY
  helper check-wrong-empty
  cli backup restore --from ciarchive --namespace ci-fresh-fiction latest --target /home/ci/restored
  helper compare
  echo "SECOND_INDEPENDENT_RUNNER_NATIVE_ENCRYPTED_RESTORE=PASS"
  config tamper
  if cli backup restore --from ciarchive --namespace ci-fresh-fiction latest --target /home/ci/tamper-target > "$RUNNER_TEMP/tamper.log" 2>&1; then
    echo TAMPER_ACCEPTED=FAIL; exit 1
  fi
  python3 - "$RUNNER_TEMP/tamper.log" <<'PY'
import pathlib,re,sys
s=pathlib.Path(sys.argv[1]).read_text(); assert re.search(r'authenticat|decrypt|integrity|corrupt',s,re.I),s[-1000:]
print('TAMPERED_CIPHERTEXT_NATIVE_RESTORE_REFUSED=PASS')
PY
  helper check-tamper-empty
  echo "NATIVE_ENCRYPTED_CROSS_RUNNER_TEST=PASS"
fi
echo "SYNTHETIC_ONLY_NO_REAL_KEYS_NO_MAC_NO_HERMES_NO_OLD_OPENCLAW_NO_MERGE_NO_DEPLOY_PRODUCTION_NO_GO"
