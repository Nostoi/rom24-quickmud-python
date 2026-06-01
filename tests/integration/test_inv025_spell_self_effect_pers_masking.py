"""INV-025 / INV-027 — single-actor spell-effect PERS masking + invis broadcast order.

Two related contracts are covered here:

1. **PERS masking sweep.** ROM routes single-actor spell-effect room lines
   through ``act("$n ...", ch, NULL, NULL, TO_ROOM)`` (e.g. ``spell_infravision``
   ``src/magic.c:3598``).  ``act()`` renders ``$n`` through ``PERS(ch, to)`` per
   recipient, so an invisible actor appears as "someone" to witnesses who cannot
   see them.  The Python port baked ``_character_name(actor)`` into the message
   once and broadcast it via ``broadcast_room``, leaking the name; the fix routes
   each line through the shared ``act_to_room`` helper (per-recipient
   ``act_format`` PERS masking + per-NPC TRIG_ACT dispatch).

2. **invis / mass_invis broadcast order.** ROM ``spell_invisibility``
   (``src/magic.c:3650-3659``) and ``spell_mass_invis`` (``:3837-3847``) emit the
   ``"$n fades out of existence."`` room line *before* applying ``AFF_INVISIBLE``,
   so the actor is still visible at broadcast time and witnesses see the real
   name (per-recipient PERS).  The Python ``invis`` handler applied the affect
   first, then broadcast — harmless while the name was baked in, but once the
   line renders through per-recipient PERS it would wrongly mask the visible
   actor to "someone".  The handler now broadcasts before ``apply_spell_effect``,
   matching ROM.  ``mass_invis`` already broadcast first.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, Sector
from mud.models.room import Room
from mud.skills.handlers import infravision, invis, mass_invis


def _lit_room() -> Room:
    room = Room(
        vnum=42801,
        name="Spell Self-Effect Lab",
        description="A well-lit room for spell self-effect PERS tests.",
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


class TestSpellSelfEffectPERSMasking:
    """A genuinely-invisible spell actor's room line must render per-recipient
    through PERS (can_see), not leak the real name."""

    # NOTE: infravision is exercised SELF-CAST here. ROM `act("$n's eyes glow
    # red.", ch, TO_ROOM)` (src/magic.c:3598) uses the CASTER (`ch`) as the `$n`
    # actor, but the Python handler passes the target — a divergence that only
    # manifests when caster != target (filed as MAGIC-009). Self-casting makes
    # `$n` == caster == target under both ROM and Python, so the masking
    # assertion is unambiguously ROM-faithful.

    def test_infravision_masks_invisible_caster_name(self) -> None:
        room = _lit_room()
        caster = _pc("Verdana", room, level=31)
        caster.add_affect(AffectFlag.INVISIBLE)
        onlooker = _pc("Bystan", room)

        assert infravision(caster) is True

        onlooker_msgs = [str(m) for m in onlooker.messages]
        assert any("Someone's eyes glow red" in m for m in onlooker_msgs), (
            f"Expected PERS-masked infravision line for onlooker, got: {onlooker_msgs}"
        )
        assert not any("Verdana's eyes glow red" in m for m in onlooker_msgs), (
            f"Invisible caster's name leaked to onlooker: {onlooker_msgs}"
        )

    def test_infravision_shows_visible_caster_name(self) -> None:
        room = _lit_room()
        caster = _pc("Verdana", room, level=31)
        onlooker = _pc("Bystan", room)

        assert infravision(caster) is True

        onlooker_msgs = [str(m) for m in onlooker.messages]
        assert any("Verdana's eyes glow red" in m for m in onlooker_msgs), (
            f"Expected real name for visible caster, got: {onlooker_msgs}"
        )


class TestInvisBroadcastOrder:
    """ROM emits the fade-out room line before applying AFF_INVISIBLE, so the
    actor is still visible and witnesses see the real name."""

    def test_invis_broadcasts_name_before_applying_invisible(self) -> None:
        room = _lit_room()
        caster = _pc("Mystra", room, level=31)
        target = _pc("Verdana", room, level=30)
        onlooker = _pc("Bystan", room)

        assert invis(caster, target) is True
        assert target.has_affect(AffectFlag.INVISIBLE)

        onlooker_msgs = [str(m) for m in onlooker.messages]
        assert any("Verdana fades out of existence" in m for m in onlooker_msgs), (
            f"Expected real name (broadcast precedes affect) for onlooker, got: {onlooker_msgs}"
        )
        assert not any("Someone fades out of existence" in m for m in onlooker_msgs), (
            f"Broadcast ran after AFF_INVISIBLE was applied (wrong order): {onlooker_msgs}"
        )

    def test_mass_invis_broadcasts_member_name_before_applying_invisible(self) -> None:
        room = _lit_room()
        caster = _pc("Oracle", room, level=31)
        caster.leader = caster
        ally = _pc("Scout", room, level=28)
        ally.leader = caster
        onlooker = _pc("Bystan", room)

        assert mass_invis(caster) is True
        assert ally.has_affect(AffectFlag.INVISIBLE)

        onlooker_msgs = [str(m) for m in onlooker.messages]
        assert any("Scout slowly fades out of existence" in m for m in onlooker_msgs), (
            f"Expected real member name (broadcast precedes affect), got: {onlooker_msgs}"
        )
