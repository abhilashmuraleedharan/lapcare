# M5 — MVP Hardening & Release (v1.0.0): Status

**State:** IN PROGRESS. **Branch:** `feature/m5` (single engineering PR, rebase-merged;
the v1.0.0 tag itself is gated separately — see Release gates below).
**Objective (ROADMAP):** polish, perf, PPA pipeline, user docs, community hardware-test
round across ≥ 5 ThinkPad models; health-score calibration review.

**This milestone splits in two by who can execute it:**

1. **Engineering work (this PR):** performance to the < 1.5 s bar, the accessibility
   criteria, hardening/crash audit, user documentation, packaging documentation, the PPA
   pipeline (everything up to the Launchpad upload itself), and the health-score
   calibration review document.
2. **Release gates (maintainer + community; CANNOT be executed by an agent):** Launchpad
   PPA creation/GPG signing/upload and the install-from-PPA verification on both LTS; the
   community hardware round (≥ 5 ThinkPad models); the two carried interactive polkit
   verifications (M3 firmware install, M4 SMART prompt) on the E16. **v1.0.0 is tagged
   only when these pass** — tagging earlier would fake the milestone's own bar.

## Commit plan (engineering PR)

- [ ] C1 `docs: open milestone M5` — this file.
- [x] C2 `perf: measure and hit the launch bar` — `lapcare.mark_launch()` anchors t0 at
      first package import; "window presented" and "dashboard ready" log elapsed.
      **Measured on the E16 Gen 2's own CPU** (validation containers, xvfb, real host
      sysfs): window at 0.24-0.55 s, first dashboard content at **0.29 s warm / 0.74 s
      cold** on 24.04 and 0.29-0.38 s on 26.04 — the 1.5 s bar is met with ~2× headroom,
      so no optimization was warranted. Smoke test now carries a loose (5 s) regression
      guard to catch order-of-magnitude startup regressions in CI; the real bar stays a
      hardware judgment.
- [x] C3 `a11y: keyboard navigation + screen-reader labels + no color-only info` —
      audit of all six pages found exactly two gaps, both fixed: WearChart was silent to
      screen readers (now role IMG with a data-summarizing label) and drew its day labels
      with fixed-pixel cairo toy text (now Pango from the widget's font context, label
      space from real font metrics — respects system font scaling); the app had no
      keyboard shortcuts (Ctrl+Q quit, Ctrl+W close added). Everything else already
      passed: stock Adwaita rows/buttons with text labels everywhere, and every colored
      status pairs its color with words. Audit recorded as a per-release checklist in
      docs/testing.md.
- [x] C4 `hardening: crash audit` — sweep results: every `scheduler.submit` has a real
      error handler; all re-entrancy guarded by busy flags; no division/None hazards in
      parsers or the chart. **One real field bug found and fixed:**
      `AdwPreferencesRow:use-markup` defaults to TRUE, so any hardware-derived string
      (disk model, USB product name, fwupd device name) containing `&`/`<` was parsed as
      Pango markup and the row text silently BLANKED (measured — only a Gtk-WARNING the
      smoke test didn't fail on). Every row carrying hardware/tool strings now sets
      `use_markup=False` (17 code sites + 16 template rows); smoke now fails on the
      "Failed to set text" warning; the SMART parser gained a hostile-JSON-types fuzz
      test (the helper guarantees valid JSON, never a valid schema).
- [x] C5 `docs: user guide + packaging guide` — `docs/user-guide.md` (install, every
      page, what the two auth prompts mean and that declining is always safe, privacy,
      troubleshooting table); `docs/packaging.md` (paths, deps, the libexecdir/polkit
      exec.path lockstep warning, helper packaging rules, AppStream). Both linked from
      README.
- [x] C6 `feat(release): PPA pipeline` — `tools/ppa-source.sh` builds unsigned
      per-series source packages in containers (noble + resolute); CI `ppa-lane` produces
      the same as a tag artifact; docs/release.md gains the full maintainer runbook
      (one-time Launchpad/GPG setup, sign, dput, and the containerized install-from-PPA
      verification for the acceptance criterion). **Verified Launchpad-faithfully**: both
      series' source packages were built to binaries in clean containers with ONLY the
      declared Build-Depends (`mk-build-deps`) — which caught and fixed two Build-Depends
      gaps CI's fuller environment had masked (`libglib2.0-bin` for
      glib-compile-schemas, `gir1.2-gtk-4.0`/`gir1.2-adw-1` for blueprint-compiler's
      typelib lookup): the first PPA upload would have failed to build without them.
- [x] C7 `docs: health-score calibration review` — `docs/health-score-calibration.md`:
      every threshold with its provenance, the accepted 1.0 limitations, the field-data
      wishlist the beta should collect, and the revision procedure (constants + this
      table + boundary tests move together; score-structure changes need an ADR).
- [ ] C8 `docs: close engineering; hand off release gates` — status updated, ROADMAP
      note, maintainer runbook finalized.

## Acceptance criteria (from ROADMAP) and who owns each

- [ ] MVP definition fully met — engineering side done in M0–M4; final judgment at tag
- [ ] Zero known crashers — C4 sweep (agent) + beta field reports (maintainer triage)
- [ ] Install-from-PPA works on both LTS — **maintainer** (runbook in C6)
- [ ] Accessibility: full keyboard navigation; screen-reader labels on all rows; no
      information by color alone; respects font scaling — C3 (agent)
- [ ] Performance: < 1.5 s launch → window + first meaningful dashboard content on a
      mid-range ThinkPad — C2 (agent measures on the E16-class environment; maintainer
      confirms on the real E16)
- [ ] Community hardware round ≥ 5 ThinkPad models — **maintainer/community**
- [ ] Health-score calibration review — C7 document (agent); revision itself needs field
      data (post-beta)

## Release gates (maintainer runbook — v1.0.0 tag blocked on these)

1. Launchpad PPA created; GPG key registered; `ppa-lane` source package uploaded; install
   verified on clean 24.04 and 26.04 (C6 runbook).
2. Community hardware round: ≥ 5 ThinkPad models through the manual matrix.
3. Carried interactive verifications on the E16: one real firmware install (M3), one
   "Read Health" polkit prompt (M4).
4. Then: version bump to 1.0.0, CHANGELOG, tag, release — the standard close.

## Retrospective

(at close)
