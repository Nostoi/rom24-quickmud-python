from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Sunlight(IntEnum):
    DARK = 0
    RISE = 1
    LIGHT = 2
    SET = 3


@dataclass
class TimeInfo:
    hour: int = 0
    day: int = 0
    month: int = 0
    year: int = 0
    sunlight: Sunlight = Sunlight.DARK

    def advance_hour(self) -> list[str]:
        """Advance time by one hour and return broadcast messages."""
        messages: list[str] = []
        self.hour += 1
        if self.hour >= 24:
            self.hour = 0
            self.day += 1
            if self.day >= 35:
                self.day = 0
                self.month += 1
                if self.month >= 17:
                    self.month = 0
                    self.year += 1
        if self.hour == 5:
            self.sunlight = Sunlight.LIGHT
            messages.append("The day has begun.")
        elif self.hour == 6:
            self.sunlight = Sunlight.RISE
            messages.append("The sun rises in the east.")
        elif self.hour == 19:
            self.sunlight = Sunlight.SET
            messages.append("The sun slowly disappears in the west.")
        elif self.hour == 20:
            self.sunlight = Sunlight.DARK
            messages.append("The night has begun.")
        return messages


time_info = TimeInfo()
