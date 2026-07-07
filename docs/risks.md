# Risk Register

Living document; reviewed at every milestone close. Source: Engineering Plan v1.1 §22 plus
review reconciliation. Likelihood/impact: Low / Medium / High.

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Hardware variance: sysfs/ACPI fields differ or lie across ThinkPad generations | High | Medium | Fixture corpus from real machines; `availability()` contract; every model field Optional by default; community fixture-capture command; bug→fixture pipeline |
| 2 | Trademark exposure ("Lenovo", "ThinkPad", "Vantage") | Medium | High | Neutral name (ADR-0001); descriptive use only; no Lenovo logos/assets; disclaimer in README |
| 3 | Privileged-helper vulnerability | Low | Critical | Tiny fixed-verb helper; enumerate-and-match device targeting; injection test suite; per-verb polkit actions; ADR-0006 gate + security review before M4 ships |
| 4 | Upstream drift (fwupd API, sysfs paths, tool JSON schemas) | Medium | Medium | All source knowledge isolated in one provider each; CI full lane on newest LTS catches drift; version-gated paths documented in module docs |
| 5 | Scope creep toward reimplementing tools | Medium | High | Constitution principle #1 enforced in review; new data sources require an ADR naming the wrapped tool |
| 6 | Solo-maintainer bus factor / burnout | Medium | High | Agent-first design doubles as human onboarding; small milestones; strict scope discipline |
| 7 | GNOME/libadwaita API churn | Low | Low | Stable libadwaita from current LTS; stock widgets only; CI matrix catches breakage |
| 8 | Flatpak-first user expectations | Medium | Low | ADR-0005 reasoning public in README/FAQ; Flatpak on roadmap (M11) |
| 9 | Health score perceived as arbitrary or alarmist | Medium | Medium | Fully explainable rubric; per-signal confidence markers; aggregate labeled experimental until fixture coverage justifies it |
| 10 | Ubuntu-only tunnel vision limits adoption | Low | Medium | Nothing Ubuntu-specific in code; install paths as Meson options; `docs/packaging.md` (M5); non-Debian packaging community-owned |
| 11 | PyGObject/GLib version skew breaks asyncio integration (`gi.events` needs ≥ 3.50; Ubuntu 24.04 ships 3.48) | High | Medium | M0 stack-validation spike per LTS (Commit 9); platform-owned executor fallback; mechanism per LTS recorded in ADR-0007 |
| 12 | Fixture corpus leaks identifying data or rots without process | Medium | Medium | Capture-time redaction by default; fixture schema + review checklist gate community captures (M1) |
