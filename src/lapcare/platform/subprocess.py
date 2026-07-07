# SPDX-License-Identifier: GPL-3.0-or-later
"""The single audited subprocess runner (constitution invariant; STYLEGUIDE).

Every external command in this process goes through run_tool(): argv lists
only, binaries resolved against the fixed whitelist below, scrubbed
environment, mandatory timeout, bounded output. No shell, ever.

Raises the small platform-level exceptions below; PROVIDERS translate them
into the core.errors hierarchy at the provider boundary (a runner doesn't
know which provider is calling it).
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Sequence
from typing import Protocol

log = logging.getLogger(__name__)

# tool name -> absolute candidate paths, first executable wins. Adding a tool
# here is a conscious, reviewable act — no PATH lookups.
ALLOWED_TOOLS: dict[str, tuple[str, ...]] = {
    "lspci": ("/usr/bin/lspci",),
    "lsusb": ("/usr/bin/lsusb",),
}

MAX_OUTPUT_BYTES = 8 * 1024 * 1024
_SCRUBBED_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C.UTF-8"}


class ToolNotFound(Exception):
    def __init__(self, tool: str) -> None:
        self.tool = tool
        super().__init__(f"tool not installed: {tool}")


class ToolTimeout(Exception):
    def __init__(self, tool: str, timeout: float) -> None:
        self.tool = tool
        super().__init__(f"{tool} exceeded {timeout}s timeout")


class ToolFailed(Exception):
    def __init__(self, tool: str, returncode: int, stderr_snippet: str) -> None:
        self.tool = tool
        self.returncode = returncode
        self.stderr_snippet = stderr_snippet
        super().__init__(f"{tool} exited {returncode}")


class ToolRunner(Protocol):
    """What providers accept for injection (fixture tests pass a fake)."""

    async def __call__(self, tool: str, args: Sequence[str], *, timeout: float = 10.0) -> str: ...


async def run_tool(tool: str, args: Sequence[str], *, timeout: float = 10.0) -> str:
    """Run a whitelisted tool; return stdout text. See module doc for errors.

    A tool name absent from ALLOWED_TOOLS is a programming error (KeyError),
    not a runtime condition.
    """
    candidates = ALLOWED_TOOLS[tool]
    path = next((c for c in candidates if os.access(c, os.X_OK)), None)
    if path is None:
        raise ToolNotFound(tool)

    proc = await asyncio.create_subprocess_exec(
        path,
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_SCRUBBED_ENV,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise ToolTimeout(tool, timeout) from None

    if proc.returncode != 0:
        snippet = err.decode(errors="replace")[:500]
        log.debug("%s stderr: %s", tool, snippet)
        raise ToolFailed(tool, proc.returncode or -1, snippet)
    if len(out) > MAX_OUTPUT_BYTES:
        raise ToolFailed(tool, 0, f"output exceeded {MAX_OUTPUT_BYTES} bytes")
    return out.decode(errors="replace")
