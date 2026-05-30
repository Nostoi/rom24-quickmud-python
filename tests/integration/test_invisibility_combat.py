"""
Integration tests for invisibility in combat commands.

Tests verify that combat targeting respects AFF_INVISIBLE and AFF_DETECT_INVIS.
"""

from __future__ import annotations

from mud.combat.engine import _position_change_message
from mud.commands.dispatcher import process_command
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.world_state import create_test_character


class TestCombatInvisibility:
    """Test combat commands respect invisibility."""

    def test_cannot_kill_invisible_mob(self):
        """
        Test: Cannot target invisible mobs with KILL command.

        ROM Parity: Mirrors ROM src/fight.c - can_see() check before combat

        Given: Invisible mob in room
        When: Player tries to kill mob
        Then: "They aren't here" message
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            attacker = create_test_character("Attacker", 1000)
            attacker.level = 10

            invisible_mob = Character(name="Orc", level=5, room=test_room)
            invisible_mob.is_npc = True
            invisible_mob.short_descr = "an orc"
            invisible_mob.long_descr = "An orc is here."
            invisible_mob.add_affect(AffectFlag.INVISIBLE)
            test_room.people.append(invisible_mob)
            character_registry.append(invisible_mob)

            result = process_command(attacker, "kill orc")
            assert "aren't here" in result.lower(), f"Should not see invisible mob: {result}"

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()

    def test_can_kill_invisible_with_detect_invis(self):
        """
        Test: Can target invisible mobs with DETECT_INVIS.

        ROM Parity: Mirrors ROM src/fight.c - can_see() with AFF_DETECT_INVIS

        Given: Invisible mob + attacker with detect_invis
        When: Player tries to kill mob
        Then: Combat begins successfully
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            attacker = create_test_character("Attacker", 1000)
            attacker.level = 10
            attacker.add_affect(AffectFlag.DETECT_INVIS)

            invisible_mob = Character(name="Orc", level=5, room=test_room)
            invisible_mob.is_npc = True
            invisible_mob.short_descr = "an orc"
            invisible_mob.long_descr = "An orc is here."
            invisible_mob.add_affect(AffectFlag.INVISIBLE)
            test_room.people.append(invisible_mob)
            character_registry.append(invisible_mob)

            result = process_command(attacker, "kill orc")
            assert "aren't here" not in result.lower(), f"Should see with detect_invis: {result}"

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()

    def test_cannot_backstab_invisible_victim(self):
        """
        Test: Cannot backstab invisible victims.

        ROM Parity: Mirrors ROM src/fight.c - backstab visibility check

        Given: Invisible victim in room
        When: Thief tries to backstab
        Then: "They aren't here" message
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            thief = create_test_character("Thief", 1000)
            thief.level = 10
            thief.skills = {"backstab": 75}

            invisible_victim = Character(name="Victim", level=5, room=test_room)
            invisible_victim.is_npc = True
            invisible_victim.short_descr = "a victim"
            invisible_victim.long_descr = "A victim is here."
            invisible_victim.hit = 100
            invisible_victim.max_hit = 100
            invisible_victim.add_affect(AffectFlag.INVISIBLE)
            test_room.people.append(invisible_victim)
            character_registry.append(invisible_victim)

            result = process_command(thief, "backstab victim")
            assert "aren't here" in result.lower(), f"Should not see invisible victim: {result}"

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()

    def test_cannot_rescue_invisible_ally(self):
        """
        Test: Cannot rescue invisible allies.

        ROM Parity: Mirrors ROM src/fight.c - rescue visibility check

        Given: Invisible ally in room
        When: Player tries to rescue ally
        Then: "They aren't here" message
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            rescuer = create_test_character("Rescuer", 1000)
            rescuer.level = 10

            invisible_ally = create_test_character("Ally", 1000)
            invisible_ally.level = 5
            invisible_ally.add_affect(AffectFlag.INVISIBLE)

            result = process_command(rescuer, "rescue ally")
            assert "aren't here" in result.lower(), f"Should not see invisible ally: {result}"

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()

    def test_can_rescue_invisible_with_detect_invis(self):
        """
        Test: Can rescue invisible allies with DETECT_INVIS.

        ROM Parity: Mirrors ROM src/fight.c - rescue with AFF_DETECT_INVIS

        Given: Invisible ally + rescuer with detect_invis
        When: Player tries to rescue ally
        Then: Rescue command processes (may fail for other reasons like "not fighting")
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            rescuer = create_test_character("Rescuer", 1000)
            rescuer.level = 10
            rescuer.add_affect(AffectFlag.DETECT_INVIS)

            invisible_ally = create_test_character("Ally", 1000)
            invisible_ally.level = 5
            invisible_ally.add_affect(AffectFlag.INVISIBLE)

            result = process_command(rescuer, "rescue ally")
            assert "aren't here" not in result.lower(), f"Should see with detect_invis: {result}"

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()


class TestPositionChangeBroadcastPers:
    """FIGHT-004..008 — position-change TO_ROOM broadcasts must route
    `$n` through ROM PERS() so an invisible victim renders as
    "someone" to room observers without DETECT_INVIS. Mirrors the
    channel-arc fix pattern (SAY-002 / EMOTE-001 / TELL-003 /
    SHOUT-003 / YELL-001).
    """

    def test_fight_004_pos_mortal_broadcast_uses_pers_for_invisible_victim(self):
        """FIGHT-004 — POS_MORTAL TO_ROOM `$n` routes through PERS.

        ROM C: src/fight.c:837-838
            act ("$n is mortally wounded, and will die soon, if not aided.",
                 victim, NULL, NULL, TO_ROOM);

        ROM's act() macro substitutes `$n` per-listener through
        PERS(victim, looker), so an invisible victim renders as
        "someone" to room observers without DETECT_INVIS. Python
        previously baked `victim.name` into a single fixed broadcast
        string via `_broadcast_room`, leaking the victim's name to
        every recipient.
        """
        test_room = Room(vnum=1000, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1000] = test_room

        try:
            victim = create_test_character("Aliceee", 1000)
            victim.level = 5
            victim.add_affect(AffectFlag.INVISIBLE)
            victim.position = Position.MORTAL

            observer = create_test_character("Bobbb", 1000)
            observer.level = 5
            # No DETECT_INVIS — must not see Aliceee.
            observer.messages = []

            _position_change_message(victim, Position.STANDING)

            joined = "\n".join(observer.messages)
            assert "is mortally wounded" in joined.lower(), (
                f"POS_MORTAL broadcast not delivered to observer: {observer.messages!r}"
            )
            assert "someone is mortally wounded" in joined.lower(), (
                f"PERS render missing — expected 'someone' for invisible victim; got: {observer.messages!r}"
            )
            assert "aliceee" not in joined.lower(), (
                f"invisible victim's name leaked through TO_ROOM broadcast: {observer.messages!r}"
            )

        finally:
            room_registry.pop(1000, None)
            character_registry.clear()

    def test_fight_005_pos_incap_broadcast_uses_pers_for_invisible_victim(self):
        """FIGHT-005 — POS_INCAP TO_ROOM `$n` routes through PERS.

        ROM C: src/fight.c:845-846
            act ("$n is incapacitated and will slowly die, if not aided.",
                 victim, NULL, NULL, TO_ROOM);
        """
        test_room = Room(vnum=1001, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1001] = test_room

        try:
            victim = create_test_character("Aliceee", 1001)
            victim.level = 5
            victim.add_affect(AffectFlag.INVISIBLE)
            victim.position = Position.INCAP

            observer = create_test_character("Bobbb", 1001)
            observer.level = 5
            observer.messages = []

            _position_change_message(victim, Position.STANDING)

            joined = "\n".join(observer.messages).lower()
            assert "is incapacitated" in joined, (
                f"POS_INCAP broadcast not delivered: {observer.messages!r}"
            )
            assert "someone is incapacitated" in joined, (
                f"PERS render missing for invisible victim: {observer.messages!r}"
            )
            assert "aliceee" not in joined, (
                f"invisible victim name leaked: {observer.messages!r}"
            )

        finally:
            room_registry.pop(1001, None)
            character_registry.clear()

    def test_fight_006_pos_stunned_broadcast_uses_pers_for_invisible_victim(self):
        """FIGHT-006 — POS_STUNNED TO_ROOM `$n` routes through PERS.

        ROM C: src/fight.c:853-854
            act ("$n is stunned, but will probably recover.",
                 victim, NULL, NULL, TO_ROOM);
        """
        test_room = Room(vnum=1002, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1002] = test_room

        try:
            victim = create_test_character("Aliceee", 1002)
            victim.level = 5
            victim.add_affect(AffectFlag.INVISIBLE)
            victim.position = Position.STUNNED

            observer = create_test_character("Bobbb", 1002)
            observer.level = 5
            observer.messages = []

            _position_change_message(victim, Position.STANDING)

            joined = "\n".join(observer.messages).lower()
            assert "is stunned" in joined, (
                f"POS_STUNNED broadcast not delivered: {observer.messages!r}"
            )
            assert "someone is stunned" in joined, (
                f"PERS render missing for invisible victim: {observer.messages!r}"
            )
            assert "aliceee" not in joined, (
                f"invisible victim name leaked: {observer.messages!r}"
            )

        finally:
            room_registry.pop(1002, None)
            character_registry.clear()

    def test_fight_007_pos_dead_broadcast_uses_pers_and_red_colour_and_two_bangs(self):
        """FIGHT-007 — POS_DEAD TO_ROOM `{R$n is DEAD!!{x` (3 sub-gaps).

        ROM C: src/fight.c:860
            act ("{R$n is DEAD!!{x", victim, 0, 0, TO_ROOM);

        Three divergences from Python's previous
        `f"{victim.name} is DEAD!!!"` baked broadcast:
          (a) `$n` must route through PERS — invisible victim renders
              as "someone" to observers without DETECT_INVIS.
          (b) Message must be wrapped with ROM red colour codes
              `{R...{x` — the ANSI translation layer consumes them.
          (c) ROM uses two exclamation marks (`DEAD!!`), Python
              previously emitted three.
        """
        test_room = Room(vnum=1003, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1003] = test_room

        try:
            victim = create_test_character("Aliceee", 1003)
            victim.level = 5
            victim.add_affect(AffectFlag.INVISIBLE)
            victim.position = Position.DEAD

            observer = create_test_character("Bobbb", 1003)
            observer.level = 5
            observer.messages = []

            _position_change_message(victim, Position.STANDING)

            assert observer.messages, (
                f"POS_DEAD broadcast not delivered: {observer.messages!r}"
            )
            msg = observer.messages[-1]
            # (a) PERS render — invisible victim → "someone" (INV-027), then ROM
            # act_new's `{`-kludge caps buf[2] (the char after the {R colour
            # code) → "Someone" (FIGHT-031 / src/comm.c:2376-2379). The mask
            # still holds; only the first letter is upper-cased.
            assert "Someone is DEAD!!" in msg, (
                f"PERS render missing for invisible victim: {msg!r}"
            )
            assert "Aliceee" not in msg, (
                f"invisible victim name leaked: {msg!r}"
            )
            # (b) ROM red colour wrap.
            assert msg.startswith("{R") and msg.endswith("{x"), (
                f"missing ROM red colour codes {{R...{{x: {msg!r}"
            )
            # (c) Two exclamation marks, not three.
            assert "DEAD!!{x" in msg and "DEAD!!!" not in msg, (
                f"ROM wording is 'DEAD!!' (two bangs), Python emitted: {msg!r}"
            )

        finally:
            room_registry.pop(1003, None)
            character_registry.clear()

    def test_fight_008_pos_dead_self_message_wraps_red_and_appends_blank_line(self):
        """FIGHT-008 — POS_DEAD TO_CHAR self-message colour + spacing.

        ROM C: src/fight.c:861
            send_to_char ("{RYou have been KILLED!!{x\\n\\r\\n\\r", victim);

        Two divergences from Python's previous
        `return "You have been KILLED!!"`:
          (a) Missing ROM red colour codes `{R...{x` — the ANSI
              translation layer in `mud/net/ansi.py` consumes them.
          (b) Missing trailing blank-line newline. ROM appends two
              `\\n\\r` pairs, the second of which renders as a visual
              blank line after the death notice. Python's protocol
              layer auto-appends one `\\r\\n` to every message, so
              the Python return needs exactly one embedded trailing
              `\\n` for the auto-append to produce the blank line.
        """
        test_room = Room(vnum=1004, name="Test Room", description="A test room.", room_flags=0, sector_type=0)
        test_room.people = []
        test_room.contents = []
        room_registry[1004] = test_room

        try:
            victim = create_test_character("Aliceee", 1004)
            victim.level = 5
            victim.position = Position.DEAD
            victim.messages = []

            _push_msg = _position_change_message(victim, Position.STANDING)

            # Test path: function returns the self-message string;
            # caller in apply_damage delivers via _push_message.
            assert _push_msg, "POS_DEAD self-message should not be empty"
            assert _push_msg.startswith("{R"), (
                f"missing ROM red colour open code {{R: {_push_msg!r}"
            )
            assert "You have been KILLED!!" in _push_msg, (
                f"ROM-exact wording missing: {_push_msg!r}"
            )
            assert "{x" in _push_msg, (
                f"missing ROM red colour close code {{x: {_push_msg!r}"
            )
            # Trailing blank-line newline (the second of ROM's two
            # \\n\\r pairs — Python's protocol layer auto-appends the
            # first one as \\r\\n).
            assert _push_msg.endswith("\n"), (
                f"missing trailing \\n for ROM's blank-line spacing: {_push_msg!r}"
            )

        finally:
            room_registry.pop(1004, None)
            character_registry.clear()
