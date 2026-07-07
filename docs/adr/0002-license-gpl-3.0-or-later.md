# ADR-0002: License is GPL-3.0-or-later

- **Status:** Accepted
- **Date:** 2026-07-06
- **Deciders:** Project owner, Lead Architect

## Context

Lapcare is an **end-user desktop application**, not a library: nobody links against it, so
the classic advantage of permissive licenses (proprietary embedding) is worth little here,
and the classic cost of copyleft (deterring adoption as a dependency) doesn't apply. The
project's most expensive asset over time will be its accumulated hardware-quirk knowledge and
fixture corpus. The realistic fork scenario is a hardware vendor or integrator shipping a
rebranded, customized build. The surrounding ecosystem (GNOME Firmware, Mission Center, TLP,
thinkfan) is overwhelmingly GPL-family, and license compatibility is one-directional: a GPL
project can absorb LGPL and GPL code; an MIT project can absorb neither without relicensing.

## Decision

We will license Lapcare under **GPL-3.0-or-later**. The `LICENSE` file carries the GPLv3
text; the "or-later" election is expressed via `SPDX-License-Identifier: GPL-3.0-or-later`
headers in source files and in packaging metadata. Contributions are accepted under the
inbound=outbound norm with DCO-style sign-off (see `CONTRIBUTING.md`); no CLA.

## Consequences

- Vendor/integrator forks must publish their improvements — the quirk corpus keeps growing in
  one place. GPL-3's anti-tivoization terms also apply, relevant for a hardware companion app.
- We can borrow code from the GPL/LGPL ecosystem we imitate (GNOME Firmware is GPL-2+,
  Mission Center GPL-3).
- Patent protection is explicit (GPLv3 §11), matching Apache-2.0 and strictly better than MIT.
- Commercial *use* remains unrestricted (deployment, support, resale); only proprietary
  derivatives are excluded — intended.
- If the provider layer ever warrants extraction as a reusable library, that component can be
  released under LGPL at that time (new code / copyright-holder decision); revisit by ADR.

## Alternatives Considered

- **Apache-2.0:** strong patent grant, but permits proprietary capture of the project's core
  asset; its embedding-friendliness solves a problem an end-user app doesn't have; and it
  walls us off from borrowing GPL ecosystem code.
- **MIT:** simplest, but silent on patents (weakest of the three in hardware-adjacent
  territory) and shares Apache's proprietary-capture and one-way-compatibility problems.
