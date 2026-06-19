"""INV-050 — the silent bool ``is_safe`` is now a thin wrapper over the faithful
``_kill_safety_message`` mirror.

ROM has ONE ``is_safe`` (``src/fight.c:1018-1124``): a bool that ALSO writes the
rejection line before returning TRUE. The Python port had split this into a
silent bool (``mud/combat/safety.py:is_safe``) and a message-returning mirror
(``mud/commands/combat.py:_kill_safety_message``). The bool was *bidirectionally
divergent* from ROM — it checked ROOM_SAFE for ALL victims and lacked ROM's
retaliation / immortal bypasses and the PC-vs-PC clan ladder.

This converges the bool onto the mirror (``is_safe(ch, v) == (_kill_safety_message
(ch, v) is not None)``), leaving only the intentionally-silent ``apply_damage``
re-check (``combat/engine.py``, FIGHT-002, ROM ``src/fight.c:730``) as its caller.

The clearest divergence the wrapper fixes: ROM evaluates the retaliation bypass
(``victim->fighting == ch`` → return FALSE, ``src/fight.c:1023``) BEFORE the
NPC-victim ROOM_SAFE gate (``:1034``). The old bool checked ROOM_SAFE first and
had no retaliation bypass at all, so a victim already fighting the attacker inside
a safe room was wrongly flagged "safe" — which would stall an in-progress combat
at the ``apply_damage`` re-check.
"""

from __future__ import annotations

import pytest

from mud.combat.safety import is_safe
from mud.commands.combat import _kill_safety_message
from mud.models.character import Character
from mud.models.constants import ActFlag, RoomFlag
from mud.world import create_test_character, initialize_world

_ROOM = 2300  # non-safe room in area.lst


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_pc(name: str, level: int = 20) -> Character:
    ch = create_test_character(name, _ROOM)
    ch.is_npc = False
    ch.level = level
    ch.act = 0
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    return ch


def _make_npc(name: str, level: int = 20) -> Character:
    ch = create_test_character(name, _ROOM)
    ch.is_npc = True
    ch.level = level
    ch.act = int(ActFlag.IS_NPC)
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    return ch


def test_inv050_retaliation_bypass_precedes_safe_room() -> None:
    # mirrors ROM src/fight.c:1023 — `victim->fighting == ch || victim == ch`
    # returns FALSE *before* the NPC ROOM_SAFE gate at :1034. A victim already
    # fighting the attacker is NOT safe, even inside a safe room.
    attacker = _make_pc("Attacker")
    victim = _make_npc("Defender")
    assert victim.room is not None
    victim.room.room_flags = int(getattr(victim.room, "room_flags", 0)) | int(RoomFlag.ROOM_SAFE)
    victim.fighting = attacker  # already retaliating

    result = is_safe(attacker, victim)

    assert result is False, (
        f"is_safe must return False (not safe) when the victim is already fighting "
        f"the attacker, even in a ROOM_SAFE room; got {result!r}. ROM src/fight.c:1023 "
        "evaluates the retaliation bypass BEFORE the ROOM_SAFE gate at :1034."
    )


def test_inv050_bool_equals_mirror_across_cases() -> None:
    # The bool must agree with the faithful message-mirror on every branch:
    # is_safe(ch, v) is True  <=>  _kill_safety_message(ch, v) is not None.
    attacker = _make_pc("Striker")

    # Plain NPC victim, non-safe room, no retaliation → both report NOT safe.
    # (Checked first: all _ROOM chars share one Room instance, so the ROOM_SAFE
    # mutation below would otherwise contaminate this case.)
    mob = _make_npc("Orc")
    assert is_safe(attacker, mob) is (_kill_safety_message(attacker, mob) is not None)
    assert is_safe(attacker, mob) is False

    # NPC victim in a safe room (no retaliation) → both report safe.
    healer = _make_npc("Healer")
    assert healer.room is not None
    healer.room.room_flags = int(getattr(healer.room, "room_flags", 0)) | int(RoomFlag.ROOM_SAFE)
    assert is_safe(attacker, healer) is (_kill_safety_message(attacker, healer) is not None)
    assert is_safe(attacker, healer) is True

    # NPC victim retaliating in that same safe room → both report NOT safe.
    healer.fighting = attacker
    assert is_safe(attacker, healer) is (_kill_safety_message(attacker, healer) is not None)
    assert is_safe(attacker, healer) is False
