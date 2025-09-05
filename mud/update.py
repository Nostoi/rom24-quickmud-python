from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, List

from mud.models.character import character_registry
from mud.spawning.reset_handler import reset_tick


@dataclass
class Weather:
    """Very small subset of ROM weather handling."""

    cycle: List[str] = field(
        default_factory=lambda: ["night", "sunrise", "day", "sunset"]
    )
    index: int = 0

    @property
    def sunlight(self) -> str:
        """Current sunlight state."""
        return self.cycle[self.index]

    def advance(self) -> None:
        """Advance to the next sunlight state."""
        self.index = (self.index + 1) % len(self.cycle)


weather = Weather()


@dataclass
class TimedEvent:
    ticks: int
    callback: Callable[[], None]


events: List[TimedEvent] = []


def schedule_event(ticks: int, callback: Callable[[], None]) -> None:
    """Schedule *callback* to run after ``ticks`` update cycles."""

    events.append(TimedEvent(ticks, callback))


def regen_tick() -> None:
    """Regenerate hit, mana, and move for all characters."""

    for ch in character_registry:
        if ch.hit < ch.max_hit:
            ch.hit = min(ch.max_hit, ch.hit + 1)
        if ch.mana < ch.max_mana:
            ch.mana = min(ch.max_mana, ch.mana + 1)
        if ch.move < ch.max_move:
            ch.move = min(ch.max_move, ch.move + 1)


def weather_tick() -> None:
    """Advance the global weather cycle."""

    weather.advance()


def event_tick() -> None:
    """Run any scheduled events whose timers have expired."""

    for event in list(events):
        event.ticks -= 1
        if event.ticks <= 0:
            event.callback()
            events.remove(event)


def update_tick() -> None:
    """Advance one game tick of regeneration, weather, events, and resets."""

    regen_tick()
    weather_tick()
    event_tick()
    reset_tick()
