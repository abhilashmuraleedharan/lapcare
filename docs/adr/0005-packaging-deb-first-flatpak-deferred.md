# ADR-0005: Packaging — native .deb first; Flatpak deliberately deferred

- **Status:** Accepted
- **Date:** 2026-07-06
- **Deciders:** Project owner, Lead Architect

## Context

Lapcare wants tight system integration: a polkit policy in `/usr/share/polkit-1`, a helper in
`/usr/libexec`, arbitrary sysfs reads, and host tools (`smartctl`, `nvme`). The Flatpak
sandbox blocks arbitrary sysfs access, pkexec helpers, and host binaries; the fwupd/UPower
portions would work via D-Bus talk permissions, but the result would be a half-functional
app. Users increasingly expect Flatpak, so the deferral must be public and reasoned.

## Decision

We will ship **native .deb packages via an Ubuntu PPA as the primary channel**, plus source
tarballs and CI-built .debs on GitHub Releases. Install paths (libexecdir, polkit policy dir)
are Meson options so other distros can package cleanly; non-Debian packaging is explicitly
**community-owned** (`docs/packaging.md`, M5). **Flatpak is deferred** until the privileged
D-Bus system service contemplated in ADR-0004 exists, since that architecture is
sandbox-compatible; revisit then (roadmap M11).

## Consequences

- Honest packaging: everything the app promises works when installed.
- We maintain PPA infrastructure (pipeline target: M5) and a `debian/` tree from M0 (CI builds
  it, catching packaging drift early).
- Some users will ask "why no Flatpak?" — README/FAQ answers with this ADR's reasoning.
- CI full lane builds and install-tests the .deb on every supported LTS.

## Alternatives Considered

- **Flatpak-first:** rejected for MVP — shipping with storage health and the helper
  non-functional damages the product promise more than a missing channel does.
- **Snap:** rejected — same sandbox constraints, plus a GNOME-app audience mismatch; not
  worth dual sandbox engineering.
- **AppImage:** rejected — no story at all for polkit policy installation.
