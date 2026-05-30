"""WIZ-047 — imm_commands._act_room per-recipient PERS name masking.

ROM ``do_transfer`` (``src/act_wiz.c:870,873``) announces the mushroom-cloud /
puff-of-smoke lines via ``act(..., TO_ROOM)``, so ``$n`` (the transferred
victim) is rendered per-recipient through ``PERS(victim, witness)`` →
``"someone"`` for any witness who cannot ``can_see`` the (invisible / wiz-invis)
subject. The line is still delivered to every witness; only the NAME is masked
(ROM masks, it does not suppress — contrast WIZ-045/046, which gate the whole
bamf line on ``invis_level`` via ``_act_room_invis_gated``).

This is the remaining half of the INV-027 (ACT-PERS-NAME-MASKING) contract — the
2.11.34 enforcement scoped its fix to ``mud/utils/act.py:act_format._pers`` and
explicitly left ``imm_commands._act_room`` untouched.

Cross-ref: ``docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`` INV-027 "Remaining".
"""

from __future__ import annotations

from mud.commands.imm_commands import _act_room
from mud.models.character import Character
from mud.models.constants import AffectFlag, Sector
from mud.models.room import Room


def _lit_room() -> Room:
    # sector INSIDE is never dark (mud/world/vision.py:room_is_dark), so the only
    # visibility variable is the invisible/detect-invis pairing.
    room = Room(
        vnum=42710,
        name="Lit Hall",
        description="A well-lit hall.",
        room_flags=0,
        sector_type=int(Sector.INSIDE),
    )
    room.people = []
    room.contents = []
    return room


def _char(name: str, room: Room) -> Character:
    char = Character(name=name, level=50, room=room, is_npc=False)
    room.people.append(char)
    return char


def test_act_room_masks_invisible_subject_name_for_nonseeing_witness() -> None:
    # mirrors ROM src/act_wiz.c:870,873 — do_transfer act(..., TO_ROOM) renders
    # $n via PERS(victim, witness): real name if can_see, else "someone".
    room = _lit_room()
    wraith = _char("Wraith", room)  # the transferred subject ($n)
    wraith.add_affect(AffectFlag.INVISIBLE)

    seer = _char("Seer", room)
    seer.add_affect(AffectFlag.DETECT_INVIS)  # can_see → real name
    blindspot = _char("Blindspot", room)  # no detect-invis → "someone"

    _act_room(room, wraith, "$n arrives from a puff of smoke.")

    # Delivery sink = char.messages mailbox (push_message appends to .messages
    # when the recipient has no `connection`). _act_room sends the string WITHOUT
    # a trailing \n\r, so substring-match.
    assert any("Wraith arrives from a puff of smoke." in m for m in seer.messages)
    # INV-029 (ACT-FIRST-LETTER-CAP, src/comm.c:2376-2379): ROM act_new caps the
    # rendered line's first letter, so the masked "someone" renders "Someone".
    assert any("Someone arrives from a puff of smoke." in m for m in blindspot.messages)
    # The subject never receives their own line (ROM act() TO_ROOM skips the actor).
    assert all("puff of smoke" not in m for m in wraith.messages)


def test_act_room_shows_real_name_to_all_when_subject_visible() -> None:
    # Regression guard: a fully-visible subject's name reaches every witness
    # exactly as before — PERS(visible, witness) returns the real name. ROM
    # src/act_wiz.c:870,873.
    room = _lit_room()
    mota = _char("Mota", room)  # no invisibility → can_see is true for all
    bystander = _char("Bystander", room)

    _act_room(room, mota, "$n disappears in a mushroom cloud.")

    assert any("Mota disappears in a mushroom cloud." in m for m in bystander.messages)
    assert all("mushroom cloud" not in m for m in mota.messages)
