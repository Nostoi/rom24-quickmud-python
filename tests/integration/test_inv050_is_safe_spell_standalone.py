"""INV-050 gate — ``is_safe_spell`` must mirror ROM's STANDALONE function.

ROM ``is_safe_spell`` (``src/fight.c:1126-1218``) is NOT ``is_safe`` — it is a
separate function with its own check order and extra clauses (the immortal
bypass, the ``victim->fighting == ch`` retaliation bypass evaluated BEFORE the
NPC ROOM_SAFE check, area handling, the legal-kill ``is_same_group`` clauses,
and the full PC-vs-PC clan PK ladder).

The Python port's ``mud/combat/safety.py:is_safe_spell`` historically delegated
to the silent ``is_safe`` bool, which is bidirectionally divergent from ROM's
standalone ``is_safe_spell``. These tests pin the cases where the two diverge,
so ``do_cast``'s TAR_OBJ_CHAR_OFF branch (``src/magic.c:484``) gates correctly.
"""

from __future__ import annotations

import pytest

from mud.combat.safety import is_safe_spell
from mud.models.character import Character
from mud.models.constants import ActFlag, PlayerFlag, RoomFlag
from mud.world import create_test_character, initialize_world

_ROOM = 2300  # non-safe room in area.lst


@pytest.fixture(autouse=True)
def _world():
    initialize_world("area/area.lst")


def _make_pc(name: str) -> Character:
    ch = create_test_character(name, _ROOM)
    ch.is_npc = False
    ch.level = 20
    ch.act = 0
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    ch.clan = 0
    return ch


def _make_npc(name: str) -> Character:
    ch = create_test_character(name, _ROOM)
    ch.is_npc = True
    ch.level = 20
    ch.act = int(ActFlag.IS_NPC)
    ch.affected_by = 0
    ch.master = None
    ch.fighting = None
    return ch


# ── Retaliation bypass precedes NPC ROOM_SAFE ─────────────────────────────────


def test_inv050_npc_fighting_caster_in_safe_room_is_not_safe() -> None:
    # mirrors ROM src/fight.c:1134 — `victim->fighting == ch` → return FALSE,
    # evaluated BEFORE the NPC ROOM_SAFE check at :1144. The delegated is_safe
    # checks ROOM_SAFE first and would (wrongly) return True here.
    caster = _make_pc("Caster")
    victim = _make_npc("Aggressor")
    victim.fighting = caster
    victim.room.room_flags = int(getattr(victim.room, "room_flags", 0)) | int(RoomFlag.ROOM_SAFE)

    result = is_safe_spell(caster, victim, area=False)

    assert result is False, (
        f"is_safe_spell should return False (can retaliate) when the NPC victim is fighting "
        f"the caster, even in a SAFE room; got {result!r}. "
        "ROM src/fight.c:1134 checks victim->fighting == ch BEFORE the ROOM_SAFE branch (:1144)."
    )


# ── PC-vs-PC clan PK ladder (entirely missing from is_safe) ───────────────────


def test_inv050_pc_caster_not_in_clan_is_safe() -> None:
    # mirrors ROM src/fight.c:1205 — !is_clan(ch) → return TRUE. is_safe has NO
    # PC-vs-PC handling at all, so it would (wrongly) return False (allow).
    caster = _make_pc("Loner")
    victim = _make_pc("Target")

    result = is_safe_spell(caster, victim, area=False)

    assert result is True, (
        f"is_safe_spell should return True (blocked) when a non-clan PC casts on a PC; "
        f"got {result!r}. ROM src/fight.c:1205: !is_clan(ch) → return TRUE."
    )


def test_inv050_pc_caster_outlevels_clan_victim_is_safe() -> None:
    # mirrors ROM src/fight.c:1215 — ch->level > victim->level + 8 → return TRUE.
    caster = _make_pc("Bully")
    caster.clan = 1
    caster.level = 30
    victim = _make_pc("Weakling")
    victim.clan = 1
    victim.level = 10

    result = is_safe_spell(caster, victim, area=False)

    assert result is True, (
        f"is_safe_spell should return True (blocked, 'pick on someone your own size') when the "
        f"PC caster outlevels the clan victim by >8; got {result!r}. "
        "ROM src/fight.c:1215: ch->level > victim->level + 8 → return TRUE."
    )


def test_inv050_pc_caster_can_strike_clan_killer() -> None:
    # mirrors ROM src/fight.c:1208-1210 — PLR_KILLER/PLR_THIEF victim → return FALSE
    # (open season), evaluated before the !is_clan(victim) and level-gap clauses.
    caster = _make_pc("Avenger")
    caster.clan = 1
    caster.level = 30
    victim = _make_pc("Murderer")
    victim.act = int(PlayerFlag.KILLER)
    victim.level = 10  # would otherwise trip the level-gap clause at :1215

    result = is_safe_spell(caster, victim, area=False)

    assert result is False, (
        f"is_safe_spell should return False (open season) when a clan PC casts on a PLR_KILLER PC; "
        f"got {result!r}. ROM src/fight.c:1208: PLR_KILLER → return FALSE before the level gap."
    )
