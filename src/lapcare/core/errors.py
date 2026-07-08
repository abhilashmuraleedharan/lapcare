# SPDX-License-Identifier: GPL-3.0-or-later
"""The Lapcare exception hierarchy (ARCHITECTURE.md, plan §12).

Providers translate EVERY underlying failure (OSError, subprocess errors,
parse errors) into one of these at the provider boundary; nothing above a
provider sees a CalledProcessError. User-facing message text is built in the
UI layer from the structured fields here — core carries data, not prose.
"""

from __future__ import annotations

from lapcare.core.models import Availability


class LapcareError(Exception):
    """Base for all Lapcare domain errors."""


class ProviderUnavailable(LapcareError):
    """The provider cannot answer at all (missing tool, wrong hardware, EPERM).

    Absence of hardware is NOT this — that's data (None/empty list).
    """

    def __init__(self, source: str, reason: Availability, tool: str | None = None) -> None:
        self.source = source  # provider name, e.g. "dmi"
        self.reason = reason  # never Availability.OK
        self.tool = tool  # missing tool/package name when reason is TOOL_MISSING
        super().__init__(f"{source}: {reason.value}" + (f" ({tool})" if tool else ""))


class ProviderTimeout(LapcareError):
    def __init__(self, source: str, detail: str) -> None:
        self.source = source
        self.detail = detail
        super().__init__(f"{source}: timeout: {detail}")


class ProviderParseError(LapcareError):
    """A tool/file produced output we could not interpret. Raw payload is
    logged at DEBUG by the provider, never carried here (privacy)."""

    def __init__(self, source: str, detail: str) -> None:
        self.source = source
        self.detail = detail
        super().__init__(f"{source}: parse error: {detail}")


class PrivilegedActionDenied(LapcareError):
    """User declined (or failed) polkit authentication — a legitimate choice,
    rendered as quiet degradation, never an error page (ADR-0004)."""

    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(f"authorization declined: {action}")


class FirmwareInstallFailed(LapcareError):
    """fwupd itself reported an install failure (not a polkit decline — that's
    PrivilegedActionDenied). Rendered as a retryable failure banner, never a
    full-page error (a firmware install failure is not a page failure)."""

    def __init__(self, device_id: str, detail: str) -> None:
        self.device_id = device_id
        self.detail = detail
        super().__init__(f"firmware install failed ({device_id}): {detail}")
