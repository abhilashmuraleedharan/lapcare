# SPDX-License-Identifier: GPL-3.0-or-later
# Development/validation container for lapcare. Build from the repo root:
#   docker build --build-arg UBUNTU_VERSION=24.04 -t lapcare-dev:24.04 -f tools/containers/Dockerfile .
# Normally driven by tools/dev-container.sh (via ./run --lts / ./check --lts).
ARG UBUNTU_VERSION=24.04
FROM ubuntu:${UBUNTU_VERSION}

COPY tools/install-deps.sh /tmp/install-deps.sh
RUN sh /tmp/install-deps.sh && rm -rf /var/lib/apt/lists/*
