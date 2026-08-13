#!/usr/bin/env bash
set -euo pipefail

EXPECTED_SHA="b854a8316ecc1003ea9f2806ceb9dea229c9f276f881b942dad3dc2c46e30f87"
SNAPSHOT_ID="1ufivwWBMohoPzaNj_8maCWWe8MTEQxrt"
SNAPSHOT_URL="${BINARIO_SOURCE_SNAPSHOT_URL:-https://drive.google.com/uc?export=download&id=${SNAPSHOT_ID}}"
REPO_ROOT="${1:-$(pwd)}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/binario-source-hydrate.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

cd "$REPO_ROOT"

if [[ ! -f config/development.json || ! -f .release-blocked ]]; then
  echo "Refusing hydration outside the governed R27 repository." >&2
  exit 2
fi

python3 - <<'PY'
import json
from pathlib import Path
p=Path('config/development.json')
d=json.loads(p.read_text(encoding='utf-8'))
assert d.get('canonical_repository')=='arendon7/BINARIOIA', d
assert d.get('cycle')=='R27', d
assert d.get('release_blocked') is True, d
print('Governance identity PASS')
PY

ARCHIVE="$WORK/R26_SOURCE_TEXT.tar.gz"
echo "Downloading certified source custody snapshot…"
curl -fL --retry 2 --retry-delay 1 --connect-timeout 20 "$SNAPSHOT_URL" -o "$ARCHIVE" || true
ACTUAL_SHA="$(shasum -a 256 "$ARCHIVE" 2>/dev/null | awk '{print $1}')"
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
  echo "Direct Drive download did not yield the certified bytes; using gdown fallback."
  rm -f "$ARCHIVE"
  python3 -m pip install --disable-pip-version-check -q gdown
  gdown "$SNAPSHOT_ID" -O "$ARCHIVE"
  ACTUAL_SHA="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
fi
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
  echo "SHA mismatch: expected $EXPECTED_SHA got $ACTUAL_SHA" >&2
  exit 3
fi
echo "Snapshot SHA PASS · $ACTUAL_SHA"

mkdir -p "$WORK/extracted"
tar -xzf "$ARCHIVE" -C "$WORK/extracted"

SOURCE_ROOT="$(python3 - "$WORK/extracted" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
candidates=[root]
candidates += [p for p in root.rglob('*') if p.is_dir() and len(p.relative_to(root).parts)<=4]
for p in candidates:
    if (p/'apps').is_dir() and (p/'common').is_dir() and (p/'r26').is_dir():
        print(p)
        raise SystemExit(0)
raise SystemExit('Could not locate certified source root inside snapshot')
PY
)"

echo "Certified source root: $SOURCE_ROOT"

# R27 wins conflicts: baseline is allowed to fill missing paths only.
rsync -a --ignore-existing \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache/' \
  "$SOURCE_ROOT"/ "$REPO_ROOT"/

python3 - <<'PY'
from pathlib import Path
required=['apps','common','hub','runtime','r26','scripts','tests','config']
missing=[x for x in required if not Path(x).exists()]
assert not missing, missing
apps=sorted(p.name for p in Path('apps').iterdir() if p.is_dir() and p.name[:2].isdigit())
assert len(apps)>=12, apps
print(f'Hydration filesystem check PASS · {len(apps)} app directories')
PY

printf '%s\n' "$EXPECTED_SHA" > config/R26_SOURCE_SNAPSHOT_SHA256.txt

echo "Hydration completed. Existing R27 files were preserved."
git status --short
