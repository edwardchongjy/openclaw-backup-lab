#!/usr/bin/env bash
set -euo pipefail
umask 077
mode="$1"
case "$mode" in produce|restore) ;; *) echo "Unknown synthetic runner mode"; exit 2;; esac
test "$RUNNER_ENVIRONMENT" = github-hosted
test "$RUNNER_OS" = Linux
test "$GITHUB_REPOSITORY" = edwardchongjy/openclaw-backup-lab
test "$GITHUB_REF" = refs/heads/lab/clean-rebuild-v1-gateway-backup-ci
test "$(id -u)" -ne 0
test "$(git -C lab rev-parse HEAD)" = "$GITHUB_SHA"
test "$(git -C upstream rev-parse HEAD)" = 1b58cb9a1b4f4353e1add63c8506db4d890962e8
node --version | grep -Fx v24.16.0
node -e 'if(require("./upstream/package.json").version!=="2026.10.5")process.exit(1)'
for file in lab/ci/clean-v1-crossrunner-fake-provider.mjs lab/ci/clean-v1-crossrunner-pilot.mjs lab/ci/clean-v1-crossrunner.Dockerfile; do
  test -s "$file"
done
archive="$RUNNER_TEMP/clean-v1-crossrunner-state.tar"
if test "$mode" = restore; then
  archive="$RUNNER_TEMP/recovery-input/clean-v1-crossrunner-state.tar"
  test -s "$archive"
  export CI_EXPECTED_ARCHIVE_SHA
  python3 - "$archive" <<'PY'
import hashlib,io,os,pathlib,sys,tarfile
source=pathlib.Path(sys.argv[1]).read_bytes()
assert 0<len(source)<64*1024*1024, "Archive oversize or empty"
expected=os.environ["CI_EXPECTED_ARCHIVE_SHA"]
assert len(expected)==64 and all(c in "0123456789abcdef" for c in expected)
assert hashlib.sha256(source).hexdigest()==expected, "Mismatched cross-job archive SHA"
print("SECOND_RUNNER_INDEPENDENT_SHA256_MATCH=PASS")
tampered=bytearray(source);tampered[len(tampered)//2]^=1
assert hashlib.sha256(tampered).hexdigest()!=expected
print("CORRUPTED_TRANSFER_DIGEST_REJECTED=PASS")
def scan(content):
  members=set();total=0
  with tarfile.open(fileobj=io.BytesIO(content),mode="r:") as tar:
    rows=tar.getmembers()
    assert 0<len(rows)<6000
    for item in rows:
      n=item.name[2:] if item.name.startswith("./") else item.name
      if n in ("","."): continue
      parts=pathlib.PurePosixPath(n).parts
      assert not n.startswith("/") and ".." not in parts and "\\" not in n, "unsafe archive path"
      assert item.isdir() or item.isfile(), "link or device disallowed"
      total+=item.size
      assert total<64*1024*1024, "oversized archive"
      members.add(n)
  return members
names=scan(source)
assert {"state/openclaw.json","state/fictional-proof.txt","workspace/persisted-fake-note.txt"}<=names
print("SECOND_RUNNER_FULL_FICTIONAL_ARCHIVE_LAYOUT_VALIDATED=PASS")
bad=io.BytesIO()
with tarfile.open(fileobj=bad,mode="w") as tar:
  member=tarfile.TarInfo("../unexpected-fake-path")
  member.size=1;tar.addfile(member,io.BytesIO(b"X"))
try:scan(bad.getvalue())
except AssertionError:print("PATH_TRAVERSAL_IN_ARCHIVE_REJECTED=PASS")
else:raise AssertionError("unsafe archive was not rejected")
bad=io.BytesIO()
with tarfile.open(fileobj=bad,mode="w") as tar:
  member=tarfile.TarInfo("state/link")
  member.type=tarfile.SYMTYPE
  member.linkname="/invalid-fake"
  tar.addfile(member)
try:scan(bad.getvalue())
except AssertionError:print("SYMLINK_ALIAS_IN_ARCHIVE_REJECTED=PASS")
else:raise AssertionError("link was not rejected")
PY
  echo "NO_ARCHIVE_EXTRACTED_BEFORE_VALIDATION=PASS"
fi

# Only pinned public source/dependencies, on a disposable runner with no personal data.
npm install --global pnpm@12.9.0
pnpm -C upstream install --frozen-lockfile
env -i PATH="$PATH" HOME=/tmp CI=true pnpm -C upstream openclaw --version
test -f upstream/dist/entry.js -o -f upstream/dist/entry.mjs
cp lab/ci/clean-v1-crossrunner-fake-provider.mjs upstream/ci-fake-provider.mjs
cp lab/ci/clean-v1-crossrunner-pilot.mjs upstream/ci-container-pilot.mjs
cp lab/ci/clean-v1-crossrunner.Dockerfile upstream/Dockerfile.ci-crossrunner
cat > upstream/.dockerignore <<'IGNORE'
.git
.github
**/.git
**/.cache
*.log
IGNORE
echo "PUBLIC_PINNED_OPENCLAW_BUILT_ON_INDEPENDENT_RUNNER=PASS"

base="node:24.16.0-bookworm-slim@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203"
docker pull "$base" >/dev/null
tag="clean-v1-crossrunner:$GITHUB_RUN_ID"
docker build --network none --pull=false -f upstream/Dockerfile.ci-crossrunner -t "$tag" upstream
image_sha="$(docker image inspect --format '{{.Id}}' "$tag")"
test -n "$image_sha"
echo "IMAGE_BUILT_FROM_EXACT_PUBLIC_SOURCE_AND_PINNED_BASE=PASS"

vol="clean-v1-crossrunner-$mode-$GITHUB_RUN_ID"
name="clean-v1-crossrunner-$mode-agent-$GITHUB_RUN_ID"
if docker volume inspect "$vol" >/dev/null 2>&1; then
  echo "NONEMPTY_OR_REUSED_VOLUME_REFUSED=PASS"
  exit 1
fi
cleanup(){
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker volume rm -f "$vol" >/dev/null 2>&1 || true
  docker image rm "$tag" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker volume create --driver local --label ci.openclaw=fresh-fiction-only --label "ci.run=$GITHUB_RUN_ID" "$vol" >/dev/null
python3 - "$vol" "$GITHUB_RUN_ID" <<'PY'
import json,subprocess,sys
d=json.loads(subprocess.check_output(["docker","volume","inspect",sys.argv[1]],text=True))[0]
assert d["Name"]==sys.argv[1] and d["Driver"]=="local"
assert d["Labels"]=={"ci.openclaw":"fresh-fiction-only","ci.run":sys.argv[2]}
assert d.get("Options") in (None,{})
print("NEW_DOCKER_MANAGED_FICTION_ONLY_VOLUME=PASS")
PY

if test "$mode" = restore; then
  # Read strictly validated archive through stdin, into only the newly created Docker volume.
  docker run --rm -i \
    --network none --read-only --user 10001:10001 \
    --cap-drop ALL --security-opt no-new-privileges \
    --pids-limit 64 --memory 256m --ipc private \
    --mount "type=volume,source=$vol,target=/home/ci" \
    --tmpfs /tmp:rw,nosuid,nodev,size=16m \
    --entrypoint tar "$tag" \
    -C /home/ci --strip-components=1 --no-same-owner --no-same-permissions -xf - < "$archive"
  echo "INDEPENDENT_RUNNER_FRESH_VOLUME_IMPORTED=PASS"
fi

fixture="$RUNNER_TEMP/other-host-only-fiction-marker.txt"
printf 'OUTSIDE_NEW_VOLUME_FICTION_ONLY\n' > "$fixture"
pilot_mode=first
test "$mode" = restore && pilot_mode=restart
docker run --name "$name" \
  --network none --read-only --user 10001:10001 \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 256 --memory 3g --cpus 2 --ipc private \
  --mount "type=volume,source=$vol,target=/home/ci" \
  --tmpfs /tmp:rw,nosuid,nodev,uid=10001,gid=10001,mode=1777,size=128m \
  --env "HOST_ONLY_FICTION_PATH=$fixture" \
  --env "CI_PILOT_MODE=$pilot_mode" "$tag"
python3 - "$name" "$vol" "$image_sha" <<'PY'
import json,subprocess,sys
d=json.loads(subprocess.check_output(["docker","inspect",sys.argv[1]],text=True))[0]
h=d["HostConfig"];v=d["Mounts"]
assert d["State"]["ExitCode"]==0
assert d["Image"]==sys.argv[3]
assert h["NetworkMode"]=="none" and h["ReadonlyRootfs"] is True
assert h["Privileged"] is False and "ALL" in h["CapDrop"]
assert "no-new-privileges" in h["SecurityOpt"]
assert h["Binds"] in (None,[]) and h["Devices"] in (None,[])
assert d["Config"]["User"]=="10001:10001"
assert h.get("PortBindings") in (None,{})
assert h["PidsLimit"]==256 and h["IpcMode"]=="private"
assert h["Memory"]==3221225472
assert len(v)==1 and v[0]["Type"]=="volume" and v[0]["Name"]==sys.argv[2]
assert v[0]["Destination"]=="/home/ci" and v[0]["RW"] is True
assert all(m["Type"]!="bind" for m in v)
assert "/tmp" in h["Tmpfs"] and "/home/ci" not in h["Tmpfs"]
print("FULL_OPENCLAW_ISOLATED_ONE_FRESH_VOLUME_NO_HOST_BIND=PASS")
print("FULL_OPENCLAW_NO_EXTERNAL_NETWORK_NONROOT=PASS")
PY
docker rm "$name" >/dev/null
if test "$mode" = restore; then
  echo "SECOND_RUNNER_REAL_OPENCLAW_AGENT_RESTORED_AND_ANSWERED=PASS"
  echo "NO_MAC_NO_HERMES_NO_OLD_OPENCLAW_NO_REAL_PROVIDER_NO_PRODUCTION"
  exit 0
fi

# Export the *entire* newly created fictional state, after the Gateway has shut down.
echo "PRODUCER_GATEWAY_STOPPED_BEFORE_FICTIONAL_SNAPSHOT=PASS"
test ! -e "$archive"
docker run --rm \
  --network none --read-only --user 10001:10001 \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 256m --ipc private \
  --mount "type=volume,source=$vol,target=/home/ci,readonly" \
  --tmpfs /tmp:rw,nosuid,nodev,size=16m \
  --entrypoint tar "$tag" -C /home/ci -cf - . > "$archive"
python3 - "$archive" <<'PY'
import pathlib,sys,tarfile
p=pathlib.Path(sys.argv[1])
assert p.is_file() and 0<p.stat().st_size<64*1024*1024
seen=set();total=0
with tarfile.open(p,"r:") as tar:
  rows=tar.getmembers()
  assert 0<len(rows)<6000
  for item in rows:
    n=item.name[2:] if item.name.startswith("./") else item.name
    if n in ("","."): continue
    parts=pathlib.PurePosixPath(n).parts
    assert not n.startswith("/") and ".." not in parts and "\\" not in n
    assert item.isdir() or item.isfile(), "links or devices not accepted"
    total+=item.size
    assert total<64*1024*1024
    seen.add(n)
assert {"state/openclaw.json","state/fictional-proof.txt","workspace/persisted-fake-note.txt"}<=seen
print("FULL_FICTIONAL_VOLUME_ARCHIVE_PREVALIDATED=PASS")
PY
sha="$(sha256sum "$archive" | cut -d' ' -f1)"
test -n "$sha"
printf 'sha256=%s\n' "$sha" >> "$GITHUB_OUTPUT"
echo "FICTIONAL_VOLUME_ARCHIVE_SHA256=$sha"
echo "ONLY_NEW_OPENCLAW_VOLUME_WAS_ARCHIVED=PASS"