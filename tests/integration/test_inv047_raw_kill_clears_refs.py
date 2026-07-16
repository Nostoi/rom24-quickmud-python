"""INV-047 (raw_kill leg) — combat NPC death must clear reply/mprog_target refs.

ROM `extract_char` (`src/handler.c:2151-2157`) walks `char_list` and nullifies
`wch->reply == ch` (dangling-pointer hygiene) plus the 2.4b6 `mprog_target`
quirk. Crucially, that sweep sits AFTER the `if (!fPull) return` early-out
(`src/handler.c:2136-2140`) — so it runs for **NPC/pull extraction only**
(`fPull=TRUE`); a PC death (`fPull=FALSE`) returns early and correctly skips it
(the PC stays live in `char_list`, moved to the clan hall).

`raw_kill` (`src/fight.c:1695-1723`) calls `extract_char(victim, IS_NPC(victim))`,
so a combat NPC death runs the sweep. The Python port split `extract_char`
across call sites and wired `clear_extract_target_refs` into `_extract_character`
(mob/purge), `_auto_quit_character` (link-dead quit), and
`_disconnect_extract_cleanup` (socket) — but NOT into `raw_kill`, the primary
combat-death funnel. So an NPC killed in combat while some character holds a
`reply` at it (a mob's `mob tell` sets the player's `reply`) — or while the mob
holds an `mprog_target` — leaves a dangling reference at the extracted corpse.

Same signature as the INV-020 pet-leg gap (2.14.316): a cleanup step the ROM
contract runs on a given extract leg, omitted because the Python port split the
single `extract_char` funnel. This pins the raw_kill NPC leg.
"""

from __future__ import annotations

import pytest

from mud.combat.death import raw_kill
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _isolated_registry():
    saved = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(saved)
    room_registry.pop(9832, None)


def _make_room(vnum: int = 9832) -> Room:
    room = Room(vnum=vnum, name="Combat Death Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_npc(name: str, room: Room) -> Character:
    ch = Character(name=name, is_npc=True, level=10, room=room, position=int(Position.STANDING))
    ch.messages = []
    ch.hit = 100
    ch.max_hit = 100
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def test_raw_kill_npc_clears_reply_pointer_at_victim():
    """ROM raw_kill(NPC) → extract_char(victim, TRUE) → reply sweep.

    A character whose ``reply`` points at the slain mob must have it nulled.
    """
    room = _make_room()
    victim = _make_npc("victim", room)
    teller = _make_npc("teller", room)

    teller.reply = victim  # e.g. victim did `mob tell teller ...`

    raw_kill(victim)

    assert victim not in character_registry, "raw_kill must extract the NPC victim"
    assert teller.reply is None, (
        "a reply pointer at a slain mob must be cleared "
        "(ROM raw_kill → extract_char(victim, TRUE) → char_list reply sweep, "
        f"src/handler.c:2151-2153); got a dangling reply: {teller.reply!r}"
    )


def test_raw_kill_npc_clears_mprog_target_quirk():
    """ROM raw_kill(NPC) → extract_char(victim, TRUE) → mprog_target quirk.

    The 2.4b6 quirk clears the OWN mprog_target of whoever the slain mob was
    targeting (``if (ch->mprog_target == wch) wch->mprog_target = NULL``).
    """
    room = _make_room()
    victim = _make_npc("victim", room)
    target = _make_npc("target", room)

    victim.mprog_target = target  # victim remembers target
    target.mprog_target = target  # target has its own remembered pointer

    raw_kill(victim)

    assert target.mprog_target is None, (
        "ROM raw_kill → extract_char(victim, TRUE) clears wch->mprog_target when "
        "ch->mprog_target == wch; slaying the victim (who targeted `target`) must "
        f"wipe target's remembered pointer; got {target.mprog_target!r}"
    )
