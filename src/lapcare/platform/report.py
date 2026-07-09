# SPDX-License-Identifier: GPL-3.0-or-later
"""Report file writing (implements core.ports.ReportWriter).

Plain UTF-8 text to a user-chosen path. Writes are atomic-enough for a
desktop export (temp file in the target directory, then rename) so a failed
write never leaves a half-document at the chosen name.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile

log = logging.getLogger(__name__)


class TextReportWriter:
    def write(self, path: str, content: str) -> None:
        directory = os.path.dirname(path) or "."
        fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".lapcare-export-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(temp_path, path)
        except OSError:
            with contextlib.suppress(OSError):  # best-effort cleanup
                os.unlink(temp_path)
            raise
        # mkstemp creates 0600; exports are documents, give them normal perms.
        os.chmod(path, 0o644)
        log.debug("report written: %d bytes", len(content))
