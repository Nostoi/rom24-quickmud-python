from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from mud import mobprog
from mud.ai import aggressive_update
from mud.config import get_pulse_area, get_pulse_tick, get_pulse_violence
from mud.imc import pump_idle
from mud.logging.admin import rotate_admin_log
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.net.protocol import broadcast_global
from mud.skills.registry import skill_registry
from mud.spawning.reset_handler import reset_tick
from mud.spec_funs import run_npc_specs
from mud.time import time_info


@dataclass
class WeatherState:
    """Very small placeholder for global weather."""

    sky: str = "sunny"


weather = WeatherState()


@dataclass
class TimedEvent:
    ticks: int
    callback: Callable[[], None]


events: list[TimedEvent] = []


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
# Countdown counters mirror ROM's --pulse_X <= 0 semantics so cadence shifts
# (e.g., TIME_SCALE changes) take effect immediately after the next pulse.
_point_counter = get_pulse_tick()
_violence_counter = get_pulse_violence()
_area_counter = get_pulse_area()


def violence_tick() -> None:
    """Consume wait/daze counters once per pulse for all characters."""

    for ch in list(character_registry):
        wait = int(getattr(ch, "wait", 0) or 0)
        if wait > 0:
            ch.wait = wait - 1
        else:
            ch.wait = 0

        if hasattr(ch, "daze"):
            daze = int(getattr(ch, "daze", 0) or 0)
            if daze > 0:
                ch.daze = daze - 1
            else:
                ch.daze = max(0, daze)


def _mobprog_idle_tick() -> None:
    """Run mob program random/delay triggers for idle NPCs."""

    for ch in list(character_registry):
        if not getattr(ch, "is_npc", False):
            continue
        default_pos = getattr(ch, "default_pos", getattr(ch, "position", Position.STANDING))
        if getattr(ch, "position", default_pos) != default_pos:
            continue
        if mobprog.mp_delay_trigger(ch):
            continue
        mobprog.mp_random_trigger(ch)


def game_tick() -> None:
    """Run a full game tick: time, regen, weather, timed events, and resets."""
    global _pulse_counter, _point_counter, _violence_counter, _area_counter
    _pulse_counter += 1

    # Consume wait/daze every pulse before evaluating cadence counters.
    violence_tick()

    # Track pulses for future violence update hooks (combat rounds, etc.).
    _violence_counter -= 1
    if _violence_counter <= 0:
        _violence_counter = get_pulse_violence()

    # Point pulses drive time/weather/regen updates.
    _point_counter -= 1
    point_pulse = _point_counter <= 0
    if point_pulse:
        _point_counter = get_pulse_tick()
        time_tick()
        weather_tick()
        regen_tick()
        pump_idle()

    _area_counter -= 1
    if _area_counter <= 0:
        _area_counter = get_pulse_area()
        reset_tick()
    event_tick()
    _mobprog_idle_tick()
    aggressive_update()
    # Invoke NPC special functions after resets to mirror ROM's update cadence
    run_npc_specs()
