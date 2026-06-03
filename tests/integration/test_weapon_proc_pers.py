"""FIGHT-009..013 — weapon-proc TO_ROOM broadcast PERS parity.

ROM `src/fight.c:600-680` weapon special-attack broadcasts all use
`act(..., TO_ROOM)` macros with `$n` / `$p` substitutions, where
`$n` routes through `PERS(victim, looker)` per recipient. Python
previously baked `victim.name` into single fixed broadcast strings
via `_broadcast_room`, leaking the victim's name to every room
observer regardless of `can_see`.

Same channel-arc PERS fix pattern (SAY-002 / EMOTE-001 / TELL-003 /
SHOUT-003 / YELL-001 / FIGHT-004..008).
"""

from __future__ import annotations

from unittest.mock import patch

from mud.combat.engine import process_weapon_special_attacks
from mud.models.character import character_registry
from mud.models.constants import (
    WEAPON_FLAMING,
    WEAPON_FROST,
    WEAPON_POISON,
    WEAPON_SHOCKING,
    WEAPON_VAMPIRIC,
    AffectFlag,
)
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.world_state import create_test_character


class _MockWeapon:
    def __init__(self, name: str, level: int, flags: int) -> None:
        self.name = name
        self.level = level
        self.weapon_flags = flags


def _setup_room_and_chars(vnum: int, weapon_flags: int):
    test_room = Room(vnum=vnum, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
    test_room.people = []
    test_room.contents = []
    room_registry[vnum] = test_room

    attacker = create_test_character("Attaq", vnum)
    attacker.level = 20
    weapon = _MockWeapon("the sword", level=10, flags=weapon_flags)
    attacker.wielded_weapon = weapon

    victim = create_test_character("Aliceee", vnum)
    victim.level = 10
    victim.add_affect(AffectFlag.INVISIBLE)
    attacker.fighting = victim

    observer = create_test_character("Bobbb", vnum)
    observer.level = 10
    observer.messages = []

    return test_room, attacker, victim, observer


class TestWeaponProcBroadcastPers:
    """FIGHT-009..013 — weapon-proc TO_ROOM `$n` routes through PERS."""

    @patch("mud.combat.engine.saves_spell")
    def test_fight_009_poison_broadcast_uses_pers_for_invisible_victim(self, mock_saves):
        """FIGHT-009 — WEAPON_POISON TO_ROOM `$n is poisoned by the venom on $p.`

        ROM C: src/fight.c:614-615
            act ("$n is poisoned by the venom on $p.",
                 victim, wield, NULL, TO_ROOM);
        """
        mock_saves.return_value = False  # save fails → poison branch fires
        try:
            _, attacker, victim, observer = _setup_room_and_chars(2000, WEAPON_POISON)
            process_weapon_special_attacks(attacker, victim)

            joined = "\n".join(observer.messages).lower()
            assert "is poisoned by the venom" in joined, f"poison broadcast not delivered: {observer.messages!r}"
            assert "someone is poisoned by the venom on the sword" in joined, (
                f"PERS render missing for invisible victim: {observer.messages!r}"
            )
            assert "aliceee" not in joined, f"invisible victim name leaked: {observer.messages!r}"
        finally:
            room_registry.pop(2000, None)
            character_registry.clear()

    def test_fight_010_vampiric_broadcast_uses_pers_for_invisible_victim(self):
        """FIGHT-010 — WEAPON_VAMPIRIC TO_ROOM `$p draws life from $n.`

        ROM C: src/fight.c:643
            act ("$p draws life from $n.", victim, wield, NULL, TO_ROOM);
        """
        try:
            _, attacker, victim, observer = _setup_room_and_chars(2001, WEAPON_VAMPIRIC)
            process_weapon_special_attacks(attacker, victim)

            joined = "\n".join(observer.messages).lower()
            assert "draws life from" in joined, f"vampiric broadcast not delivered: {observer.messages!r}"
            assert "the sword draws life from someone" in joined, (
                f"PERS render missing for invisible victim: {observer.messages!r}"
            )
            assert "aliceee" not in joined, f"invisible victim name leaked: {observer.messages!r}"
        finally:
            room_registry.pop(2001, None)
            character_registry.clear()

    def test_fight_011_flaming_broadcast_uses_pers_for_invisible_victim(self):
        """FIGHT-011 — WEAPON_FLAMING TO_ROOM `$n is burned by $p.`

        ROM C: src/fight.c:654
            act ("$n is burned by $p.", victim, wield, NULL, TO_ROOM);
        """
        try:
            _, attacker, victim, observer = _setup_room_and_chars(2002, WEAPON_FLAMING)
            process_weapon_special_attacks(attacker, victim)

            joined = "\n".join(observer.messages).lower()
            assert "is burned by" in joined, f"flaming broadcast not delivered: {observer.messages!r}"
            assert "someone is burned by the sword" in joined, (
                f"PERS render missing for invisible victim: {observer.messages!r}"
            )
            assert "aliceee" not in joined, f"invisible victim name leaked: {observer.messages!r}"
        finally:
            room_registry.pop(2002, None)
            character_registry.clear()

    def test_fight_012_frost_broadcast_uses_pers_and_rom_wording(self):
        """FIGHT-012 — WEAPON_FROST TO_ROOM `$p freezes $n.` (PERS + wording).

        ROM C: src/fight.c:663
            act ("$p freezes $n.", victim, wield, NULL, TO_ROOM);

        Two divergences from Python's previous broadcast:
          (a) PERS gap on $n.
          (b) Wording swap — ROM is `"$p freezes $n."` (e.g. `"the
              sword freezes Alice."`); Python emitted
              `f"{victim.name} is frozen by {weapon_name}."`
              (`"Alice is frozen by the sword."`).
        """
        try:
            _, attacker, victim, observer = _setup_room_and_chars(2003, WEAPON_FROST)
            process_weapon_special_attacks(attacker, victim)

            joined = "\n".join(observer.messages).lower()
            # ROM wording — "the sword freezes Alice/someone."
            assert "the sword freezes" in joined, f"ROM wording '$p freezes $n' missing: {observer.messages!r}"
            assert "the sword freezes someone" in joined, (
                f"PERS render missing for invisible victim: {observer.messages!r}"
            )
            # Old Python wording must be gone.
            assert "is frozen by" not in joined, (
                f"old Python wording 'X is frozen by Y' still present: {observer.messages!r}"
            )
            assert "aliceee" not in joined, f"invisible victim name leaked: {observer.messages!r}"
        finally:
            room_registry.pop(2003, None)
            character_registry.clear()

    def test_fight_013_shocking_broadcast_uses_pers_for_invisible_victim(self):
        """FIGHT-013 — WEAPON_SHOCKING TO_ROOM `$n is struck by lightning from $p.`

        ROM C: src/fight.c:673-674
            act ("$n is struck by lightning from $p.", victim, wield, NULL,
                 TO_ROOM);
        """
        try:
            _, attacker, victim, observer = _setup_room_and_chars(2004, WEAPON_SHOCKING)
            process_weapon_special_attacks(attacker, victim)

            joined = "\n".join(observer.messages).lower()
            assert "is struck by lightning from" in joined, f"shocking broadcast not delivered: {observer.messages!r}"
            assert "someone is struck by lightning from the sword" in joined, (
                f"PERS render missing for invisible victim: {observer.messages!r}"
            )
            assert "aliceee" not in joined, f"invisible victim name leaked: {observer.messages!r}"
        finally:
            room_registry.pop(2004, None)
            character_registry.clear()
