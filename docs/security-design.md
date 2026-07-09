# Security Design

How Lapcare is designed to be safe. This is the *design* document; the vulnerability
*reporting* policy is `SECURITY.md`, and the privilege model decision is ADR-0004. The
privileged helper's full threat model and validation spec is **ADR-0006** (accepted at
M4 open; the helper ships since v0.5.0 with one verb, `smart-report`).

## Threat Model (summary)

Lapcare handles no network input except fwupd metadata — and fwupd itself downloads and
verifies firmware against LVFS signatures; Lapcare never downloads firmware. The primary
risks, in order:

1. **Privilege escalation** through our pkexec helper (M4+).
2. **Command injection** into wrapped CLI tools.
3. **Privacy leaks** — identifying data (serials, UUIDs, MACs) escaping via exports, logs,
   or fixture captures.

## Rules

### Subprocess hygiene
- Exactly one audited subprocess runner (`platform/subprocess.py`); every external command
  goes through it. `shell=False` always; argv lists only; binaries resolved to absolute paths
  against a whitelist; environment scrubbed; timeout mandatory (default 10 s).

### Parsing hygiene
- All tool output — even from root-owned tools — is untrusted input: size limits, strict JSON
  parsing, no dynamic evaluation of anything.

### Privileged helper (shipped M4, per ADR-0004 / ADR-0006)
- Fixed verb whitelist (M4: `smart-report` only — verbs are demand-driven, ADR-0006 §3);
  one polkit action per verb via `exec.path` + `exec.argv1` annotations; no free-form
  arguments; exact argc.
- Device targeting by enumerate-and-match against the helper's own `/sys/block` listing —
  never user-supplied paths (ADR-0006 §6-7).
- Root-owned, mode 0755, installed to `/usr/libexec/lapcare/lapcare-helper`; stdlib-only
  Python, zero lapcare imports; short-lived; no daemon, no socket, no state, no env knobs;
  one machine-readable stderr line on error, never argv echo.
- Negative/injection test suite (`tests/helper/`) is part of its definition of done —
  the required case list is ADR-0006 §18, verbatim.

### Privacy
- Serial numbers, UUIDs, and MAC addresses never appear in logs above DEBUG.
- Report exports redact identifiers by default; including them is an explicit user action.
- Fixture captures (`--capture-fixtures`) redact at capture time by default;
  `--include-identifiers` is local-only and unredacted captures are never accepted upstream.
- History DB and settings live under XDG dirs with default permissions; nothing secret is
  stored.

### Supply chain
- Minimal runtime dependencies (constitution invariant #7: no new deps without an ADR).
- Dependabot enabled; release artifacts are built only in CI from tags — never on maintainer
  machines.
- Firmware installation is triggered via fwupd's D-Bus API, so fwupd's polkit policy and LVFS
  signature verification govern it; Lapcare adds no bypasses.
