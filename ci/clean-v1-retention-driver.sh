#!/usr/bin/env bash
set -euo pipefail
umask 077
test "$RUNNER_ENVIRONMENT" = github-hosted
test "$RUNNER_OS" = Linux
test "$GITHUB_REPOSITORY" = edwardchongjy/openclaw-backup-lab
test "$GITHUB_REF" = refs/heads/lab/retention-synthetic-20261118
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
cp lab/ci/clean-v1-retention-config.mjs upstream/ci-offsite-config.mjs
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
docker run --name "$first" ${common[@]} "$tag"
python3 - "$first" "$vol_state" "$vol_offsite" <<'PY'
import json,subprocess,sys
d=json.loads(subprocess.check_output(["docker","inspect",sys.argv[1]],text=True))[0]
h=d["HostConfig"];mnt=d["Mounts"]
assert d["State"]["ExitCode"]==0
assert h["NetworkMode"]=="none" and h["ReadonlyRootfs"] is True
assert h["Privileged"] is False and "ALL" in h["CapDrop"]
assert "no-new-privileges" in h["SecurityOpt"]
assert h["Binds"] in (None,[]) and h["Devices"] in (None,[])
assert h.get("PortBindings") in (None,{})
assert d["Config"]["User"]=="10001:10001"
assert len(mnt)==2 and all(x["Type"]=="volume" and x["RW"] for x in mnt)
assert {x["Destination"]:x["Name"] for x in mnt}=={"/home/ci":sys.argv[2],"/home/offsite":sys.argv[3]}
print("REAL_GATEWAY_NO_EGRESS_TWO_NEW_SEPARATE_VOLUMES=PASS")
PY
docker rm "$first" >/dev/null
echo "GATEWAY_STOPPED_BEFORE_ENCRYPTED_BACKUP=PASS"
config configure
cli config validate
cli storage init ciarchive
cli storage test ciarchive
echo "NATIVE_OFFSITE_STORAGE_INIT_AND_WRITE_READ_DELETE=PASS"
cli backup create --to ciarchive --namespace ci-fresh-fiction
cli backup verify --from ciarchive --namespace ci-fresh-fiction latest
echo "NATIVE_OPENCLAW_ENCRYPTED_BACKUP_CREATE_AND_VERIFY=PASS"
config assert-encrypted
config seed-retention
sleep 2
cli backup create --to ciarchive --namespace ci-fresh-fiction --keep-daily 7 --keep-weekly 4 --keep-monthly 12
cli backup verify --from ciarchive --namespace ci-fresh-fiction latest
config assert-retention
cli storage test ciarchive
echo "NATIVE_OFFSITE_RETENTION_SAME_DAY=PASS"
wrong_log="$RUNNER_TEMP/clean-v1-wrong-key-$GITHUB_RUN_ID.log"
if wrong_key_cli storage test ciarchive >"$wrong_log" 2>&1; then
  echo "WRONG_PASSPHRASE_WAS_ACCEPTED=FAIL"
  exit 1
fi
echo "NATIVE_OFFSITE_WRONG_PASSPHRASE_REFUSED=PASS"
docker run --rm ${common[@]} --entrypoint sh "$tag" -ec '
  node /app/upstream/openclaw.mjs backup restore --from ciarchive \
    --namespace ci-fresh-fiction latest --target /tmp/fictional-restored
  test -d /tmp/fictional-restored
  test -n "$(find /tmp/fictional-restored -type f -print -quit)"
  echo NATIVE_ENCRYPTED_OFFSITE_RESTORED_TO_NEW_SCRATCH=PASS
'
config tamper
bad_log="$RUNNER_TEMP/clean-v1-tamper-$GITHUB_RUN_ID.log"
if cli backup verify --from ciarchive --namespace ci-fresh-fiction latest >"$bad_log" 2>&1; then
  echo "TAMPERED_ENCRYPTED_BACKUP_WAS_ACCEPTED=FAIL"
  exit 1
fi
echo "NATIVE_AUTHENTICATED_OFFSITE_TAMPER_REJECTED=PASS"
echo "ENCRYPTED_PUBLIC_FICTIONAL_BACKUP_PILOT=PASS"
echo "NO_REAL_PASSWORD; NO_MAC; NO_HERMES; NO_OLD_OPENCLAW; NO_DEPLOY; G0_G7_NO_GO"
