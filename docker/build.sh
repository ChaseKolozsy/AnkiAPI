#!/bin/bash

set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-anki-api}"
CONTAINER_NAME="${CONTAINER_NAME:-anki-api}"
HOST_PORT="${HOST_PORT:-5001}"
# Optional override for host Anki2 dir; if empty, auto-detect by OS
HOST_ANKI2_DIR="${HOST_ANKI2_DIR:-}"
# Optional OS selector: linux|mac|windows; if empty, auto-detect
SYSTEM_OVERRIDE="${SYSTEM_OVERRIDE:-}"

usage() {
  echo "Usage: $0 [-i image_name] [-c container_name] [-p host_port] [-m host_anki2_dir] [-s linux|mac|windows]" >&2
  echo "  Defaults: -i ${IMAGE_NAME} -c ${CONTAINER_NAME} -p ${HOST_PORT}" >&2
  echo "  If -m not provided, tries OS-specific defaults for Anki2 directory." >&2
}

while getopts ":i:c:p:m:s:h" opt; do
  case ${opt} in
    i) IMAGE_NAME=${OPTARG} ;;
    c) CONTAINER_NAME=${OPTARG} ;;
    p) HOST_PORT=${OPTARG} ;;
    m) HOST_ANKI2_DIR=${OPTARG} ;;
    s) SYSTEM_OVERRIDE=${OPTARG} ;;
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

# OS selection (auto-detect unless -s provided)
UNAME_S=$(uname -s 2>/dev/null || echo unknown)
SELECTED_OS=${SYSTEM_OVERRIDE}
if [ -z "${SELECTED_OS}" ]; then
  case "${UNAME_S}" in
    Darwin*) SELECTED_OS="mac" ;;
    Linux*) SELECTED_OS="linux" ;;
    CYGWIN*|MINGW*|MSYS*) SELECTED_OS="windows" ;;
    *) SELECTED_OS="linux" ;;
  esac
fi

case "${SELECTED_OS}" in
  linux)
    HOST_ANKI2_DIR=${HOST_ANKI2_DIR:-"$HOME/.local/share/Anki2"}
    mkdir -p "${HOST_ANKI2_DIR}" || true
    echo "[linux] Mounting host collection: ${HOST_ANKI2_DIR} -> /home/anki/.local/share/Anki2"
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    docker run -d --restart unless-stopped \
      -p "${HOST_PORT}:5001" \
      -e HTTP_PROXY= -e HTTPS_PROXY= -e ALL_PROXY= \
      -e NO_PROXY=sync.ankiweb.net,localhost,127.0.0.1 \
      -v "${HOST_ANKI2_DIR}:/home/anki/.local/share/Anki2" \
      --cpus=1 \
      --name "${CONTAINER_NAME}" \
      "${IMAGE_NAME}"
    ;;
  mac)
    HOST_ANKI2_DIR=${HOST_ANKI2_DIR:-"$HOME/Library/Application Support/Anki2"}
    mkdir -p "${HOST_ANKI2_DIR}" || true
    echo "[mac] Mounting host collection: ${HOST_ANKI2_DIR} -> /home/anki/.local/share/Anki2"
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    docker run -d --restart unless-stopped \
      -p "${HOST_PORT}:5001" \
      -e HTTP_PROXY= -e HTTPS_PROXY= -e ALL_PROXY= \
      -e NO_PROXY=sync.ankiweb.net,localhost,127.0.0.1 \
      -v "${HOST_ANKI2_DIR}:/home/anki/.local/share/Anki2" \
      --cpus=1 \
      --name "${CONTAINER_NAME}" \
      "${IMAGE_NAME}"
    ;;
  windows)
    if [ -z "${HOST_ANKI2_DIR}" ]; then
      if [ -n "${APPDATA:-}" ]; then
        HOST_ANKI2_DIR="${APPDATA}\\Anki2"
      else
        HOST_ANKI2_DIR="%APPDATA%\\Anki2"
      fi
    fi
    echo "[windows] Mounting host collection: ${HOST_ANKI2_DIR} -> /home/anki/.local/share/Anki2"
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    docker run -d --restart unless-stopped \
      -p "${HOST_PORT}:5001" \
      -e HTTP_PROXY= -e HTTPS_PROXY= -e ALL_PROXY= \
      -e NO_PROXY=sync.ankiweb.net,localhost,127.0.0.1 \
      -v "${HOST_ANKI2_DIR}:/home/anki/.local/share/Anki2" \
      --cpus=1 \
      --name "${CONTAINER_NAME}" \
      "${IMAGE_NAME}"
    ;;
  *)
    echo "Unknown OS selection: ${SELECTED_OS}" >&2
    exit 1
    ;;
esac
