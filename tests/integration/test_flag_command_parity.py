"""Integration tests for the immortal `flag` command (`do_flag`).

Mirrors ROM `src/flags.c:do_flag` (lines 44-251). The Python entry point
lives at `mud/commands/remaining_rom.py:do_flag`.
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.commands.remaining_rom import do_flag
from mud.models.character import character_registry
from mud.models.constants import (
    AffectFlag,
    CommFlag,
    ImmFlag,
    PlayerFlag,
)
from mud.models.room import Room
from mud.registry import room_registry
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clean_flag_state():
    original_rooms = set(room_registry)
    original_char_ids = {id(char) for char in character_registry}
    original_players = getattr(global_registry, "players", None)
    yield
    for vnum in list(room_registry):
        if vnum not in original_rooms:
            room_registry.pop(vnum, None)
    character_registry[:] = [char for char in character_registry if id(char) in original_char_ids]
    if original_players is None:
        if hasattr(global_registry, "players"):
            delattr(global_registry, "players")
    else:
        global_registry.players = original_players


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description=f"Room {vnum}")
    room_registry[vnum] = room
    return room


def _imm(name: str, room_vnum: int):
    char = create_test_character(name, room_vnum)
    char.level = 60
    char.trust = 60
    players = getattr(global_registry, "players", None)
    if players is None:
        global_registry.players = {}
        players = global_registry.players
    players[char.name] = char
    return char


def _pc(name: str, room_vnum: int):
    char = create_test_character(name, room_vnum)
    players = getattr(global_registry, "players", None)
    if players is None:
        global_registry.players = {}
        players = global_registry.players
    players[char.name] = char
    return char


def test_flag_char_plr_add_sets_player_flag_bit():
    # mirrors ROM src/flags.c:117-127, 229-244 — `flag char <name> plr +holylight`
    # resolves the plr_flags table and ORs PLR_HOLYLIGHT onto victim->act.
    _room(3001)
    immortal = _imm("Imp", 3001)
    victim = _pc("Bob", 3001)
    victim.act = 0

    do_flag(immortal, "char Bob plr +holylight")

    assert victim.act & int(PlayerFlag.HOLYLIGHT), (
        f"Expected HOLYLIGHT bit set on victim.act after `+holylight`; got {victim.act:#x}"
    )


def test_flag_char_plr_remove_clears_player_flag_bit():
    # mirrors ROM src/flags.c:237-239 — `-holylight` REMOVE_BIT branch
    _room(3001)
    immortal = _imm("Imp", 3001)
    victim = _pc("Bob", 3001)
    victim.act = int(PlayerFlag.HOLYLIGHT) | int(PlayerFlag.AUTOLOOT)

    do_flag(immortal, "char Bob plr -holylight")

    assert not (victim.act & int(PlayerFlag.HOLYLIGHT))
    assert victim.act & int(PlayerFlag.AUTOLOOT), "AUTOLOOT must remain set"


def test_flag_char_plr_toggle_default_inverts_bit():
    # mirrors ROM src/flags.c:240-244 — implicit toggle (no operator)
    _room(3001)
    immortal = _imm("Imp", 3001)
    victim = _pc("Bob", 3001)
    victim.act = 0

    do_flag(immortal, "char Bob plr holylight")
    assert victim.act & int(PlayerFlag.HOLYLIGHT)

    do_flag(immortal, "char Bob plr holylight")
    assert not (victim.act & int(PlayerFlag.HOLYLIGHT))


def test_flag_char_plr_set_equals_replaces_field():
    # mirrors ROM src/flags.c:198-199, 233-236 — `=` operator: new = 0 then SET marked bits.
    _room(3001)
    immortal = _imm("Imp", 3001)
    victim = _pc("Bob", 3001)
    victim.act = int(PlayerFlag.HOLYLIGHT) | int(PlayerFlag.AUTOLOOT)

    do_flag(immortal, "char Bob plr =autosac")

    assert victim.act & int(PlayerFlag.AUTOSAC)
    assert not (victim.act & int(PlayerFlag.HOLYLIGHT)), "HOLYLIGHT must be cleared by `=`"
    assert not (victim.act & int(PlayerFlag.AUTOLOOT)), "AUTOLOOT must be cleared by `=`"


def test_flag_char_aff_targets_affected_by():
    # mirrors ROM src/flags.c:129-133 — aff field maps to victim->affected_by
    _room(3001)
    immortal = _imm("Imp", 3001)
    victim = _pc("Bob", 3001)
    victim.affected_by = 0

    do_flag(immortal, "char Bob aff +sanctuary")

    assert victim.affected_by & int(AffectFlag.SANCTUARY)


def test_flag_char_immunity_targets_imm_flags():
    # mirrors ROM src/flags.c:135-139 — immunity field maps to victim->imm_flags
    _room(3001)
    immortal = _imm("Imp", 3001)
    victim = _pc("Bob", 3001)
    victim.imm_flags = 0

    do_flag(immortal, "char Bob immunity +fire")

    assert victim.imm_flags & int(ImmFlag.FIRE)


def test_flag_char_comm_targets_comm():
    # mirrors ROM src/flags.c:177-187 — comm field maps to victim->comm
    _room(3001)
    immortal = _imm("Imp", 3001)
    victim = _pc("Bob", 3001)
    victim.comm = 0

    do_flag(immortal, "char Bob comm +deaf")

    assert victim.comm & int(CommFlag.DEAF)


def test_flag_unknown_field_rejected():
    # mirrors ROM src/flags.c:189-193 — unknown field → "That's not an acceptable flag."
    _room(3001)
    immortal = _imm("Imp", 3001)
    _pc("Bob", 3001)

    out = do_flag(immortal, "char Bob bogus +holylight")

    assert "not an acceptable flag" in out.lower()


def test_flag_prefix_match_accepts_abbreviation():
    # mirrors ROM src/lookup.c:39-51 — flag_lookup uses str_prefix; ROM accepts
    # `+holy` as a prefix of `HOLYLIGHT`. Closes LOOKUP-002 in FLAGS_C_AUDIT.md.
    _room(3001)
    immortal = _imm("Imp", 3001)
    victim = _pc("Bob", 3001)
    victim.act = 0

    do_flag(immortal, "char Bob plr +holy")

    assert victim.act & int(PlayerFlag.HOLYLIGHT), (
        "ROM accepts `holy` as a prefix abbreviation of HOLYLIGHT; "
        "Python must use prefix-match, not exact-match."
    )


def test_flag_unknown_flag_name_rejected():
    # mirrors ROM src/flags.c:211-214 — "That flag doesn't exist!"
    _room(3001)
    immortal = _imm("Imp", 3001)
    victim = _pc("Bob", 3001)
    victim.act = 0

    out = do_flag(immortal, "char Bob plr +nonsense_flag_xyz")

    assert "doesn't exist" in out.lower()
    assert victim.act == 0, "victim.act must not change when an unknown flag name is supplied"
