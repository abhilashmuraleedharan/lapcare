# ADR-0008: Capability model deferred; availability() is its seed

- **Status:** Accepted
- **Date:** 2026-07-06
- **Deciders:** Project owner, Lead Architect (reconciled with Principal Engineer review)

## Context

The Principal Engineer review recommended adding a per-capability negotiation model
(`supports_battery_thresholds`, `supports_firmware_updates`, `supports_ec_data`, …) early, to
prepare for non-ThinkPad vendors. But the MVP is read-only with a single target vendor: we
have no write features, no second vendor, and no fixture data telling us *which* capabilities
actually vary in practice. Inventing capability names now would be speculative structure —
the same failure mode the review itself warns against elsewhere.

## Decision

We will **not** build a capability model now. The existing per-provider contract —
`availability() -> OK / TOOL_MISSING / UNSUPPORTED_HARDWARE / PERMISSION_DENIED` — is the
capability mechanism at MVP granularity, and is deliberately designed as the seed of the
fuller model. A capability-model ADR **must** be written when the first of these triggers
fires: (a) the first hardware *write* feature (battery charge thresholds, M6), or (b) the
first second-vendor support work (M10).

## Consequences

- No speculative enum to design, document, and maintain against zero variance data.
- Provider isolation keeps the retrofit cheap: introducing capabilities later touches
  `core/ports.py` and the provider registry, not call sites.
- The trigger is recorded here and in `ROADMAP.md` (M6/M10), so the decision is scheduled,
  not forgotten.

## Alternatives Considered

- **Capability flags now (review recommendation):** rejected as premature abstraction;
  detailed reasoning in `docs/history/2026-07-architecture-review-reconciliation.md` (R1).
- **Vendor subclassing of providers:** rejected — quirk *data* (fixtures + nullable fields)
  has so far explained all known variance; class hierarchies would encode guesses.
