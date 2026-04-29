from __future__ import annotations

from collections.abc import Callable

from mud.config import get_pulse_violence
from mud.handler import deduct_cost
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import ActFlag
from mud.net.protocol import broadcast_room
from mud.skills import handlers as spell_handlers
from mud.utils import rng_mm

_ServiceFunc = Callable[[Character, Character | None], int | bool]


class _HealerService(tuple):
    __slots__ = ()

    @property
    def key(self) -> str:
        return self[0]

    @property
    def match_names(self) -> tuple[str, ...]:
        return self[1]

    @property
    def display_line(self) -> str:
        return self[2]

    @property
    def words(self) -> str:
        return self[3]

    @property
    def cost_silver(self) -> int:
        return self[4]

    @property
    def spell(self) -> _ServiceFunc | None:
        return self[5]


_SERVICES: tuple[_HealerService, ...] = (
    _HealerService(
        ("light", ("light",), "  light: cure light wounds      10 gold", "judicandus dies", 1000, spell_handlers.cure_light)
    ),
    _HealerService(
        (
            "serious",
            ("serious",),
            "  serious: cure serious wounds  15 gold",
            "judicandus gzfuajg",
            1600,
            spell_handlers.cure_serious,
        )
    ),
    _HealerService(
        (
            "critical",
            ("critical", "critic"),
            "  critic: cure critical wounds  25 gold",
            "judicandus qfuhuqar",
            2500,
            spell_handlers.cure_critical,
        )
    ),
    _HealerService(("heal", ("heal",), "  heal: healing spell          50 gold", "pzar", 5000, spell_handlers.heal)),
    _HealerService(
        (
            "blindness",
            ("blindness", "blind"),
            "  blind: cure blindness         20 gold",
            "judicandus noselacri",
            2000,
            spell_handlers.cure_blindness,
        )
    ),
    _HealerService(
        (
            "disease",
            ("disease",),
            "  disease: cure disease         15 gold",
            "judicandus eugzagz",
            1500,
            spell_handlers.cure_disease,
        )
    ),
    _HealerService(
        (
            "poison",
            ("poison",),
            "  poison:  cure poison          25 gold",
            "judicandus sausabru",
            2500,
            spell_handlers.cure_poison,
        )
    ),
    _HealerService(
        (
            "uncurse",
            ("uncurse", "curse"),
            "  uncurse: remove curse          50 gold",
            "candussido judifgz",
            5000,
            spell_handlers.remove_curse,
        )
    ),
    _HealerService(
        (
            "refresh",
            ("refresh", "moves"),
            "  refresh: restore movement      5 gold",
            "candusima",
            500,
            spell_handlers.refresh,
        )
    ),
    _HealerService(("mana", ("mana", "energize"), "  mana:  restore mana          10 gold", "energizer", 1000, None)),
)

PRICE_GOLD = {service.key: service.cost_silver // 100 for service in _SERVICES}


def _has_act_flag(entity: object, flag: ActFlag) -> bool:
    checker = getattr(entity, "has_act_flag", None)
    if callable(checker):
        try:
            return bool(checker(flag))
        except Exception:
            return False

    try:
        act_bits = int(getattr(entity, "act", 0) or 0)
    except (TypeError, ValueError):
        act_bits = 0
    if act_bits & int(flag):
        return True

    proto = getattr(entity, "prototype", None)
    if proto is not None:
        try:
            proto_bits = int(getattr(proto, "act", 0) or 0)
        except (TypeError, ValueError):
            proto_bits = 0
        if proto_bits & int(flag):
            return True
    return False


def _is_legacy_healer(entity: object) -> bool:
    if getattr(entity, "is_healer", False):
        return True
    proto = getattr(entity, "prototype", None)
    spec = getattr(proto, "spec_fun", "") if proto is not None else ""
    return isinstance(spec, str) and spec.lower() == "spec_healer"


def _is_prefix(argument: str, word: str) -> bool:
    return bool(argument) and word.lower().startswith(argument.lower())


def _match_service(argument: str) -> _HealerService | None:
    for service in _SERVICES:
        for candidate in service.match_names:
            if _is_prefix(argument, candidate):
                return service
    return None


def _apply_wait_state(char: Character, beats: int) -> None:
    if beats <= 0 or not hasattr(char, "wait"):
        return
    current = int(getattr(char, "wait", 0) or 0)
    char.wait = max(current, beats)


def _healer_name(healer: object) -> str:
    return getattr(healer, "short_descr", None) or getattr(healer, "name", "The healer")


def _player_message_after(char: Character, start_index: int, fallback: str) -> str:
    messages = getattr(char, "messages", None)
    if not isinstance(messages, list):
        return fallback
    new_messages = [str(message) for message in messages[start_index:] if message]
    return new_messages[-1] if new_messages else fallback


def _find_healer(char: Character) -> object | None:
    """Find a healer NPC in the room.

    Mirrors ROM `src/healer.c:48-55` by preferring NPCs with `ACT_IS_HEALER`.
    The legacy `spec_healer` / `is_healer` fallback is retained so existing
    area data and tests still resolve healers during the transition.
    """
    room = getattr(char, "room", None)
    for mob in getattr(room, "people", []):
        if not getattr(mob, "is_npc", False):
            continue
        if _has_act_flag(mob, ActFlag.IS_HEALER) or _is_legacy_healer(mob):
            return mob
    return None


def do_heal(char: Character, args: str = "") -> str:
    """Provide ROM healer services from `src/healer.c:41-197`."""

    healer = _find_healer(char)
    if not healer:
        return "You can't do that here."

    arg = (args or "").strip().lower()
    if not arg:
        lines = [f"{_healer_name(healer)} says 'I offer the following spells:'"]
        lines.extend(service.display_line for service in _SERVICES)
        lines.append(" Type heal <type> to be healed.")
        return "\n".join(lines)

    service = _match_service(arg)
    if service is None:
        return f"{_healer_name(healer)} says 'Type 'heal' for a list of spells.'"

    total_wealth = int(getattr(char, "gold", 0) or 0) * 100 + int(getattr(char, "silver", 0) or 0)
    if service.cost_silver > total_wealth:
        return "You do not have enough gold for my services."

    _apply_wait_state(char, get_pulse_violence())
    deduct_cost(char, service.cost_silver)

    healer.gold = int(getattr(healer, "gold", 0) or 0) + service.cost_silver // 100
    healer.silver = int(getattr(healer, "silver", 0) or 0) + service.cost_silver % 100

    room = getattr(healer, "room", None)
    if room is not None:
        broadcast_room(room, f"{_healer_name(healer)} utters the words '{service.words}'.", exclude=healer)

    if service.spell is None:
        level = max(int(getattr(healer, "level", 0) or 0), 0)
        char.mana += rng_mm.dice(2, 8) + c_div(level, 3)
        char.mana = min(int(getattr(char, "mana", 0) or 0), int(getattr(char, "max_mana", 0) or 0))
        return "A warm glow passes through you."

    start_index = len(getattr(char, "messages", []) or [])
    service.spell(healer, char)
    return _player_message_after(char, start_index, "Ok.")
