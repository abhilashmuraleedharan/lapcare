# ADR-0006: Privileged helper — threat model and validation spec

- **Status:** Accepted
- **Date:** 2026-07-09
- **Deciders:** Project owner, Lead Architect
- **Gate:** blocking entry gate for milestone M4 (per ADR-0004); no helper code exists
  before this ADR.

## Context

ADR-0004 fixed the shape of Tier 2: a short-lived, fixed-verb helper at
`/usr/libexec/lapcare/lapcare-helper`, invoked via `pkexec`, one polkit action per verb,
enumerate-and-match device targeting, no daemon, no state. It deliberately left the threat
model, validation rules, and verb schema to this ADR. M4's Storage page needs SMART/NVMe
health, which requires opening block devices — root on Ubuntu.

Facts verified against upstream sources at milestone open (M3 retrospective rule), from
polkit `src/programs/pkexec.c` as shipped on both target LTS releases (pkexec 124 on 24.04,
127 on 26.04 — both post-CVE-2021-4034):

- **Action selection supports per-verb actions on one executable.**
  `find_action_for_path()` matches an action when its
  `org.freedesktop.policykit.exec.path` annotation equals the program path **and**, if the
  action also carries `org.freedesktop.policykit.exec.argv1`, that annotation equals the
  program's first argument. So "one polkit action per verb" is implementable with a single
  helper binary: the verb is argv[1] and each action pins `path` + `argv1`.
- **The path is canonicalized before matching** (`realpath()`), so the annotation must hold
  the canonical installed path, and symlink aliasing cannot select a different action.
- **If no action matches** (unknown verb), pkexec falls back to the generic
  `org.freedesktop.policykit.exec` action — a scarier admin prompt, not a bypass. The helper
  must still reject unknown verbs itself.
- **pkexec `clearenv()`s the environment**, re-adding only a validated whitelist (locale,
  `TERM`, `SHELL`, optionally `DISPLAY`/`XAUTHORITY`), and sets a fixed root-safe `PATH`.
  `PYTHONPATH`, `LD_PRELOAD`, `DBUS_*` etc. can never reach the helper — but the helper does
  not *rely* on this (defense in depth below).
- `smartctl --json` (smartmontools ≥ 7.0; 7.4/7.5 on our LTS targets) reports SATA **and**
  NVMe health in one JSON schema. Its exit status is a bitmask: bit 0 (usage error) and
  bit 1 (device open failed) mean there is no report; bits 3–7 (disk failing, attributes
  below threshold, error-log entries…) are *findings* delivered alongside valid JSON — a
  failing disk exits non-zero with perfectly good data. **Bit 2 ("a SMART command
  failed") also coexists with complete, healthy JSON** — measured on the E16 Gen 2's SK
  hynix NVMe, which lacks the optional self-test log, so every `--all` read sets bit 2
  while the full health section is present. Bit 2 is therefore *data quality*, not
  failure; the JSON gate below decides.
- `pkexec` and `polkitd` are discrete packages on both LTS releases; `smartmontools` is in
  main on both.

## Threat model

**Adversary:** any local unprivileged process. `pkexec` is world-executable, so the helper
must assume every invocation is hostile: attacker-chosen argv, environment, working
directory, umask, file descriptors, and signals. Polkit authentication gates *whether* the
helper runs as root, not *what arguments* it receives — an attacker who convinces the user
to authenticate once (or rides an `auth_admin_keep` grant within its ~5-minute window from
the same session) gets to call the helper with arbitrary arguments.

**Assets, in order:** (1) root code execution — the only catastrophic outcome; (2) root
file *read* disclosure (tricking the helper into opening an attacker-chosen path); (3)
denial of service (hung root processes); (4) the SMART data itself — low sensitivity
(device serials appear in `smartctl` JSON; see privacy note below).

**Non-threats:** the lapcare GUI process is *not* trusted by the helper (it is just another
unprivileged caller), but it is also not an adversary we defend the *user* against — a
compromised GUI can already phish the polkit prompt. Vulnerabilities in `smartctl` itself
are out of scope (SECURITY.md), but the helper still bounds what `smartctl` can be asked to
touch.

## Decision

We will ship the helper to the following spec. Every rule here is testable, and the
negative/injection suite (part of the helper's definition of done, `docs/security-design.md`)
asserts each one.

### Program

1. **One file, Python 3 stdlib only, zero imports from `lapcare`** (it must be auditable in
   isolation and runnable before/without the app's site-packages). Installed to
   `/usr/libexec/lapcare/lapcare-helper`, root-owned, mode 0755, shebang
   `#!/usr/bin/python3` (the distro interpreter, absolute).
2. **No daemon, no socket, no config file, no state, no network, no logging framework.**
   One request per process; output on stdout; a single terse line on stderr for errors.

### Verbs

3. Verb = `argv[1]`. **M4 ships exactly one verb: `smart-report`** (polkit action
   `io.github.abhilashmuraleedharan.lapcare.smart-report`). ADR-0004 named `.nvme-report`
   and `.dmi-full` as the expected Tier-2 set; those verbs ship **only when a feature
   consumes them** — `smartctl --json` covers NVMe health natively, so `nvme-report` has no
   M4 consumer, and no M4 feature reads root-only DMI fields. A root-executing verb with no
   consumer is pure attack surface. (This narrows ADR-0004's list; it does not widen
   anything, and the one-action-per-verb rule is unchanged.)
4. **Verb schema doubles as the future D-Bus method schema** (ADR-0004 consequence):
   `smart-report(device: str) -> JSON string`. New verbs get new polkit actions; existing
   verbs never gain parameters.

### Input validation (the core of the spec)

5. **Exact argc.** `smart-report` takes exactly one argument: `argc == 3`. Anything else —
   including zero arguments, extra arguments, `--` — is rejected before any other work.
6. **Enumerate-and-match, never parse.** The device argument is a bare kernel block-device
   name (e.g. `nvme0n1`, `sda`). The helper builds its own allow-set from
   `os.listdir("/sys/block")` and rejects any argument not **exactly** in that set. There
   is no path handling, no prefix stripping, no normalization, no regex — `/dev/sda`,
   `../sda`, `sda/..`, names with `/`, NUL, newline, or empty strings all fail the set
   membership test by construction. The device node handed to `smartctl` is
   `/dev/<name>` assembled *by the helper* from the matched name.
7. **Post-match sanity:** the assembled `/dev/<name>` must exist and be a block device
   (`stat.S_ISBLK`); otherwise reject. (Guards against a `/sys/block` entry with no
   matching node, e.g. inside containers.)

### Execution hygiene

8. **Absolute tool path, no discovery:** `/usr/sbin/smartctl` only. Missing → exit with the
   distinct `tool-missing` error (the app degrades, ADR-0004).
9. **Scrubbed child environment**, even though pkexec already cleared ours:
   `{"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C.UTF-8"}` and nothing else.
   `shell=False`, argv list, stdin `/dev/null`, cwd `/`.
10. **Helper-enforced timeout:** 25 s wall clock on the child, then SIGKILL and a
    `tool-timeout` error. (The GUI-side pkexec timeout must be much longer — it contains
    the human typing a password; see Client contract.)
11. **Bounded output:** stdout capped at 4 MiB read; larger output is an error, not a
    truncation (truncated JSON is worse than no JSON).
12. **Exit-bitmask policy (measured above):** `smartctl` bits 0–1 → hard error
    (`tool-failed`); any other exit (bits 2–7 in any combination) → success provided the
    JSON gate passes — a failing disk is *data*, and a partially-answering drive (bit 2,
    e.g. no self-test log on the E16's own NVMe) is data with gaps that the provider maps
    to Optional fields. In all success paths the helper confirms stdout parses as JSON
    (`json.loads`) before emitting it verbatim; it never interprets the contents further
    (parsing SMART semantics is the provider's job, per the one-parser-per-tool rule).
13. **Error channel:** errors are one machine-readable line on stderr —
    `lapcare-helper: <code>: <short detail>` with `code` ∈ `usage | unknown-verb |
    unknown-device | tool-missing | tool-timeout | tool-failed | output-invalid` — and a
    non-zero exit. Stderr never echoes raw argv (only the matched device name or nothing);
    stdout is empty on error.

### Polkit policy

14. One `.policy` file, `data/io.github.abhilashmuraleedharan.lapcare.policy`, one
    `<action>` per verb: `allow_any=no`, `allow_inactive=no`,
    `allow_active=auth_admin_keep`; annotations `exec.path =
    /usr/libexec/lapcare/lapcare-helper` and `exec.argv1 = <verb>`. No `allow_gui`
    annotation (the helper is not an X client). Message text names Lapcare and the verb's
    purpose ("Read storage device health (SMART)").

### Client contract (unprivileged side)

15. The GUI invokes `/usr/bin/pkexec /usr/libexec/lapcare/lapcare-helper smart-report
    <name>` through the audited runner (`platform/subprocess.py`) — `pkexec` joins
    `ALLOWED_TOOLS`. Timeout **120 s** (it contains an interactive auth prompt). pkexec
    exit 126 (dialog dismissed) and 127 (not authorized) → `PrivilegedActionDenied` — quiet
    degradation, never an error page (ADR-0004). Helper-missing → `TOOL_MISSING`
    availability (dev builds run uninstalled; the Storage page's unprivileged device
    inventory still works).
16. **The GUI treats helper output as untrusted input** (security-design parsing rules):
    strict JSON parse, size-bounded, no dynamic evaluation — same as any tool output.

### Privacy

17. `smartctl` JSON contains the drive serial number. The provider redacts `serial_number`
    (and WWN) fields at the parse boundary into a dedicated identifier field that follows
    the existing redaction rules: never logged above DEBUG, excluded from exports by
    default (security-design.md).

### Definition of done for any change to the helper

18. The negative/injection suite must cover, at minimum: wrong argc (0/2/extra), unknown
    verb, path-shaped device arguments (`/dev/sda`, `../sda`, `sda/../nvme0n1`, absolute
    paths, embedded newline/space), device not in `/sys/block`, tool missing, tool timeout,
    non-JSON tool output, oversized output, and the bits-3–7 "failing disk is still data"
    path. The suite runs the helper **directly as a subprocess without pkexec** — every
    validation rule above fires before privilege is relevant, so the suite is meaningful
    unprivileged and runs in CI containers.

## Consequences

- New packaged artifacts: the helper (libexec) and the polkit `.policy` (datadir);
  `debian/control` gains `Depends: pkexec` and `Recommends: smartmontools` — sanctioned
  here (constitution: no new runtime deps without an ADR).
- The privileged surface of the entire application is one 200-line auditable file with one
  verb; SECURITY.md's escalation scope stays reviewable in one sitting.
- `auth_admin_keep` means one prompt covers a whole Storage-page refresh and a subsequent
  diagnostics run — and also means a hostile local process in the same session has a
  ~5-minute window to call the helper without a prompt. Accepted: the helper's verbs are
  read-only reports whose only sensitive content is device serials (redacted downstream);
  this trade is re-evaluated in the first *write*-verb ADR (M6, per ADR-0004/0008).
- Unknown-verb calls fall through to polkit's generic exec action prompt (upstream
  behavior) — ugly but safe; the helper rejects the verb after any authentication.
- Dev-mode (`./run`, uninstalled): no helper on disk → Storage health reports
  TOOL_MISSING; full flow is only testable from an installed .deb — noted in
  `docs/testing.md`'s manual matrix.
- Adding `nvme-report`/`dmi-full` later is cheap (new verb + new action + suite rows), and
  this ADR's spec already binds their shape.

## Alternatives Considered

- **Ship all three ADR-0004 verbs now:** rejected — two of them have no consumer in M4,
  and unconsumed root-executing verbs are free attack surface plus untestable-in-anger
  code. ADR-0004's *action model* is kept; its verb list becomes demand-driven.
- **`nvme-cli` alongside smartmontools:** rejected for M4 — `smartctl --json` reports NVMe
  health natively (verified on the E16 Gen 2's real NVMe during fixture capture); a second
  root-spawned tool doubles the execution surface for zero new data. Revisit only if a
  concrete field is missing.
- **C helper:** rejected — the risk class here is logic (validation, argv handling), not
  memory safety of a 200-line tool; Python stdlib is more auditable for this project's
  contributors and the .deb already depends on python3. No third-party imports allowed,
  ever.
- **Per-verb wrapper executables instead of argv1 annotations:** unnecessary — upstream
  pkexec's `exec.argv1` matching (verified in source) gives per-verb actions with one
  binary; three binaries would triple the installed setuid-adjacent surface.
- **A polkit-authenticated D-Bus service:** already rejected for the read-only MVP in
  ADR-0004 (R4); unchanged. The verb schema is kept D-Bus-shaped so that migration stays
  cheap.
- **Passing device paths (`/dev/…`) with validation:** rejected in ADR-0004 and again
  here — enumerate-and-match eliminates the entire path/symlink/normalization bug class
  instead of defending it.
