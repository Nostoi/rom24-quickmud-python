from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from mud.models.character import Character, character_registry
from mud.skills.registry import skill_registry
from mud.spawning.reset_handler import reset_tick
from mud.time import time_info
from mud.config import get_pulse_tick, get_pulse_violence, GAME_LOOP_STRICT_POINT
from mud.net.protocol import broadcast_global
from mud.logging.admin import rotate_admin_log
from mud.spec_funs import run_npc_specs


@dataclass
class WeatherState:
    """Very small placeholder for global weather."""
    sky: str = "sunny"


weather = WeatherState()


@dataclass
class TimedEvent:
    ticks: int
    callback: Callable[[], None]


events: List[TimedEvent] = []


def schedule_event(ticks: int, callback: Callable[[], None]) -> None:
    """Schedule a callback to run after a number of ticks."""
    events.append(TimedEvent(ticks, callback))


def event_tick() -> None:
    """Advance timers and fire ready callbacks."""
    for ev in events[:]:
        ev.ticks -= 1
        if ev.ticks <= 0:
            ev.callback()
            events.remove(ev)


def regen_character(ch: Character) -> None:
    """Apply a single tick of regeneration to a character."""
    ch.hit = min(ch.max_hit, ch.hit + 1)
    ch.mana = min(ch.max_mana, ch.mana + 1)
    ch.move = min(ch.max_move, ch.move + 1)
    skill_registry.tick(ch)


def regen_tick() -> None:
    for ch in list(character_registry):
        regen_character(ch)


_WEATHER_STATES = ["sunny", "cloudy", "rainy"]


def weather_tick() -> None:
    """Cycle through simple weather states."""
    index = _WEATHER_STATES.index(weather.sky)
    weather.sky = _WEATHER_STATES[(index + 1) % len(_WEATHER_STATES)]


def time_tick() -> None:
    """Advance world time and broadcast day/night transitions."""
    messages = time_info.advance_hour()
    if time_info.hour == 0:
        try:
            rotate_admin_log()
        except Exception:
            pass
    for message in messages:
        broadcast_global(message, channel="info")


_pulse_counter = 0
_violence_counter = 0


def violence_tick() -> None:
    """Violence cadence updates: decrement wait/daze counters."""
    for ch in list(character_registry):
        ch.wait = max(0, int(getattr(ch, "wait", 0)) - 1)
        # daze is optional in some tests; default to attr when present
        if hasattr(ch, "daze"):
            ch.daze = max(0, int(getattr(ch, "daze", 0)) - 1)


def game_tick() -> None:
    """Run a full game tick: time, regen, weather, timed events, and resets."""
    global _pulse_counter, _violence_counter
    _pulse_counter += 1
    # Violence cadence: decrement wait/daze on PULSE_VIOLENCE boundaries
    # This mirrors ROM's update_handler calling violence_update.
    _violence_counter += 1
    if _violence_counter % get_pulse_violence() == 0:
        violence_tick()
    # Advance time/weather/resets on point pulses, preserving legacy behavior when not strict
    point_pulse = (_pulse_counter % get_pulse_tick() == 0)
    if point_pulse:
        time_tick()
        weather_tick()
        reset_tick()
    else:
        if not GAME_LOOP_STRICT_POINT:
            weather_tick()
            reset_tick()
    regen_tick()
    event_tick()
    # Invoke NPC special functions after resets to mirror ROM's update cadence
    run_npc_specs()
