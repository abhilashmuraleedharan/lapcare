#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""lapcare-helper: Lapcare's polkit-mediated privileged helper.

Spec: ADR-0006 (docs/adr/0006-privileged-helper-threat-model.md); every rule
enforced here is asserted by tests/helper/. Source lives as
helper/lapcare_helper.py and installs as /usr/libexec/lapcare/lapcare-helper
(root:root 0755), invoked only via pkexec; one polkit action per verb.

Standalone by design: Python stdlib only, no lapcare imports, no config, no
environment knobs, no state, no logging. Every invocation is treated as
hostile — polkit gates WHO may run this as root, not WHAT arguments arrive.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from typing import NoReturn

SMARTCTL = "/usr/sbin/smartctl"
CHILD_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C.UTF-8"}
TOOL_TIMEOUT_S = 25
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
# smartctl's exit status is a bitmask: bit 0 (usage error) and bit 1 (device
# open failed) mean there is no report; every other bit coexists with valid
# JSON — bits 3-7 are health FINDINGS and bit 2 fires even on healthy drives
# that lack an optional log (measured on the E16 Gen 2's NVMe; ADR-0006 §12).
_FATAL_SMARTCTL_BITS = 0b00000011


def _fail(code: str, detail: str = "") -> NoReturn:
    # ADR-0006 §13: one machine-readable stderr line, empty stdout, non-zero
    # exit. Callers must never pass raw argv in `detail`.
    line = f"lapcare-helper: {code}"
    if detail:
        line += f": {detail}"
    print(line, file=sys.stderr)
    raise SystemExit(1)


def _device_node(name: str) -> str:
    """Enumerate-and-match (ADR-0006 §6-7): the argument is accepted only if
    it is exactly a current /sys/block entry; the /dev node is assembled from
    the MATCHED name, so no path in the argument is ever interpreted."""
    try:
        present = set(os.listdir("/sys/block"))
    except OSError as exc:
        _fail("unknown-device", f"cannot enumerate /sys/block: {exc.strerror}")
    if name not in present:
        _fail("unknown-device")
    node = "/dev/" + name
    try:
        st = os.stat(node)
    except OSError:
        _fail("unknown-device", f"no device node for {name}")
    if not stat.S_ISBLK(st.st_mode):
        _fail("unknown-device", f"{node} is not a block device")
    return node


def _smart_report(node: str) -> None:
    if not os.access(SMARTCTL, os.X_OK):
        _fail("tool-missing", SMARTCTL)
    try:
        proc = subprocess.run(
            [SMARTCTL, "--json", "--all", node],
            env=CHILD_ENV,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=TOOL_TIMEOUT_S,
            cwd="/",
            check=False,
        )
    except subprocess.TimeoutExpired:
        _fail("tool-timeout", f"smartctl exceeded {TOOL_TIMEOUT_S}s")
    # Negative returncode = killed by signal; otherwise apply the bitmask
    # policy (a non-zero exit with only bits 3-7 set still carries good JSON).
    if proc.returncode < 0 or proc.returncode & _FATAL_SMARTCTL_BITS:
        _fail("tool-failed", f"smartctl exited {proc.returncode}")
    if len(proc.stdout) > MAX_OUTPUT_BYTES:
        _fail("output-invalid", f"output exceeds {MAX_OUTPUT_BYTES} bytes")
    try:
        json.loads(proc.stdout)
    except ValueError:
        _fail("output-invalid", "smartctl output is not JSON")
    sys.stdout.buffer.write(proc.stdout)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        _fail("usage", "expected: lapcare-helper smart-report <device>")
    verb, device = argv[1], argv[2]
    if verb != "smart-report":
        _fail("unknown-verb")
    _smart_report(_device_node(device))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
