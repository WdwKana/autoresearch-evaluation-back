#!/usr/bin/env bash
# Persistence backstop: before force-removing a work container, copy out any
# artifact-bearing trees that might live in its ephemeral layer (writes that
# escaped the mounted universe). Verbatim docker cp; never follows the copy
# with any content transformation. Usage:
#   harvest_before_rm.sh <container> <dest_dir> [path ...]
# Default paths cover the known framework worldview roots. Missing paths are
# skipped silently (most runs write only into mounts and harvest nothing).
set -uo pipefail
C="${1:?container}"; DEST="${2:?dest dir}"; shift 2
PATHS=("$@"); [ ${#PATHS[@]} -gt 0 ] || PATHS=(/project /workplace /workspace/project)
mkdir -p "$DEST"
harvested=0
for p in "${PATHS[@]}"; do
  # only harvest if the path exists in the container AND is not just a mount
  if docker exec "$C" test -d "$p" 2>/dev/null; then
    if docker cp "$C:$p" "$DEST/$(basename "$p")_harvest" 2>/dev/null; then
      echo "[harvest] $C:$p -> $DEST/$(basename "$p")_harvest"
      harvested=$((harvested+1))
    fi
  fi
done
echo "[harvest] $harvested tree(s) harvested from $C"
docker rm -f "$C" >/dev/null 2>&1 && echo "[harvest] container $C removed"
