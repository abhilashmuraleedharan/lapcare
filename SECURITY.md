# Security Policy

## Supported Versions

Lapcare is in pre-alpha development. There are no supported releases yet. Once releases
begin: the latest release is supported pre-1.0; post-1.0, the latest minor release plus
security fixes for the previous one.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Report privately via **GitHub private vulnerability reporting**:
[Security → Report a vulnerability](https://github.com/abhilashmuraleedharan/lapcare/security/advisories/new)
on this repository. If that is unavailable to you, email **amuraleedharan13@gmail.com** with
`[lapcare security]` in the subject line.

You can expect an acknowledgement within **7 days** and a status assessment within **30
days**. Please include reproduction steps, affected version/commit, and your assessment of
impact. Coordinated disclosure is appreciated; you will be credited in the advisory unless
you prefer otherwise.

## Scope Notes

Security reports of particular interest:

- **Privilege escalation** through Lapcare's polkit-mediated privileged helper (ships in
  milestone M4) — argument handling, device targeting, environment, or polkit policy issues.
- **Command injection** into any wrapped system tool.
- **Privacy leaks**: personally identifying data (serial numbers, UUIDs, MAC addresses)
  appearing in logs, exports, or fixture captures despite redaction defaults.

Out of scope: vulnerabilities in the wrapped tools themselves (`fwupd`, `smartctl`, etc.) —
report those upstream; we will gladly help route them.

The project's security *design* (threat model, subprocess hygiene, helper hardening rules)
is documented in `docs/security-design.md`.
