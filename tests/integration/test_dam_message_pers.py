"""DAMMSG-001/002/003 — `dam_message` PERS parity on TO_NOTVICT/TO_VICT/TO_CHAR.

ROM `src/fight.c:dam_message` (lines 2035-2233) ends with three
`act()` macro calls that evaluate `PERS()` per recipient:

    act (buf1, ch, NULL, victim, TO_NOTVICT);  // room observers
    act (buf2, ch, NULL, victim, TO_CHAR);     // attacker
    act (buf3, ch, NULL, victim, TO_VICT);     // victim

Python's previous `dam_message` returned `DamageMessages` with three
pre-rendered strings baked from `attacker.name`/`victim.name`, then
the engine broadcast them via `_broadcast_room` / `_push_message`
without per-recipient PERS substitution — leaking both names to
every observer regardless of `can_see`.

Same channel-arc PERS fix pattern (SAY-002 / EMOTE-001 / TELL-003 /
SHOUT-003 / YELL-001 / FIGHT-004..014).
"""

from __future__ import annotations

from mud.combat.engine import _broadcast_damage_messages
from mud.combat.messages import TYPE_HIT, dam_message
from mud.models.character import character_registry
from mud.models.constants import AffectFlag
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.world_state import create_test_character


def _setup_three(vnum: int):
    test_room = Room(vnum=vnum, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
    test_room.people = []
    test_room.contents = []
    room_registry[vnum] = test_room

    attacker = create_test_character("Aliceee", vnum)
    attacker.level = 10
    attacker.messages = []

    victim = create_test_character("Bobbb", vnum)
    victim.level = 10
    victim.max_hit = 100
    victim.hit = 100
    victim.messages = []

    observer = create_test_character("Carolll", vnum)
    observer.level = 10
    observer.messages = []

    return test_room, attacker, victim, observer


class TestDamMessagePers:
    def test_dammsg_001_to_notvict_renders_attacker_and_victim_per_observer(self):
        """DAMMSG-001 — TO_NOTVICT `$n` and `$N` route through PERS per-listener.

        ROM C: src/fight.c:2222
            act (buf1, ch, NULL, victim, TO_NOTVICT);

        Invisible attacker + observer without DETECT_INVIS → "someone"
        for $n. Visible victim → real name for $N.
        """
        _, attacker, victim, observer = _setup_three(2200)
        attacker.add_affect(AffectFlag.INVISIBLE)
        try:
            messages = dam_message(attacker, victim, 50, TYPE_HIT, immune=False)
            _broadcast_damage_messages(attacker, victim, messages)

            joined = "\n".join(observer.messages).lower()
            assert "someone" in joined, (
                f"PERS render missing for invisible attacker in TO_NOTVICT: {observer.messages!r}"
            )
            assert "bobbb" in joined, f"visible victim should render real name in TO_NOTVICT: {observer.messages!r}"
            assert "aliceee" not in joined, f"invisible attacker name leaked to room observer: {observer.messages!r}"
        finally:
            room_registry.pop(2200, None)
            character_registry.clear()

    def test_dammsg_002_to_vict_renders_attacker_per_victim(self):
        """DAMMSG-002 — TO_VICT `$n` routes through PERS for victim's view.

        ROM C: src/fight.c:2224
            act (buf3, ch, NULL, victim, TO_VICT);
        """
        _, attacker, victim, _ = _setup_three(2201)
        attacker.add_affect(AffectFlag.INVISIBLE)
        try:
            messages = dam_message(attacker, victim, 50, TYPE_HIT, immune=False)
            _broadcast_damage_messages(attacker, victim, messages)

            joined = "\n".join(victim.messages).lower()
            assert "someone" in joined, f"PERS render missing for invisible attacker in TO_VICT: {victim.messages!r}"
            assert "aliceee" not in joined, f"invisible attacker name leaked to victim: {victim.messages!r}"
        finally:
            room_registry.pop(2201, None)
            character_registry.clear()

    def test_dammsg_003_to_char_renders_victim_per_attacker(self):
        """DAMMSG-003 — TO_CHAR `$N` routes through PERS for attacker's view.

        ROM C: src/fight.c:2223
            act (buf2, ch, NULL, victim, TO_CHAR);

        Invisible victim + attacker without DETECT_INVIS → "someone".
        """
        _, attacker, victim, _ = _setup_three(2202)
        victim.add_affect(AffectFlag.INVISIBLE)
        try:
            messages = dam_message(attacker, victim, 50, TYPE_HIT, immune=False)
            _broadcast_damage_messages(attacker, victim, messages)

            joined = "\n".join(attacker.messages).lower()
            assert "someone" in joined, f"PERS render missing for invisible victim in TO_CHAR: {attacker.messages!r}"
            assert "bobbb" not in joined, f"invisible victim name leaked to attacker: {attacker.messages!r}"
        finally:
            room_registry.pop(2202, None)
            character_registry.clear()
