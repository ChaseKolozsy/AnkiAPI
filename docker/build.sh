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

# Fast path: build a reusable base for the current Anki commit, then the app image
ANKI_DIR="../anki"
if git -C "${ANKI_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ANKI_COMMIT=$(git -C "${ANKI_DIR}" rev-parse HEAD)
else
  echo "Error: ${ANKI_DIR} is not a git repository. Ensure Anki is cloned as a git repo/submodule." >&2
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
  --tag "${IMAGE_NAME}" \
  --build-arg ANKI_COMMIT="${ANKI_COMMIT}" \
  --file Dockerfile.app \
  ..

# Run the Docker container (replace if exists)
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
docker run -p "${HOST_PORT}:5001" --cpus=1 --name "${CONTAINER_NAME}" "${IMAGE_NAME}"
