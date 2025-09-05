#!/usr/bin/env bash

set -euo pipefail

# Export a Docker image to a compressed tarball, ready for upload.
#
# Usage:
#   ./export_image.sh [-i image[:tag]] [-o out.tar.gz]
#
# Defaults:
#   - image: anki-api (as built by build.sh)
#   - out: exports/anki-api-<image>-<date>-<id>.tar.gz

IMAGE_REF="${IMAGE_REF:-}"
OUT_FILE="${OUT_FILE:-}"

usage() {
  echo "Usage: $0 [-i image[:tag]] [-o out.tar.gz]" >&2
}

while getopts ":i:o:h" opt; do
  case ${opt} in
    i) IMAGE_REF=${OPTARG} ;;
    o) OUT_FILE=${OPTARG} ;;
    h) usage; exit 0 ;;
    :) echo "Option -${OPTARG} requires an argument" >&2; usage; exit 1 ;;
    \?) echo "Invalid option: -${OPTARG}" >&2; usage; exit 1 ;;
  esac
done

IMAGE_REF=${IMAGE_REF:-anki-api}

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker not found in PATH" >&2
  exit 1
fi

# Ensure the image exists locally
if ! docker image inspect "${IMAGE_REF}" >/dev/null 2>&1; then
  echo "Error: image '${IMAGE_REF}' not found locally. Build it first (e.g. ./build.sh)." >&2
  exit 1
fi

# Derive defaults for output path
mkdir -p exports
IMG_SAFE=$(echo "${IMAGE_REF}" | tr '/:' '__')
DATE_STR=$(date +%Y%m%d-%H%M%S)
IMG_ID=$(docker image inspect -f '{{.Id}}' "${IMAGE_REF}" | sed 's/^sha256://; s/\(..............\).*/\1/')
OUT_FILE=${OUT_FILE:-exports/anki-api-${IMG_SAFE}-${DATE_STR}-${IMG_ID}.tar.gz}

echo "Saving image '${IMAGE_REF}' to '${OUT_FILE}' ..."

# Prefer pigz for speed if available
if command -v pigz >/dev/null 2>&1; then
  docker save "${IMAGE_REF}" | pigz -1 > "${OUT_FILE}"
else
  docker save "${IMAGE_REF}" | gzip -1 > "${OUT_FILE}"
fi

SHA_FILE="${OUT_FILE}.sha256"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${OUT_FILE}" > "${SHA_FILE}"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "${OUT_FILE}" > "${SHA_FILE}"
fi

echo "Done. File ready for upload: ${OUT_FILE}"
if [ -f "${SHA_FILE}" ]; then
  echo "Checksum written to: ${SHA_FILE}"
fi

