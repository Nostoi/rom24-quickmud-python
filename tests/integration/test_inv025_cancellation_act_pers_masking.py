"""INV-025 enforcement — cancellation wear-off PERS masking.

ROM ``src/magic.c:1062-1196`` uses ``act("$n is no longer blinded.", victim, NULL, NULL, TO_ROOM)``
for every wear-off room line in ``spell_cancellation``.  ``act()`` renders ``$n``
through ``PERS(victim, to)`` per recipient, so an invisible victim appears as
"Someone" to witnesses who cannot see them.

The Python port previously baked ``_character_name(target)`` into the message
once and broadcast it via ``broadcast_room`` — leaking the invisible name to
every room occupant.  The fix routes each wear-off line through ``act_to_room``
(per-recipient ``act_format`` rendering + per-NPC TRIG_ACT dispatch), matching
the ROM ``act(TO_ROOM)`` contract.
"""

from __future__ import annotations

from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, Sector
from mud.models.room import Room
from mud.skills.handlers import cancellation


def _lit_room() -> Room:
    room = Room(
        vnum=42701,
        name="Cancellation Lab",
        description="A well-lit room for spell-cancellation tests.",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    room.contents = []
    return room


def _pc(name: str, room: Room, *, level: int = 30) -> Character:
    char = Character(name=name, level=level, room=room, is_npc=False)
    room.people.append(char)
    return char


def _mob(name: str, room: Room, *, level: int = 30) -> Character:
    char = Character(name=name, level=level, room=room, is_npc=True)
    room.people.append(char)
    return char


class TestCancellationPERSMasking:
    """An invisible cancellation target's wear-off messages must render
    per-recipient through PERS (can_see), not leak the real name."""

    def test_invisible_mob_blindness_wear_off_masks_name(self) -> None:
        room = _lit_room()
        caster = _pc("Dispelra", room, level=31)
        target = _mob("Verdana", room, level=30)
        target.add_affect(AffectFlag.INVISIBLE)

        onlooker = _pc("Bystan", room)

        target.apply_spell_effect(SpellEffect(name="blindness", duration=10, level=31, affect_flag=AffectFlag.BLIND))
        assert target.has_affect(AffectFlag.BLIND)

        cancellation(caster, target)

        assert not target.has_affect(AffectFlag.BLIND)

        onlooker_msgs = [str(m) for m in onlooker.messages]
        assert any("Someone is no longer blinded" in m for m in onlooker_msgs), (
            f"Expected PERS-masked wear-off for onlooker, got: {onlooker_msgs}"
        )

    def test_visible_mob_blindness_wear_off_shows_name(self) -> None:
        room = _lit_room()
        caster = _pc("Dispelra", room, level=31)
        target = _mob("Verdana", room, level=30)

        onlooker = _pc("Bystan", room)

        target.apply_spell_effect(SpellEffect(name="blindness", duration=10, level=31, affect_flag=AffectFlag.BLIND))

        cancellation(caster, target)

        onlooker_msgs = [str(m) for m in onlooker.messages]
        assert any("Verdana is no longer blinded" in m for m in onlooker_msgs), (
            f"Expected real-name wear-off for visible target, got: {onlooker_msgs}"
        )

    def test_invisible_mob_sanctuary_wear_off_masks_name(self) -> None:
        room = _lit_room()
        caster = _pc("Dispelra", room, level=31)
        target = _mob("Verdant", room, level=30)
        target.add_affect(AffectFlag.INVISIBLE)

        onlooker = _pc("Bystan", room)

        target.apply_spell_effect(
            SpellEffect(name="sanctuary", duration=10, level=31, affect_flag=AffectFlag.SANCTUARY)
        )

        cancellation(caster, target)

        onlooker_msgs = [str(m) for m in onlooker.messages]
        # $n is in mid-sentence, so PERS-masked "someone" is lowercase;
        # capitalize_act_line only caps the first letter of the whole line.
        assert any("around someone's body" in m for m in onlooker_msgs), (
            f"Expected PERS-masked sanctuary wear-off for onlooker, got: {onlooker_msgs}"
        )
