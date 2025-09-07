"""Wiznet flag definitions.

Placeholder module defining wiznet flags for immortal notifications.
"""
from __future__ import annotations

from enum import IntFlag


class WiznetFlag(IntFlag):
    """Wiznet flags mirroring ROM bit values."""

    WIZ_ON = 0x00000001
