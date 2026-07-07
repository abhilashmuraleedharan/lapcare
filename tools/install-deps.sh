#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Install build/test system dependencies on Ubuntu 24.04+.
# Single source of truth, used by tools/containers/Dockerfile and CI.
set -eu

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    python3 \
    python3-pip \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-4.0 \
    gir1.2-adw-1 \
    meson \
    ninja-build \
    blueprint-compiler \
    desktop-file-utils \
    appstream \
    libglib2.0-bin \
    gettext \
    dbus \
    xvfb \
    xauth \
    python3-dbusmock
