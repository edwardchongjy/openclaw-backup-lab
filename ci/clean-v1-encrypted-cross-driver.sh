#!/usr/bin/env bash
set -euo pipefail
umask 077
mode=${1:?produce or restore}
[[ "$mode" = produce || "$mode" = restore ]]
test "$RUNNER_ENVIRONMENT" = github-hosted
test "$RUNNER_OS" = Linux
test "$GITHUB_REPOSITORY" = edwardchongjy/openclaw-backup-lab
test "$GITHUB_REF" = refs/heads/lab/clean-rebuild-v1-gateway-backup-ci
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
cp lab/ci/clean-v1-encrypted-cross-check.mjs upstream/ci-encrypted-cross-check.mjs
cp lab/ci/clean-v1-offsite.Dockerfile upstream/Dockerfile.ci-offsite
cat > upstream/.dockerignore <<'IGNORE'
.git
.github
**/.git
**/.cache
*.log
IGNORE
docker pull node:24.16.0-bookworm-slim@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203 >/dev/null
tag="clean-v1-native-crypto:$GITHUB_RUN_ID"
docker build --network none --pull=false -f upstream/Dockerfile.ci-offsite -t "$tag" upstream
test -n "$(docker image inspect --format '{{.Id}}' "$tag")"
echo "PUBLIC_PINNED_OPENCLAW_WITH_NATIVE_STORAGE_ENCRYPTION_BUILT=PASS"
vol_state="clean-v1-crypto-state-$GITHUB_RUN_ID"
vol_offsite="clean-v1-crypto-offsite-$GITHUB_RUN_ID"
first="clean-v1-crypto-first-$GITHUB_RUN_ID"
cleanup(){
  docker rm -f "$first" >/dev/null 2>&1 || true
  docker volume rm -f "$vol_state" "$vol_offsite" >/dev/null 2>&1 || true
  docker image rm "$tag" >/dev/null 2>&1 || true
}
trap cleanup EXIT
for vol in "$vol_state" "$vol_offsite"; do
  if docker volume inspect "$vol" >/dev/null 2>&1; then exit 1; fi
  docker volume create --driver local --label "ci.project=clean-v1-only" --label "ci.run=$GITHUB_RUN_ID" "$vol" >/dev/null
done
echo "TWO_NEW_DOCKER_OWNED_VOLUMES_FOR_STATE_AND_ENCRYPTED_BACKUP=PASS"
fake_host="$RUNNER_TEMP/ci-fake-unmounted-$GITHUB_RUN_ID.txt"
printf 'PUBLIC_FAKE_UNMOUNTED_HOST_MARKER\n' > "$fake_host"
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
  --env OPENCLAW_GATEWAY_TOKEN=PUBLIC-CI-NOT-SECRET
  --env OPENCLAW_DISABLE_BUNDLED_PLUGINS=1
  --env NODE_DISABLE_COMPILE_CACHE=1
  --env "OPENCLAW_STORAGE_PASSPHRASE=$CI_FICTIONAL_PASSPHRASE"
  --env "HOST_ONLY_FICTION_PATH=$fake_host"
  --env CI_PILOT_MODE=first --env CI=true
)
cli(){ docker run --rm ${common[@]} --entrypoint node "$tag" /app/upstream/openclaw.mjs "$@"; }
config(){ docker run --rm ${common[@]} --entrypoint node "$tag" /app/upstream/ci-offsite-config.mjs "$@"; }
wrong_key_cli(){
  docker run --rm ${common[@]} --env OPENCLAW_STORAGE_PASSPHRASE=WRONG_PUBLIC_FAKE_TEST_KEY \
    --entrypoint node "$tag" /app/upstream/openclaw.mjs "$@"
}
check(){ docker run --rm ${common[@]} --entrypoint node "$tag" /app/upstream/ci-encrypted-cross-check.mjs "$@"; }
docker create --name "$first" ${common[@]} --entrypoint node "$tag" -e 'const f=require("fs");if(process.getuid()!==10001||f.existsSync("/var/run/docker.sock")||f.existsSync(process.env.HOST_ONLY_FICTION_PATH))process.exit(1);try{f.writeFileSync("/app/upstream/forbidden","x");process.exit(2)}catch{}' >/dev/null
docker start -a "$first"
python3 - "$first" "$vol_state" "$vol_offsite" <<'BOUNDARY'
import json,subprocess,sys
d=json.loads(subprocess.check_output(['docker','inspect',sys.argv[1]],text=True))[0]
h=d['HostConfig'];m=d['Mounts']
assert d['State']['ExitCode']==0 and d['Config']['User']=='10001:10001'
assert h['NetworkMode']=='none' and h['ReadonlyRootfs'] and not h['Privileged']
assert 'ALL' in h['CapDrop'] and 'no-new-privileges' in h['SecurityOpt']
assert not h.get('Binds') and not h.get('Devices') and not h.get('PortBindings')
assert len(m)==2 and all(x['Type']=='volume' for x in m)
assert {x['Destination']:x['Name'] for x in m}=={'/home/ci':sys.argv[2],'/home/offsite':sys.argv[3]}
print('THIS_RUNNER_NONROOT_NO_NETWORK_NO_BINDS_READ_ONLY_ROOT=PASS')
BOUNDARY
docker rm "$first" >/dev/null
if [[ "$mode" = produce ]]; then
  docker run --name "$first" ${common[@]} "$tag"
  test "$(docker inspect --format '{{.State.ExitCode}}' "$first")" = 0
  docker rm "$first" >/dev/null
  config configure
  cli config validate
  cli storage init ciarchive
  cli storage test ciarchive
  check manifest > "$RUNNER_TEMP/expected-files.json"
  cli backup create --to ciarchive --namespace ci-fresh-fiction
  cli backup verify --from ciarchive --namespace ci-fresh-fiction latest
  config assert-encrypted
  check no-plaintext
  docker run --rm ${common[@]} --entrypoint tar "$tag" -C /home/offsite -cf - . > "$RUNNER_TEMP/encrypted-store.tar"
  test "$(stat -c %s "$RUNNER_TEMP/encrypted-store.tar")" -lt 33554432
  echo "sha256=$(sha256sum "$RUNNER_TEMP/encrypted-store.tar" | cut -d ' ' -f1)" >> "$GITHUB_OUTPUT"
  echo "manifest_sha256=$(sha256sum "$RUNNER_TEMP/expected-files.json" | cut -d ' ' -f1)" >> "$GITHUB_OUTPUT"
  echo SECOND_HOST_ENCRYPTED_EXPORT_READY=PASS
else
  archive="$RUNNER_TEMP/recovery-input/encrypted-store.tar"
  expected="$RUNNER_TEMP/recovery-input/expected-files.json"
  python3 - "$archive" "$CI_EXPECTED_ARCHIVE_SHA" "$expected" "$CI_EXPECTED_MANIFEST_SHA" <<'VERIFY'
import hashlib,sys,tarfile,pathlib
for f,want in [(sys.argv[1],sys.argv[2]),(sys.argv[3],sys.argv[4])]:
 assert len(want)==64 and hashlib.sha256(open(f,'rb').read()).hexdigest()==want
with tarfile.open(sys.argv[1]) as t:
 members=t.getmembers(); assert 0<len(members)<1000
 assert sum(m.size for m in members)<33554432
 for m in members:
  p=pathlib.PurePosixPath(m.name)
  assert not p.is_absolute() and '..' not in p.parts and (m.isfile() or m.isdir())
print('SECOND_HOST_INDEPENDENT_TRANSFER_DIGEST_AND_LAYOUT=PASS')
VERIFY
  docker run --rm -i ${common[@]} --entrypoint tar "$tag" -C /home/offsite -xf - < "$archive"
  docker run --rm ${common[@]} --entrypoint sh "$tag" -ec 'mkdir -p /home/ci/state; printf "{}\n" > /home/ci/state/openclaw.json'
  config configure
  config assert-encrypted
  check no-plaintext
  cli backup verify --from ciarchive --namespace ci-fresh-fiction latest
  docker run --rm -i ${common[@]} --entrypoint sh "$tag" -ec '
    cat > /tmp/expected-files.json
    node /app/upstream/openclaw.mjs backup restore --from ciarchive --namespace ci-fresh-fiction latest --target /tmp/restored
    node /app/upstream/ci-encrypted-cross-check.mjs compare /tmp/restored /tmp/expected-files.json
  ' < "$expected"
  docker run --rm ${common[@]} --env OPENCLAW_STORAGE_PASSPHRASE=WRONG_PUBLIC_FAKE_TEST_KEY --entrypoint node "$tag" /app/upstream/ci-encrypted-cross-check.mjs reject wrong
  config tamper
  check reject tamper
  echo SECOND_HOST_NATIVE_ENCRYPTED_RESTORE=PASS
fi
echo NO_REAL_CREDENTIALS_NO_MAC_NO_HERMES_NO_OLD_OPENCLAW_NO_DEPLOY
