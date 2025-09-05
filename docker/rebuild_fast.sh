#!/bin/bash

set -euo pipefail

API_URL="http://localhost:5001/api"
EXPORT_PATH="/tmp/anki_collection.apkg"
ANKI_USERNAME="User 1"

# Export collection if possible (best-effort)
curl -X POST "${API_URL}/export-collection-package?username=$(echo ${ANKI_USERNAME} | sed 's/ /%20/g')" \
     -H "Content-Type: application/json" \
     -d "{\"out_path\": \"/tmp/anki_collection.apkg\", \"include_media\": true, \"legacy\": true}" \
     --fail --silent --show-error -o ${EXPORT_PATH} || true

docker container stop anki-api || true
docker container rm anki-api || true
docker image rm anki-api || true
docker system prune --force --volumes || true

ANKI_DIR="../anki"
if git -C "${ANKI_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ANKI_COMMIT=$(git -C "${ANKI_DIR}" rev-parse HEAD)
else
  echo "Error: ${ANKI_DIR} is not a git repository. Please ensure Anki is cloned as a git repo/submodule."
  exit 1
fi

echo "Target Anki commit: ${ANKI_COMMIT}"

if docker image inspect "anki-core:${ANKI_COMMIT}" >/dev/null 2>&1; then
  echo "Using cached base image anki-core:${ANKI_COMMIT}"
else
  echo "Building base image anki-core:${ANKI_COMMIT} (one-time)"
  docker build --no-cache \
    --tag "anki-core:${ANKI_COMMIT}" \
    --build-arg ANKI_COMMIT="${ANKI_COMMIT}" \
    --file Dockerfile.base \
    ..
fi

docker build \
  --tag anki-api \
  --build-arg ANKI_COMMIT="${ANKI_COMMIT}" \
  --file Dockerfile.app \
  ..

docker run -p 5001:5001 -p 5678:5678 --name anki-api anki-api

# Restore collection if exported
curl -X POST "${API_URL}/users/create/$(echo ${ANKI_USERNAME} | sed 's/ /%20/g')" || true
curl -X POST "${API_URL}/import-package?username=$(echo ${ANKI_USERNAME} | sed 's/ /%20/g')" \
    -F "file=@${EXPORT_PATH}" \
    --fail --silent --show-error || true
rm -f ${EXPORT_PATH} || true

echo "Rebuild (fast path) completed."

