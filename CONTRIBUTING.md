# Contributing to Lapcare

Contributions from humans and AI coding agents are equally welcome and follow the identical
workflow. AI agents: start with `AGENTS.md`. Everyone: the project's non-negotiables are in
`PROJECT_CONSTITUTION.md`, and conduct is governed by `CODE_OF_CONDUCT.md`.

## Workflow

1. Find or open an issue; for anything architectural, check `DECISIONS.md` first — accepted
   ADRs are changed by superseding ADRs, not by PRs that quietly diverge.
2. Branch from `main` (`feat/<topic>`, `fix/<topic>`, `docs/<topic>`). During a milestone's
   initial development a single `feature/<milestone>` branch may carry the whole milestone as
   one PR of small commits (M0 works this way).
3. Keep commits small and logically separated; one concern per commit.
4. Ensure `./check` passes locally (it mirrors the CI fast lane).
5. Open a PR against `main`; fill the template — it embeds the Definition of Done.
6. Milestone-scoped PRs are merged with **rebase-merge** (preserving the commit sequence);
   single-topic PRs are **squash-merged**. Merge commits are disabled either way.

## Commit conventions

Conventional-commit subjects: `feat:`, `fix:`, `docs:`, `test:`, `build:`, `ci:`, `chore:`,
`provider:` (provider-specific changes), `spike:` (investigations). Imperative mood, ≤ 72
chars. Body explains *why* when it isn't obvious.

**Sign-off:** we use the [Developer Certificate of Origin](https://developercertificate.org).
Add `Signed-off-by: Your Name <email>` (`git commit -s`). By signing off you certify you have
the right to contribute the code under GPL-3.0-or-later (inbound=outbound; no CLA).

## Definition of Done

A change is done when **all** of these hold — the PR template repeats this checklist:

- [ ] Code follows `STYLEGUIDE.md` and the import rules in `ARCHITECTURE.md`.
- [ ] Tests: new behavior is tested at the right layer (`docs/testing.md`); `./check` green.
- [ ] Docs updated **in the same PR**: module docs, guides, or ADRs affected by the change.
- [ ] The current milestone's `docs/status/` file is ticked/annotated if the change advances
      an acceptance criterion.
- [ ] User-visible strings are `_()`-wrapped.
- [ ] No new runtime dependencies (or an accepted ADR authorizes them).
- [ ] `CHANGELOG.md` `[Unreleased]` updated for user-visible changes.
- [ ] Commit messages follow conventions and carry DCO sign-off.

## Documentation rules (contracts vs. recipes)

- **Contracts** (constitution, architecture, styleguide, ADRs) record *decisions* — write or
  update them the moment the decision is made.
- **Recipes** (`docs/guides/*`) record *how to do things* — they are extracted from real,
  working implementations, never written speculatively. If you build the first instance of
  something, writing the recipe from it is part of your DoD.
- Documentation describes current truth; aspirational content lives only in `ROADMAP.md`.
  Stale docs are bugs — file them as such.

## Hardware fixtures

Provider tests run against captured real hardware data (`tests/fixtures/`). Contributing
captures from your machine is one of the most valuable contributions possible — see the
hardware-report issue template. **Only redacted captures are accepted** (the capture tool
redacts by default from M1 onward); never attach raw serials/UUIDs.

## Development setup

Ubuntu 24.04+ (or any distro with GTK4 ≥ 4.14, libadwaita ≥ 1.5, PyGObject, Meson,
blueprint-compiler). Then:

```
./run      # build + launch
./check    # everything CI's fast lane runs
```

(Both scripts land in M0 Commits 6–7; exact system packages are listed in `./check --help`
output and README once the build exists.)

## Security

Never report vulnerabilities in public issues — see `SECURITY.md` for the private channel.
