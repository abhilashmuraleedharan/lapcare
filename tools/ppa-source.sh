#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Build per-series PPA *source* packages in containers (host needs only docker).
#
#   tools/ppa-source.sh [ppa-revision]     # default revision: 1
#
# Output: dist-ppa/<series>/lapcare_<version>+ppa<N>~<series>1_source.changes
# (+ .dsc/.tar.xz), UNSIGNED. The maintainer signs and uploads on the host:
#
#   debsign dist-ppa/noble/lapcare_*_source.changes
#   dput ppa:<launchpad-user>/lapcare dist-ppa/noble/lapcare_*_source.changes
#
# Full runbook: docs/release.md ("PPA runbook"). Source packages are
# series-independent to BUILD (only the changelog stanza differs), so one
# builder image covers all series.
set -eu

HERE="$(cd "$(dirname "$0")/.." && pwd)"
REV="${1:-1}"
VERSION="$(sed -n "s/^  version: '\(.*\)',$/\1/p" "${HERE}/meson.build")"
[ -n "$VERSION" ] || { echo "could not read version from meson.build" >&2; exit 1; }

# Target Ubuntu LTS series (docs/testing.md targets): 24.04, 26.04.
SERIES="noble resolute"
BUILDER_IMAGE="ubuntu:24.04"
OUT="${HERE}/dist-ppa"
rm -rf "$OUT"

for series in $SERIES; do
    mkdir -p "$OUT/$series"
    echo "== source package for ${series} (${VERSION}+ppa${REV}~${series}1) =="
    docker run --rm \
        -v "$HERE:/src:ro" -v "$OUT/$series:/out" \
        -e "DEBEMAIL=amuraleedharan13@gmail.com" \
        -e "DEBFULLNAME=Abhilash Muraleedharan" \
        "$BUILDER_IMAGE" sh -ec "
            export DEBIAN_FRONTEND=noninteractive
            apt-get update -qq && apt-get install -y -qq --no-install-recommends \
                devscripts debhelper dpkg-dev >/dev/null
            mkdir -p /build && cp -a /src /build/lapcare && cd /build/lapcare
            rm -rf build build2604 dist-ppa .git
            dch -v '${VERSION}+ppa${REV}~${series}1' -D '${series}' \
                --force-distribution 'PPA upload for ${series}.'
            dpkg-buildpackage -S -us -uc -d
            cp ../lapcare_* /out/
        "
done

echo
echo "Unsigned source packages in dist-ppa/. Next (maintainer, on the host):"
echo "  debsign dist-ppa/<series>/lapcare_*_source.changes"
echo "  dput ppa:<launchpad-user>/lapcare dist-ppa/<series>/lapcare_*_source.changes"
