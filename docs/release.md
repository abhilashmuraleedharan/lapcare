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

1. **Ubuntu PPA (.deb)** — primary (pipeline landed in M5; runbook below).
2. **GitHub Releases** — source tarball + CI-built .deb from tags.
3. **Flatpak** — deferred per ADR-0005; revisit at M11.

## PPA runbook (maintainer)

The pipeline builds **unsigned per-series source packages**; signing never leaves the
maintainer's machine (CI holds no keys). Verified at M5: both series' source packages
build to binaries in clean containers with ONLY the declared Build-Depends — the
Launchpad-faithful check (`mk-build-deps`), which caught two Build-Depends gaps CI's
fuller environment had masked.

**One-time setup**

1. Launchpad account; create the `lapcare` PPA (web UI: Create a new PPA).
2. GPG key: `gpg --full-generate-key` (RSA 4096), publish it —
   `gpg --send-keys --keyserver keyserver.ubuntu.com <KEYID>` — and register the
   fingerprint on your Launchpad profile (confirmation mail must be decrypted).
3. Host tools (fine on Ubuntu 22.04): `sudo apt install devscripts dput gnupg`.

**Per release** (after the `vX.Y.Z` tag is pushed and full-lane is green)

1. Get the source packages — either locally (`tools/ppa-source.sh [rev]` → `dist-ppa/`)
   or download the tag's `lapcare-ppa-source` CI artifact (same content).
2. Sign: `debsign dist-ppa/<series>/lapcare_*_source.changes` (both series).
3. Upload: `dput ppa:<launchpad-user>/lapcare dist-ppa/<series>/lapcare_*_source.changes`.
4. Wait for Launchpad's builders (accepted-mail, then build success on the PPA page).
5. **Install verification on both LTS** (the M5 acceptance criterion), in clean
   containers:

   ```sh
   docker run --rm ubuntu:24.04 sh -ec 'apt-get update -qq; \
     apt-get install -y -qq software-properties-common; \
     add-apt-repository -y ppa:<launchpad-user>/lapcare; \
     apt-get install -y lapcare; lapcare --version'
   # and the same with ubuntu:26.04
   ```

Version scheme: `<upstream>+ppa<rev>~<series>1` (e.g. `1.0.0+ppa1~noble1`), so series
upgrade paths sort correctly and PPA revisions never collide with upstream versions.

Releases are built **only in CI from tags** — never on maintainer machines (supply-chain
rule, `docs/security-design.md`). Release notes are generated from `CHANGELOG.md`.

## Distro portability

Install paths (libexecdir, polkit policy dir) are Meson options. Non-Debian packaging is
community-owned; `docs/packaging.md` (M5) documents everything a packager needs (paths,
AppStream metainfo, uninstall behavior — the .deb handles policy/helper removal on purge).
