from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud import registry as global_registry
from mud.commands.imm_admin import do_snoop
from mud.commands.imm_commands import do_goto
from mud.commands.imm_server import do_protect, do_violate
from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag, CommFlag
from mud.models.room import Room
from mud.registry import room_registry
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clean_act_wiz_state():
    original_rooms = set(room_registry)
    original_char_ids = {id(char) for char in character_registry}
    original_players = getattr(global_registry, "players", None)
    original_char_list = getattr(global_registry, "char_list", None)
    original_descriptor_list = getattr(global_registry, "descriptor_list", None)
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
    if original_char_list is None:
        if hasattr(global_registry, "char_list"):
            delattr(global_registry, "char_list")
    else:
        global_registry.char_list = original_char_list
    if original_descriptor_list is None:
        if hasattr(global_registry, "descriptor_list"):
            delattr(global_registry, "descriptor_list")
    else:
        global_registry.descriptor_list = original_descriptor_list


def _room(vnum: int, *, owner: str | None = None, room_flags: int = 0, name: str | None = None) -> Room:
    room = Room(vnum=vnum, name=name or f"Room {vnum}", description=f"Room {vnum}", owner=owner, room_flags=room_flags)
    room_registry[vnum] = room
    return room


def _imm(name: str, room_vnum: int, *, trust: int = 60):
    char = create_test_character(name, room_vnum)
    char.level = trust
    char.trust = trust
    players = getattr(global_registry, "players", None)
    if players is None:
        global_registry.players = {}
        players = global_registry.players
    players[char.name.lower()] = char

    char_list = getattr(global_registry, "char_list", None)
    if char_list is None:
        global_registry.char_list = []
        char_list = global_registry.char_list
    if char not in char_list:
        char_list.append(char)

    if not hasattr(global_registry, "descriptor_list"):
        global_registry.descriptor_list = []
    return char


def test_goto_denies_non_owner_into_owned_private_room() -> None:
    source = _room(9100, name="Source")
    target = _room(9101, owner="Keeper", name="Owner Room")
    intruder = _imm("Intruder", source.vnum, trust=52)
    _imm("Occupant", target.vnum, trust=10)

    result = do_goto(intruder, str(target.vnum))

    assert result == "That room is private right now."
    assert intruder.room is source


def test_violate_uses_room_lookup_and_rejects_non_private_rooms() -> None:
    source = _room(9110, name="Origin")
    private_room = _room(9111, owner="Keeper", name="Secret Study")
    public_room = _room(9112, name="Courtyard")
    immortal = _imm("Implementor", source.vnum, trust=60)

    result = do_violate(immortal, str(private_room.vnum))

    assert immortal.room is private_room
    assert "Secret Study" in result

    immortal.room.remove_character(immortal)
    source.add_character(immortal)

    public_result = do_violate(immortal, str(public_room.vnum))
    assert public_result == "That room isn't private, use goto.\n\r"
    assert immortal.room is source


def test_protect_sets_rom_snoop_proof_flag_and_message() -> None:
    room = _room(9120, name="Hall")
    admin = _imm("Admin", room.vnum, trust=59)
    victim = _imm("Victim", room.vnum, trust=10)

    result = do_protect(admin, "Victim")

    assert result == "Victim is now snoop-proof.\n\r"
    assert victim.has_comm_flag(CommFlag.SNOOP_PROOF)
    assert "You are now immune to snooping.\n\r" in getattr(victim, "output_buffer", [])


def test_snoop_honors_comm_snoop_proof_enum() -> None:
    room = _room(9130, name="Watch Room")
    snooper = _imm("Snooper", room.vnum, trust=59)
    victim = _imm("Target", room.vnum, trust=10)

    snooper.desc = SimpleNamespace()
    victim.desc = SimpleNamespace(snoop_by=None)
    victim.comm = int(CommFlag.SNOOP_PROOF)

    result = do_snoop(snooper, "Target")

    assert result == "You failed."
    assert victim.desc.snoop_by is None


# mirrors ROM src/act_wiz.c:2927-2982 (WIZ-006)


def test_log_toggles_plr_log_on_act_not_bool_field() -> None:
    # mirrors ROM src/act_wiz.c:2970-2978 — IS_SET/SET_BIT/REMOVE_BIT on PLR_LOG
    from mud.commands.admin_commands import cmd_log
    from mud.models.constants import PlayerFlag

    room = _room(9140, name="Log Room")
    admin = _imm("Admin", room.vnum, trust=60)
    victim = _imm("Victim", room.vnum, trust=10)

    victim.act = 0

    result_set = cmd_log(admin, "Victim")
    assert result_set == "LOG set.\n\r"
    assert victim.act & int(PlayerFlag.LOG), "PLR_LOG flag must be set on victim.act"

    result_removed = cmd_log(admin, "Victim")
    assert result_removed == "LOG removed.\n\r"
    assert not (victim.act & int(PlayerFlag.LOG)), "PLR_LOG flag must be cleared on victim.act"


def test_log_rejects_npc() -> None:
    # mirrors ROM src/act_wiz.c:2961-2964 — "Not on NPC's."
    from mud.commands.admin_commands import cmd_log

    room = _room(9141, name="NPC Room")
    admin = _imm("Admin", room.vnum, trust=60)
    npc = Character(name="guard", is_npc=True, level=10, room=room, hit=100, max_hit=100)
    npc.act = int(ActFlag.IS_NPC)
    room.people.append(npc)
    character_registry.append(npc)
    global_registry.char_list.append(npc)

    result = cmd_log(admin, "guard")
    assert result == "Not on NPC's.\n\r"

    character_registry.remove(npc)
    room.people.remove(npc)
    global_registry.char_list.remove(npc)


def test_log_all_toggles_global_flag() -> None:
    # mirrors ROM src/act_wiz.c:2940-2952 — fLogAll toggle
    from mud.admin_logging.admin import is_log_all_enabled, set_log_all
    from mud.commands.admin_commands import cmd_log

    room = _room(9142, name="AllRoom")
    admin = _imm("Admin", room.vnum, trust=60)

    set_log_all(False)
    assert not is_log_all_enabled()

    result_on = cmd_log(admin, "all")
    assert result_on == "Log ALL on.\n\r"
    assert is_log_all_enabled()

    result_off = cmd_log(admin, "all")
    assert result_off == "Log ALL off.\n\r"
    assert not is_log_all_enabled()


def test_log_empty_arg_and_not_found() -> None:
    # mirrors ROM src/act_wiz.c:2934-2938,2955-2958
    from mud.commands.admin_commands import cmd_log

    room = _room(9143, name="EmptyRoom")
    admin = _imm("Admin", room.vnum, trust=60)

    assert cmd_log(admin, "") == "Log whom?\n\r"
    assert cmd_log(admin, "Nonexistent") == "They aren't here.\n\r"


# mirrors ROM src/act_wiz.c:4183-4322 (WIZ-007)


def test_force_rejects_delete_and_mob_prefix() -> None:
    # mirrors ROM src/act_wiz.c:4197-4202
    from mud.commands.imm_commands import do_force

    room = _room(9150, name="ForceRoom")
    admin = _imm("Admin", room.vnum, trust=60)

    assert "NOT" in do_force(admin, "victim delete")
    assert "NOT" in do_force(admin, "victim mob kill")


def test_force_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:4191-4194
    from mud.commands.imm_commands import do_force

    room = _room(9151, name="ForceRoom")
    admin = _imm("Admin", room.vnum, trust=60)

    assert do_force(admin, "") == "Force whom to do what?\n\r"
    assert do_force(admin, "target") == "Force whom to do what?\n\r"


def test_force_self_returns_aye_aye() -> None:
    # mirrors ROM src/act_wiz.c:4289-4292
    from mud.commands.imm_commands import do_force

    room = _room(9152, name="ForceRoom")
    admin = _imm("Admin", room.vnum, trust=60)

    assert do_force(admin, "Admin look") == "Aye aye, right away!\n\r"


def test_force_gods_branch_rejects_low_trust() -> None:
    # mirrors ROM src/act_wiz.c:4258-4263
    from mud.commands.imm_commands import do_force

    room = _room(9153, name="ForceRoom")
    low_imm = _imm("Lowadmin", room.vnum, trust=57)

    result = do_force(low_imm, "gods look")
    assert result == "Not at your level!\n\r"


def test_force_private_room_blocks_non_owner() -> None:
    # mirrors ROM src/act_wiz.c:4295-4301
    from mud.commands.imm_commands import do_force
    from mud.models.constants import RoomFlag

    source = _room(9154, name="Source")
    private_room = _room(9155, name="PrivateRoom", room_flags=int(RoomFlag.ROOM_PRIVATE))
    private_room.owner = "OwnerName"
    admin = _imm("Admin", source.vnum, trust=57)
    _imm("Victim", private_room.vnum, trust=10)

    result = do_force(admin, "Victim look")
    assert result == "That character is in a private room.\n\r"


def test_force_single_target_trust_check() -> None:
    # mirrors ROM src/act_wiz.c:4304-4307 — get_trust(victim) >= get_trust(ch)
    from mud.commands.imm_commands import do_force

    room = _room(9156, name="ForceRoom")
    low_imm = _imm("Lowadmin", room.vnum, trust=53)
    _imm("Highadmin", room.vnum, trust=55)

    result = do_force(low_imm, "Highadmin look")
    assert result == "Do it yourself!\n\r"


def test_force_returns_ok_after_single_force() -> None:
    # mirrors ROM src/act_wiz.c:4320
    from mud.commands.imm_commands import do_force

    room = _room(9157, name="ForceRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    _imm("Victim", room.vnum, trust=10)

    result = do_force(admin, "Victim look")
    assert result == "Ok.\n\r"
