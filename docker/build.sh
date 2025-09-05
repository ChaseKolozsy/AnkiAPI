#!/bin/bash

set -euo pipefail

# Defaults for testing: different image/container names and port
IMAGE_NAME="${IMAGE_NAME:-anki-api-test}"
CONTAINER_NAME="${CONTAINER_NAME:-anki-api-test}"
HOST_PORT="${HOST_PORT:-5002}"

usage() {
  echo "Usage: $0 [-i image_name] [-c container_name] [-p host_port]" >&2
  echo "  Defaults: -i ${IMAGE_NAME} -c ${CONTAINER_NAME} -p ${HOST_PORT}" >&2
}

while getopts ":i:c:p:h" opt; do
  case ${opt} in
    i) IMAGE_NAME=${OPTARG} ;;
    c) CONTAINER_NAME=${OPTARG} ;;
    p) HOST_PORT=${OPTARG} ;;
    h) usage; exit 0 ;;
    :) echo "Option -${OPTARG} requires an argument" >&2; usage; exit 1 ;;
    \?) echo "Invalid option: -${OPTARG}" >&2; usage; exit 1 ;;
  esac
done

echo "Building image '${IMAGE_NAME}' and running container '${CONTAINER_NAME}' on port ${HOST_PORT} -> 5001"

# Step 1: Prepare an isolated build context that includes a real .git dir
ANKI_SRC="../anki"
BUILD_CTX=$(mktemp -d -p . anki-build-XXXXXX)

# Sync source (excluding .git placeholder)
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude='.git' "${ANKI_SRC}/" "${BUILD_CTX}/"
else
  echo "rsync not found; falling back to cp -a (slower)" >&2
  mkdir -p "${BUILD_CTX}"
  (cd "${ANKI_SRC}" && find . -path './.git' -prune -o -print0 | xargs -0 -I{} bash -c 'src="{}"; dst="${0%/}/$src"; mkdir -p "$(dirname "$dst")"; [ -d "$src" ] && mkdir -p "$dst" || cp -a "$src" "$dst"' "${BUILD_CTX}")
fi

# Inject API server files into the build context
cp ../anki_api_server.py "${BUILD_CTX}/"
cp ../blueprint_decks.py "${BUILD_CTX}/"
cp ../blueprint_exports.py "${BUILD_CTX}/"
cp ../blueprint_imports.py "${BUILD_CTX}/"
cp ../blueprint_notetypes.py "${BUILD_CTX}/"
cp ../blueprint_users.py "${BUILD_CTX}/"
cp ../blueprint_cards.py "${BUILD_CTX}/"
cp ../blueprint_study_sessions.py "${BUILD_CTX}/"
cp ../blueprint_db.py "${BUILD_CTX}/"
cp ../qt/tools/new/build_ui.py "${BUILD_CTX}/qt/tools/"

# Resolve and copy the actual git dir so Anki's build can invoke git
if git -C "${ANKI_SRC}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_DIR=$(git -C "${ANKI_SRC}" rev-parse --git-dir)
  # Make absolute if necessary
  if [[ "${GIT_DIR}" != /* ]]; then
    GIT_DIR=$(cd "${ANKI_SRC}" && cd "${GIT_DIR}" && pwd)
  fi
  if [ -d "${GIT_DIR}" ]; then
    mkdir -p "${BUILD_CTX}/.git"
    rsync -a "${GIT_DIR}/" "${BUILD_CTX}/.git/"
  fi
fi

# Step 2: Build the Docker image from source using the isolated context
docker build --no-cache --tag "${IMAGE_NAME}" --file Dockerfile.source "${BUILD_CTX}"

# Step 3: Clean up the temporary build context
rm -rf "${BUILD_CTX}"

# Step 4: Run the Docker container (replace if exists)
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
docker run -p "${HOST_PORT}:5001" --cpus=1 --name "${CONTAINER_NAME}" "${IMAGE_NAME}"
