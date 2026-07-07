#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Run a command in a lapcare dev container for a given Ubuntu LTS.
# Usage: tools/dev-container.sh <24.04|26.04> <command> [args...]
# Used by ./run --lts and ./check --lts; X11 is forwarded when available so
# GUI runs work from container (host may need: xhost +si:localuser:root).
set -eu

LTS="${1:?usage: dev-container.sh <24.04|26.04> <command> [args...]}"
shift
[ $# -gt 0 ] || { echo "dev-container.sh: missing command" >&2; exit 2; }

REPO="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="lapcare-dev:${LTS}"

docker build --quiet \
    --build-arg UBUNTU_VERSION="${LTS}" \
    -t "${IMAGE}" \
    -f "${REPO}/tools/containers/Dockerfile" \
    "${REPO}" >/dev/null

X11_ARGS=""
if [ -n "${DISPLAY:-}" ] && [ -d /tmp/.X11-unix ]; then
    X11_ARGS="-e DISPLAY=${DISPLAY} -v /tmp/.X11-unix:/tmp/.X11-unix"
fi

# Run as the host user so build artifacts in the mounted workspace are not
# root-owned; HOME points at /tmp because that uid has no passwd entry.
# shellcheck disable=SC2086  # X11_ARGS is deliberately word-split
exec docker run --rm -i ${X11_ARGS} \
    -u "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -v "${REPO}":/workspace \
    -w /workspace \
    -e LAPCARE_DEBUG="${LAPCARE_DEBUG:-}" \
    "${IMAGE}" "$@"
