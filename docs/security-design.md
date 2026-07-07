# Security Design

How Lapcare is designed to be safe. This is the *design* document; the vulnerability
*reporting* policy is `SECURITY.md`, and the privilege model decision is ADR-0004. The
privileged helper's full threat model will be ADR-0006 (blocking gate for milestone M4).

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

### Privileged helper (M4+, per ADR-0004 / ADR-0006)
- Fixed verb whitelist; one polkit action per verb; no free-form arguments.
- Device targeting by enumerate-and-match against the helper's own `/sys/block` listing —
  never user-supplied paths.
- Root-owned, mode 0755, installed to `/usr/libexec/lapcare/`; short-lived; no daemon, no
  socket, no state; stderr only, never logs command output at privileged level beyond exit
  status.
- Negative/injection test suite is part of its definition of done.

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
