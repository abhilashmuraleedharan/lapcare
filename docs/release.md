# Release Strategy

Decision record: ADR-0005 (packaging). Labels and gates: `ROADMAP.md`.

## Cadence & versioning

SemVer. Pre-1.0: every milestone close tags `0.N.0`. Post-MVP: time-boxed minor releases
roughly every 6–8 weeks; patch releases as needed. `1.0` = MVP definition met and stable on
two LTS releases. Support: latest release only pre-1.0; post-1.0, latest minor + security
fixes for the previous one.

## Staged public labels

- **M2 close → public alpha (v0.3.0):** first announcement. Read-only, zero privileges —
  lowest-risk first exposure. All hygiene files (SECURITY, CoC, templates, trademark
  disclaimer, fixture policy) must already exist (done in M0).
- **M3 close → beta (v0.4.0):** firmware updates get a full cycle of field testing before 1.0.

## Channels

1. **Ubuntu PPA (.deb)** — primary (pipeline lands in M5).
2. **GitHub Releases** — source tarball + CI-built .deb from tags.
3. **Flatpak** — deferred per ADR-0005; revisit at M11.

Releases are built **only in CI from tags** — never on maintainer machines (supply-chain
rule, `docs/security-design.md`). Release notes are generated from `CHANGELOG.md`.

## Distro portability

Install paths (libexecdir, polkit policy dir) are Meson options. Non-Debian packaging is
community-owned; `docs/packaging.md` (M5) documents everything a packager needs (paths,
AppStream metainfo, uninstall behavior — the .deb handles policy/helper removal on purge).
