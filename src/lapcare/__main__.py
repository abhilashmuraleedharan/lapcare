# SPDX-License-Identifier: GPL-3.0-or-later
"""Allow running from a source checkout: PYTHONPATH=src python3 -m lapcare."""
import sys

from lapcare.app import main

sys.exit(main())
