"""INV-029 — ACT-FIRST-LETTER-CAP.

ROM ``act_new`` upper-cases the first visible letter of *every* formatted
``act()`` line before delivery (``src/comm.c:2376-2379``), with a kludge for a
leading ``{`` colour code (``buf[0] == '{'`` → cap ``buf[2]``, else ``buf[0]``).
``UPPER`` (``src/merc.h``) flips ASCII ``a``–``z`` only.

The Python port renders act lines through two boundaries that this contract
locks:

1. ``mud/utils/act.py:act_format`` — the central act-line renderer (~113 call
   sites). Capping its return mirrors ROM's per-buffer cap in ``act_new``.
2. ``mud/commands/imm_commands.py`` ``pers()``-built f-strings (``do_force``
   TO_VICT ×4, ``do_transfer`` TO_VICT, ``_act_room`` TO_ROOM) — a second render
   path that does NOT route through ``act_format``.

This is the natural completion of INV-027 (ACT-PERS-NAME-MASKING): once a
masked ``$n`` renders as ``"someone"`` at a sentence start, ROM caps it to
``"Someone"``. The WIZ-047/048/049 masked-name assertions move in lockstep with
this contract (they previously asserted lowercase ``"someone"`` deliberately).

Cousins still uncapped and tracked under INV-029 (direct-f-string act sites that
bypass ``act_format``): ``do_say`` / ``do_tell`` (``mud/commands/communication.py``)
and the combat damage messages (``mud/combat/messages.py`` / ``engine.py``).
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.commands.imm_commands import do_force
from mud.models.character import character_registry
from mud.models.constants import AffectFlag, Sector
from mud.models.room import Room
from mud.registry import room_registry
from mud.utils.act import act_format, capitalize_act_line
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clean_state():
    original_rooms = set(room_registry)
    original_char_ids = {id(c) for c in character_registry}
    original_descriptor_list = getattr(global_registry, "descriptor_list", None)
    yield
    for vnum in list(room_registry):
        if vnum not in original_rooms:
            room_registry.pop(vnum, None)
    character_registry[:] = [c for c in character_registry if id(c) in original_char_ids]
    if original_descriptor_list is None:
        if hasattr(global_registry, "descriptor_list"):
            delattr(global_registry, "descriptor_list")
    else:
        global_registry.descriptor_list = original_descriptor_list


def _room(vnum: int, *, name: str | None = None) -> Room:
    room = Room(vnum=vnum, name=name or f"Room {vnum}", description=f"Room {vnum}")
    room.sector_type = int(Sector.INSIDE)  # never dark → only invisibility governs visibility
    room_registry[vnum] = room
    return room


def _imm(name: str, room_vnum: int, *, trust: int = 60):
    char = create_test_character(name, room_vnum)
    char.level = trust
    char.trust = trust
    if not hasattr(global_registry, "descriptor_list"):
        global_registry.descriptor_list = []
    return char


# ── capitalize_act_line helper — ROM act_new kludge (src/comm.c:2376-2379) ──


def test_capitalize_act_line_caps_plain_first_letter() -> None:
    assert capitalize_act_line("the door opens.") == "The door opens."


def test_capitalize_act_line_caps_after_colour_code() -> None:
    # buf[0] == '{' → cap buf[2] (the char after the 2-char {X colour code).
    assert capitalize_act_line("{ka rune glows.") == "{kA rune glows."


def test_capitalize_act_line_only_flips_ascii_lowercase() -> None:
    # UPPER flips a-z only; digits / already-capital first letters are untouched.
    assert capitalize_act_line("5 gold coins fall.") == "5 gold coins fall."
    assert capitalize_act_line("Already capitalized.") == "Already capitalized."


def test_capitalize_act_line_handles_empty_and_short() -> None:
    assert capitalize_act_line("") == ""
    # A bare 2-char colour code has no buf[2] to cap → returned unchanged.
    assert capitalize_act_line("{x") == "{x"


# ── act_format chokepoint (path 1) ──


def test_act_format_capitalizes_first_letter() -> None:
    ch = create_test_character("Watcher", 3001)
    assert act_format("the potion bubbles.", recipient=ch) == "The potion bubbles."


def test_act_format_capitalizes_masked_name_at_sentence_start() -> None:
    # INV-027 ↔ INV-029: an invisible actor's $n masks to "someone"; ROM then
    # caps the line's first letter → "Someone".
    room = _room(9300, name="Crypt")
    ghost = _imm("Spectre", room.vnum, trust=60)
    ghost.add_affect(AffectFlag.INVISIBLE)
    victim = _imm("Pawn", room.vnum, trust=5)  # no detect-invis → cannot see ghost

    rendered = act_format("$n bites you!", recipient=victim, actor=ghost)
    assert rendered == "Someone bites you!"


# ── imm_commands second render path (path 2) ──


def test_force_masked_immortal_name_is_capitalized() -> None:
    # mirrors ROM src/act_wiz.c:4205 act("$n forces you to '...'.", ch, NULL, vch,
    # TO_VICT); $n masks to "someone" for a non-seeing victim, then act_new caps
    # buf[0] → "Someone". (WIZ-049 + INV-029.)
    room = _room(9301, name="Dungeon")
    ghost = _imm("Tyrant", room.vnum, trust=60)
    ghost.add_affect(AffectFlag.INVISIBLE)
    victim = _imm("Serf", room.vnum, trust=5)  # no detect-invis → cannot see ghost
    victim.messages.clear()

    do_force(ghost, "Serf smile")

    assert any("Someone forces you to 'smile'." in m for m in victim.messages)
    assert not any("someone forces you to 'smile'." in m for m in victim.messages)
