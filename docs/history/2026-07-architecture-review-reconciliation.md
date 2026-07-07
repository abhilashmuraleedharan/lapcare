# LapCare — Reconciliation of Architecture Review vs. Engineering Plan

**Inputs:** `lapcare-engineering-plan.md` (v1.0), `lapcare-architcture-review.md` (Principal Engineer).
**Author:** Lead Architect. **Date:** 2026-07-06.
**Output:** this disposition record + Engineering Plan revised to v1.1.

Method: every review finding was evaluated independently. Acceptance was not the goal;
consistency with the plan's guiding principles was. Where the review conflicts with itself
(it does, in one place) or asks for speculative structure, I rejected it and say why.

**Tally:** 18 accepted (8 of them with modification), 2 rejected, 1 partially rejected.
Both High-severity findings accepted. All six "must fix before implementation" items resolved.

---

## Disposition table

| # | Review finding | Severity | Disposition | Resolution (plan section changed) |
|---|---|---|---|---|
| 1 | MVP bundles too much before 1.0 | High | **Accept (modified)** | The milestone gates already stage the risk; what was missing is *public labeling*. Named release channels added: public **alpha** after M2 (read-only, zero privileges), **beta** after M3 (firmware), 1.0 after M5. MVP content unchanged — firmware and storage health remain separate release gates as they already were (§17, §19). Rejected the implied option of cutting MVP features: a "Vantage alternative" without firmware updates isn't credibly the product. |
| 2 | pkexec helper: device-path validation harder than it looks; needs threat model | High | **Accept, strengthened** | The review is right and my regex was the tell. Better than fixing the regex: the helper no longer accepts device *paths* at all — it accepts a device *name* (e.g. `nvme0n1`) and resolves it against its **own enumeration of `/sys/block`**, rejecting anything not in that set. Enumerate-and-match beats validate-untrusted-input. ADR-0006 (helper threat model: discovery rules, allowlists, env scrubbing, timeouts, negative tests) is now a **blocking entry gate for M4** (§6, §14, §19). |
| 3 | Health score risks being misleading; calibration unaddressed | Medium | **Accept** | Aggregate score ships labeled **experimental** and each contributing signal displays its own status + data-confidence (e.g. "cycle count unavailable on this model — excluded"). The aggregate number is de-emphasized until fixture coverage justifies it (§6, M4). |
| 4 | Import-rule inconsistency: UI importing `providers/base.py` still imports the provider layer | Medium | **Accept** | Correct catch — this was a genuine contradiction in v1.0. Provider protocols move to **`core/ports.py`** (ports-and-adapters). `Protocol` definitions are typing-only, so core stays pure. UI now imports **core only** (+ GTK); providers implement core ports; the composition root wires them (§3, §6, §8, §9). |
| 5 | "Pure core" contradicted by SQLite history and file export | Medium | **Accept** | Also a genuine contradiction. Core computes; it defines `HistoryStore` and `ReportWriter` ports; SQLite and filesystem implementations live in `platform/`. Report *rendering* to a string stays in core (pure); *writing* does not (§6, §9). |
| 6 | Add a capability model (`supports_battery_thresholds`, …) now for future vendors | Medium | **Reject (deferred with explicit trigger)** | See rationale R1 below. The existing `availability()` contract *is* the capability model at the granularity the MVP needs; a vendor-capability framework with one vendor and zero write features is speculative structure. Deferred to an ADR triggered by the first write feature (M6) or second vendor (M10), whichever comes first — now stated in §6 and §21. |
| 7 | sysfs/ACPI variance: require stability notes; nullable fields | Medium | **Accept** | Already partially in plan; hardened into rules: every provider doc must include kernel/interface stability notes and known model quirks; **every model field is `Optional` unless a fixture corpus proves it universal** (§6, §10, docs/modules template). |
| 8 | State "GNOME-first, distro-portable where practical"; don't abstract toolkit | Low | **Accept** | One sentence added to §5. The "don't abstract the UI toolkit" advice was already plan policy. |
| 9 | High tooling floor; prove the stack in M0; keep `./run` and `./check` | Medium | **Accept** | M0 acceptance criteria now include a **stack-validation spike on both supported LTS releases** and `./run` + `./check` wrapper scripts so contributors/agents need exactly two commands (§19 M0). |
| 10 | asyncio + GLib integration is a hidden compatibility assumption | Medium | **Accept, made concrete** | The review flagged this generically; the concrete fact confirms it: PyGObject's native asyncio integration (`gi.events`) landed in **3.50**, but Ubuntu 24.04 LTS ships **3.48**. Resolution: M0 spike validates per-LTS; the sanctioned fallback is **one shared thread-pool executor behind the platform layer** marshaling results via `GLib.idle_add`. "No raw threads" is re-worded to "no ad-hoc threads" — the executor is the single exception, owned by `platform/` (§3, §4, §19, §22 new risk row). |
| 11 | Fixture collection/sanitization cost underestimated | Medium | **Accept** | Fixture **schema, redaction rules, and review checklist** must exist before any community capture is accepted — scheduled inside M1, where the corpus starts (§15, §19 M1). |
| 12 | Redact identifiers at capture time, `--include-identifiers` opt-in | Medium | **Accept verbatim** | Exactly right and cheap. `--capture-fixtures` redacts serials/UUIDs/MACs by default; `--include-identifiers` exists for local-only debugging and its output is never accepted upstream (§13, §15). |
| 13 | Packaging underspecified beyond PPA (paths, AppStream, uninstall) | Medium | **Accept (modified)** | Install paths (libexecdir, polkit dir) become **Meson options** — standard practice, near-zero cost. AppStream metainfo was already in `data/`; uninstall behavior documented (deb handles policy/helper removal). **Rejected** the implied commitment to maintain Fedora/Arch packaging: `docs/packaging.md` declares non-Debian packaging community-owned (§9, §17). |
| 14 | M0 doc scaffold risks speculative documentation | Low/Med | **Accept (modified)** | See rationale R2. M0 docs are split: **contracts** (AGENTS.md, ARCHITECTURE.md, STYLEGUIDE core rules, ADRs for decisions actually made) are written at M0 — they describe decisions, not implementations, so they cannot be speculative. **Recipes** (`docs/guides/*`) are written only after the first real instance exists, extracted from real code at end of M1. Status docs stay lightweight checklists (§ Agent-First, §19). |
| 15 | CI < 5 min across full matrix is optimistic | Low/Med | **Accept** | Split lanes: **fast PR lane** (lint, mypy, import-linter, tests, smoke — one LTS, < 5 min) and **full lane** (both-LTS matrix + deb build) on main/nightly/release (§16). |
| 16 | Missing UX acceptance criteria (firmware flows, prompts, copy) | Medium | **Accept** | Each milestone now carries UX acceptance criteria; M3 gains the firmware-specific ones: reboot-required flow, failure recovery, declined-auth, AC/battery preconditions (surfaced from fwupd, which enforces them), and "what changed" post-update (§19). |
| 17 | Cold start < 1.5 s conflicts with provider probing | Medium | **Accept** | Target redefined as **window + first meaningful dashboard content**; providers are lazy-initialized per page; dashboard renders fast/cached signals first and progressively enriches (§7, §19 M5). |
| 18 | Missing open-source hygiene (SECURITY.md, CoC, templates, trademark guidance) | Medium | **Accept** | Gate: all hygiene files exist **before the first public announcement** (the M2 alpha), not before M0. SECURITY.md additionally required before M4 ships the helper (§17, §19). |
| 19 | Overengineering: strictness rules may slow early learning; expect revision | — | **Partial reject** | Rules stay from M0 — see rationale R3. Accepted the spirit: rules are revisable **via ADR**, never by silent divergence. |
| 20 | Consider moving to a polkit D-Bus service *earlier* | — | **Reject** | See rationale R4. Trigger unchanged: first *write* feature (M6). ADR-0006 must, however, show the pkexec→service migration path so nothing in M4 makes it harder. |
| 21 | Missing: settings/preferences module | — | **Accept** | Genuine omission in v1.0. **GSettings** (schema already shipped in `data/`) accessed via a thin `platform/settings.py`; covers units, privacy defaults, report options. No custom config files (§9). |

"Missing modules" list items not shown above map to already-accepted rows: persistence boundary → #5,
capability model → #6, fixture redaction → #12, AppStream/uninstall → #13, a11y criteria → #16/M5
(concrete criteria: full keyboard navigation, screen-reader labels on all rows, no
information-by-color-alone), firmware recovery UX → #16, security policy → #18.

---

## Rationale for rejections and major modifications

### R1 — Capability model: rejected as premature (finding #6)

The review asks for `supports_battery_thresholds`, `supports_firmware_updates`,
`supports_ec_data` flags *now*. But:

1. **The review contradicts itself.** Its own overengineering section warns against building
   speculative structure before implementation teaches what is true. A capability negotiation
   layer designed with **one vendor, zero write features, and zero fixtures** is exactly that:
   we would be inventing capability names before knowing which capabilities vary in practice.
2. **The mechanism already exists at the right granularity.** `availability()` per provider
   (`OK / TOOL_MISSING / UNSUPPORTED_HARDWARE / PERMISSION_DENIED`) is capability reporting for
   everything the MVP does. A read-only app doesn't negotiate capabilities; it reports what it
   could read.
3. **The cost of deferring is low by design.** Capabilities become load-bearing only when
   (a) write operations exist or (b) a second vendor arrives. Both are post-1.0 milestones, and
   provider isolation means retrofitting a capability enum touches ports + registry, not
   call sites.

What I did accept: the plan now *names* `availability()` as the seed of the capability model
and pre-commits to the ADR at the M6-or-M10 trigger, so the decision is scheduled rather than
forgotten. This is the same reasoning the plan applies to the D-Bus service: define the trigger,
don't build the thing.

### R2 — M0 documentation: split contracts from recipes (finding #14)

The review's concern is real but overbroad. The fix is to distinguish two kinds of docs:

- **Contracts** (AGENTS.md, ARCHITECTURE.md, STYLEGUIDE rules, ADRs) document *decisions*.
  Every decision they record is being made in M0 regardless — writing it down is nearly free
  and is precisely what makes agent-driven M1 work. Cutting these would defeat a stated,
  first-class project goal (agent-first development), which a review comment doesn't outrank.
- **Recipes** (`docs/guides/adding-a-provider.md` etc.) document *implementations*. Written
  before any provider exists, they would be fiction. Accepted: they are now extracted from the
  first real provider/page at the end of M1.

This keeps the agent-first promise while conceding the review's actual point: don't document
what doesn't exist yet.

### R3 — Strictness rails stay from M0 (finding #19)

Import-linter, strict mypy in core/providers, and Blueprint-only UI are kept from day one, for
one reason the review under-weights: **this project's primary contributors will be AI agents,
and agents drift without mechanical guardrails.** A human team can hold "we know the layering
rule" in their heads for a milestone; agents re-derive the world every session. The rails are
the cheap substitute for institutional memory, and retrofitting strict mypy onto a codebase
later is far more expensive than starting with it. Accepted concession: any rule can be
loosened by ADR — visibly, not by accumulating `# noqa`.

### R4 — No early D-Bus system service (finding #20)

A resident root service is the single largest security liability the project could add, and the
MVP's privileged surface is **three read-only verbs**. pkexec's cost (a spawn per call, auth
caching via `auth_admin_keep`) is trivial at that scale. The service becomes the right design
when *writes* arrive (M6) — that trigger was already in the plan and survives review. The
accepted improvement is that ADR-0006 must document the migration path now, so M4 code treats
the helper's verb schema as a future D-Bus method schema and nothing gets harder later.

### On the review's closing "weakness" — layering vs. hardware variance

The review says the plan is "too confident that disciplined layering will control hardware
variance." Half-agree, worth answering precisely: layering was never the variance control.
Layering controls *blast radius* (a quirk stays inside one provider). Variance is controlled by
the **fixture corpus + nullable-by-default fields + availability contract** — and the accepted
findings #7, #11, #12 all strengthen exactly that mechanism. The plan v1.1 states this
distinction explicitly so future contributors don't over-trust the layers either.

---

## "Must fix before implementation" — resolution map

| Review must-fix | Resolved by | Status |
|---|---|---|
| 1. Core/provider interface boundary | `core/ports.py`, revised import table | Fixed in plan v1.1 |
| 2. Persistence outside pure core | `HistoryStore`/`ReportWriter` ports, `platform/` impls | Fixed in plan v1.1 |
| 3. Helper threat model & validation spec | ADR-0006, enumerate-don't-validate, M4 entry gate | Scheduled + gating |
| 4. Validate GTK/PyGObject/async/Meson on target LTS | M0 stack-validation spike, executor fallback defined | Gating M0 acceptance |
| 5. Fixture redaction rules before real captures | Capture-time redaction, schema + checklist in M1 | Gating M1 acceptance |
| 6. MVP scope reduce **or re-label** | Re-labeled: alpha after M2, beta after M3, 1.0 after M5 | Fixed in plan v1.1 |

## Plan changes applied (v1.0 → v1.1)

§3 ports + concurrency fallback · §4 stack table (PyGObject constraint, GSettings) · §5 GNOME-first
sentence · §6 ports, persistence boundary, experimental health score, helper enumeration ·
§8 import table rewrite · §9 layout (ports.py, history.py, settings.py, SECURITY.md, scripts,
docs/packaging.md) · §13/§15 capture-time redaction + fixture governance · §14 ADR-0006 gate ·
§16 CI lanes · §17 release channel labels + hygiene gate · §19 milestone acceptance criteria
(M0 spike, M1 fixture policy + guides authoring, M3 firmware UX, M4 security gate, M5 a11y +
cold-start definition) · §22 new risk row (PyGObject version skew) · Agent-First section
(contracts vs. recipes).
