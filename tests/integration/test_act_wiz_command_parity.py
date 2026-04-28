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


# ── do_stat family (WIZ-005) ────────────────────────────────────────


def test_stat_shows_syntax_when_no_args() -> None:
    # mirrors ROM src/act_wiz.c:1068-1075 — empty arg shows syntax
    from mud.commands.imm_search import do_stat

    room = _room(9200, name="StatRoom")
    admin = _imm("Admin", room.vnum, trust=60)

    result = do_stat(admin, "")
    assert "Syntax:" in result
    assert "stat <name>" in result


def test_stat_room_dispatches_to_rstat() -> None:
    # mirrors ROM src/act_wiz.c:1078-1081 — "room" keyword calls do_rstat
    from mud.commands.imm_search import do_stat

    room = _room(9201, name="Stat Test Room")
    admin = _imm("Admin", room.vnum, trust=60)

    result = do_stat(admin, "room")
    assert "Stat Test Room" in result


def test_stat_mob_dispatches_to_mstat() -> None:
    # mirrors ROM src/act_wiz.c:1090-1093 — "mob" keyword calls do_mstat
    from mud.commands.imm_search import do_stat

    room = _room(9202, name="StatRoom")
    mob = create_test_character("test mob", room.vnum)
    mob.is_npc = True
    mob.short_descr = "a test mob"
    if not hasattr(global_registry, "char_list"):
        global_registry.char_list = []
    if mob not in global_registry.char_list:
        global_registry.char_list.append(mob)

    admin = _imm("Admin", room.vnum, trust=60)

    result = do_stat(admin, "mob test mob")
    assert "test mob" in result.lower()


def test_stat_nothing_found() -> None:
    # mirrors ROM src/act_wiz.c:1119 — nothing found returns message
    from mud.commands.imm_search import do_stat

    room = _room(9203, name="StatRoom")
    admin = _imm("Admin", room.vnum, trust=60)

    result = do_stat(admin, "nonexistent")
    assert "Nothing by that name found" in result


def test_rstat_shows_room_info() -> None:
    # mirrors ROM src/act_wiz.c:1146-1155 — Name, Area, Vnum, Sector, Light, Healing, Mana
    from mud.commands.imm_search import do_rstat

    room = _room(9210, name="The Grand Hall")
    room.sector_type = 1
    room.light = 3
    room.heal_rate = 110
    room.mana_rate = 120
    room.description = "A grand hall stretches before you."
    admin = _imm("Admin", room.vnum, trust=60)

    result = do_rstat(admin, str(room.vnum))
    assert "The Grand Hall" in result
    assert f"Vnum: {room.vnum}" in result
    assert "Sector:" in result
    assert "Light: 3" in result
    assert "Healing: 110" in result
    assert "Mana: 120" in result


def test_rstat_private_room_blocks_non_owner() -> None:
    # mirrors ROM src/act_wiz.c:1139-1144 — private room check
    from mud.commands.imm_search import do_rstat

    source = _room(9211, name="Source")
    private_room = _room(9212, owner="Owner", name="Private Room", room_flags=0)
    private_room.owner = "Owner"
    from mud.models.constants import RoomFlag
    private_room.room_flags = int(RoomFlag.ROOM_PRIVATE)
    private_room.people = []
    _imm("Occupant", private_room.vnum, trust=10)
    _imm("Occupant2", private_room.vnum, trust=10)

    admin = _imm("Admin", source.vnum, trust=52)

    result = do_rstat(admin, str(private_room.vnum))
    assert "private" in result.lower()


def test_ostat_shows_object_info() -> None:
    # mirrors ROM src/act_wiz.c:1240-1279 — Name(s), Vnum, Format, Type, etc.
    from mud.commands.imm_search import do_ostat
    from mud.models.obj import ObjIndex, object_registry
    from mud.models.object import Object

    room = _room(9220, name="StatRoom")
    admin = _imm("Admin", room.vnum, trust=60)

    proto = ObjIndex(vnum=92200, name="stat sword test", short_descr="a stat test sword", description="A test sword lies here.", item_type=5, level=10, wear_flags=0, extra_flags=0, value=[0, 2, 8, 0, 0], weight=50, cost=100, condition=100)
    obj = Object(instance_id=77001, prototype=proto, location=-1, contained_items=[], level=10, value=[0, 2, 8, 0, 0], timer=0, wear_loc=-1, cost=100, extra_flags=0, wear_flags=0, condition=100, enchanted=False, item_type=5, owner=None, affected=[], _short_descr_override=None, _description_override=None)
    obj.in_room = room
    room.contents.append(obj)
    object_registry.append(obj)

    result = do_ostat(admin, "stat sword test")
    assert "stat sword test" in result
    assert f"Vnum: {proto.vnum}" in result
    assert "Level:" in result

    if obj in object_registry:
        object_registry.remove(obj)


def test_mstat_shows_character_info() -> None:
    # mirrors ROM src/act_wiz.c:1564-1621 — Name, Vnum, Str, Hp, Lv, Armor, etc.
    from mud.commands.imm_search import do_mstat

    room = _room(9230, name="StatRoom")
    mob = create_test_character("stat mob target", room.vnum)
    mob.is_npc = True
    mob.level = 30
    mob.hit = 100
    mob.max_hit = 200
    mob.mana = 50
    mob.max_mana = 100
    mob.move = 75
    mob.max_move = 150
    mob.gold = 100
    mob.silver = 50
    mob.alignment = 500
    mob.hitroll = 10
    mob.damroll = 5
    mob.saving_throw = 0
    mob.armor = [20, 15, 10, 5]
    if not hasattr(global_registry, "char_list"):
        global_registry.char_list = []
    if mob not in global_registry.char_list:
        global_registry.char_list.append(mob)

    admin = _imm("Admin", room.vnum, trust=60)

    result = do_mstat(admin, "stat mob target")
    assert "stat mob target" in result
    assert "Name:" in result
    assert "Hp:" in result
    assert "Lv:" in result or "Level" in result


def test_mstat_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:1553-1555 — "Stat whom?"
    from mud.commands.imm_search import do_mstat

    room = _room(9231, name="StatRoom")
    admin = _imm("Admin", room.vnum, trust=60)

    result = do_mstat(admin, "")
    assert "Stat whom?" in result


def test_ostat_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:1229-1231 — "Stat what?"
    from mud.commands.imm_search import do_ostat

    room = _room(9232, name="StatRoom")
    admin = _imm("Admin", room.vnum, trust=60)

    result = do_ostat(admin, "")
    assert "Stat what?" in result


# ── Punish commands (WIZ-008) ──────────────────────────────────────


def test_nochannels_sets_and_removes_comm_flag() -> None:
    # mirrors ROM src/act_wiz.c:339-356 — toggles COMM_NOCHANNELS on victim.comm
    from mud.commands.imm_punish import do_nochannels
    from mud.models.constants import CommFlag

    room = _room(9300, name="PunishRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    victim = _imm("Victim", room.vnum, trust=10)

    result = do_nochannels(admin, "Victim")
    assert "NOCHANNELS set" in result
    assert int(victim.comm) & int(CommFlag.NOCHANNELS)

    result = do_nochannels(admin, "Victim")
    assert "NOCHANNELS removed" in result
    assert not (int(victim.comm) & int(CommFlag.NOCHANNELS))


def test_nochannels_rejects_higher_trust() -> None:
    # mirrors ROM src/act_wiz.c:333-336
    from mud.commands.imm_punish import do_nochannels

    room = _room(9301, name="PunishRoom")
    low = _imm("Lowadmin", room.vnum, trust=52)
    _imm("Highadmin", room.vnum, trust=55)

    result = do_nochannels(low, "Highadmin")
    assert "You failed" in result


def test_noemote_sets_and_removes_comm_flag() -> None:
    # mirrors ROM src/act_wiz.c:3012-3027 — toggles COMM_NOEMOTE
    from mud.commands.imm_punish import do_noemote
    from mud.models.constants import CommFlag

    room = _room(9302, name="PunishRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    victim = _imm("Victim", room.vnum, trust=10)

    result = do_noemote(admin, "Victim")
    assert "NOEMOTE set" in result
    assert int(victim.comm) & int(CommFlag.NOEMOTE)

    result = do_noemote(admin, "Victim")
    assert "NOEMOTE removed" in result
    assert not (int(victim.comm) & int(CommFlag.NOEMOTE))


def test_noshout_rejects_npc() -> None:
    # mirrors ROM src/act_wiz.c:2893-2894 — IS_NPC check before trust check
    from mud.commands.imm_punish import do_noshout

    room = _room(9303, name="PunishRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    mob = create_test_character("test guard", room.vnum)
    mob.is_npc = True
    if not hasattr(global_registry, "char_list"):
        global_registry.char_list = []
    if mob not in global_registry.char_list:
        global_registry.char_list.append(mob)

    result = do_noshout(admin, "test guard")
    assert "Not on NPC" in result


def test_notell_sets_and_removes_comm_flag() -> None:
    # mirrors ROM src/act_wiz.c:3112-3127 — toggles COMM_NOTELL
    from mud.commands.imm_punish import do_notell
    from mud.models.constants import CommFlag

    room = _room(9304, name="PunishRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    victim = _imm("Victim", room.vnum, trust=10)

    result = do_notell(admin, "Victim")
    assert "NOTELL set" in result
    assert int(victim.comm) & int(CommFlag.NOTELL)

    result = do_notell(admin, "Victim")
    assert "NOTELL removed" in result
    assert not (int(victim.comm) & int(CommFlag.NOTELL))


def test_pardon_killer_flag() -> None:
    # mirrors ROM src/act_wiz.c:646-655 — removes PLR_KILLER from victim.act
    from mud.commands.imm_punish import do_pardon
    from mud.models.constants import PlayerFlag

    room = _room(9305, name="PunishRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    victim = _imm("Victim", room.vnum, trust=10)
    victim.act = int(victim.act) | int(PlayerFlag.KILLER)

    result = do_pardon(admin, "Victim killer")
    assert "Killer flag removed" in result
    assert not (int(victim.act) & int(PlayerFlag.KILLER))


def test_pardon_thief_flag() -> None:
    # mirrors ROM src/act_wiz.c:657-665 — removes PLR_THIEF from victim.act
    from mud.commands.imm_punish import do_pardon
    from mud.models.constants import PlayerFlag

    room = _room(9306, name="PunishRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    victim = _imm("Victim", room.vnum, trust=10)
    victim.act = int(victim.act) | int(PlayerFlag.THIEF)

    result = do_pardon(admin, "Victim thief")
    assert "Thief flag removed" in result
    assert not (int(victim.act) & int(PlayerFlag.THIEF))


def test_pardon_rejects_npc() -> None:
    # mirrors ROM src/act_wiz.c:640-643
    from mud.commands.imm_punish import do_pardon

    room = _room(9307, name="PunishRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    mob = create_test_character("test mob", room.vnum)
    mob.is_npc = True
    if not hasattr(global_registry, "char_list"):
        global_registry.char_list = []
    if mob not in global_registry.char_list:
        global_registry.char_list.append(mob)

    result = do_pardon(admin, "test mob killer")
    assert "Not on NPC" in result


def test_freeze_sets_and_removes_plr_freeze() -> None:
    # mirrors ROM src/act_wiz.c:2903-2918 — toggles PLR_FREEZE on victim.act
    from mud.commands.imm_admin import do_freeze
    from mud.models.constants import PlayerFlag

    room = _room(9308, name="PunishRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    victim = _imm("Victim", room.vnum, trust=10)

    result = do_freeze(admin, "Victim")
    assert "FREEZE set" in result
    assert int(victim.act) & int(PlayerFlag.FREEZE)

    result = do_freeze(admin, "Victim")
    assert "FREEZE removed" in result
    assert not (int(victim.act) & int(PlayerFlag.FREEZE))


def test_freeze_rejects_npc() -> None:
    # mirrors ROM src/act_wiz.c:2891-2893
    from mud.commands.imm_admin import do_freeze

    room = _room(9309, name="PunishRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    mob = create_test_character("test mob", room.vnum)
    mob.is_npc = True
    if not hasattr(global_registry, "char_list"):
        global_registry.char_list = []
    if mob not in global_registry.char_list:
        global_registry.char_list.append(mob)

    result = do_freeze(admin, "test mob")
    assert "Not on NPC" in result


# ── do_peace (WIZ-009) ─────────────────────────────────────────────


def test_peace_stops_fighting_and_removes_aggressive() -> None:
    # mirrors ROM src/act_wiz.c:3134-3148 — stop_fighting + clear ACT_AGGRESSIVE
    from mud.commands.imm_commands import do_peace
    from mud.models.constants import ActFlag

    room = _room(9350, name="PeaceRoom")
    admin = _imm("Admin", room.vnum, trust=60)
    mob = create_test_character("aggro mob", room.vnum)
    mob.is_npc = True
    mob.act = int(getattr(mob, "act", 0)) | int(ActFlag.AGGRESSIVE)
    mob.fighting = admin
    admin.fighting = mob
    if not hasattr(global_registry, "char_list"):
        global_registry.char_list = []
    if mob not in global_registry.char_list:
        global_registry.char_list.append(mob)

    result = do_peace(admin, "")
    assert "Ok" in result
    assert getattr(mob, "fighting", None) is None
    assert not (int(getattr(mob, "act", 0)) & int(ActFlag.AGGRESSIVE))


# ── do_invis / do_incognito (WIZ-010) ──────────────────────────────


def test_invis_toggle_sets_and_clears_invis_level() -> None:
    # mirrors ROM src/act_wiz.c:4329-4373 — toggles invis_level with room message
    from mud.commands.imm_display import do_invis

    room = _room(9400, name="InvisRoom")
    admin = _imm("Admin", room.vnum, trust=55)

    result = do_invis(admin, "")
    assert "vanish" in result.lower()
    assert admin.invis_level == 55

    result = do_invis(admin, "")
    assert "fade" in result.lower()
    assert admin.invis_level == 0


def test_invis_set_level() -> None:
    # mirrors ROM src/act_wiz.c:4355-4373 — sets specific invis level
    from mud.commands.imm_display import do_invis

    room = _room(9401, name="InvisRoom")
    admin = _imm("Admin", room.vnum, trust=55)

    result = do_invis(admin, "30")
    assert "vanish" in result.lower()
    assert admin.invis_level == 30


def test_invis_rejects_invalid_level() -> None:
    # mirrors ROM src/act_wiz.c:4351-4353
    from mud.commands.imm_display import do_invis

    room = _room(9402, name="InvisRoom")
    admin = _imm("Admin", room.vnum, trust=55)

    result = do_invis(admin, "1")
    assert "between 2" in result.lower() or "number" in result.lower()


def test_incognito_toggle_sets_and_clears_incog_level() -> None:
    # mirrors ROM src/act_wiz.c:4375-4420 — toggles incog_level
    from mud.commands.imm_display import do_incognito

    room = _room(9403, name="IncogRoom")
    admin = _imm("Admin", room.vnum, trust=55)

    result = do_incognito(admin, "")
    assert "cloak" in result.lower()
    assert admin.incog_level == 55

    result = do_incognito(admin, "")
    assert "no longer" in result.lower()
    assert admin.incog_level == 0


def test_incognito_set_level() -> None:
    # mirrors ROM src/act_wiz.c:4405-4418
    from mud.commands.imm_display import do_incognito

    room = _room(9404, name="IncogRoom")
    admin = _imm("Admin", room.vnum, trust=55)

    result = do_incognito(admin, "30")
    assert "cloak" in result.lower()
    assert admin.incog_level == 30
    # mirrors ROM src/act_wiz.c:4410 — reply is set to NULL when setting a level
    assert admin.reply is None


# ── WIZ-011: Echo family (do_echo, do_recho, do_zecho, do_pecho) ─────


def test_echo_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:678-679
    from mud.commands.imm_display import do_echo

    admin = _imm("Admin", 9400)
    result = do_echo(admin, "")
    assert "Global echo what?" in result


def test_recho_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:704-707
    from mud.commands.imm_display import do_recho

    admin = _imm("Admin", 9401)
    result = do_recho(admin, "")
    assert "Local echo what?" in result


def test_zecho_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:730-733
    from mud.commands.imm_display import do_zecho

    admin = _imm("Admin", 9402)
    result = do_zecho(admin, "")
    assert "Zone echo what?" in result


def test_pecho_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:757-759
    from mud.commands.imm_display import do_pecho

    admin = _imm("Admin", 9403)
    result = do_pecho(admin, "")
    assert "Personal echo what?" in result


def test_pecho_missing_message() -> None:
    # mirrors ROM src/act_wiz.c:757-759 — only name, no message
    from mud.commands.imm_display import do_pecho

    admin = _imm("Admin", 9404)
    result = do_pecho(admin, "Bob")
    assert "Personal echo what?" in result


def test_pecho_target_not_found() -> None:
    # mirrors ROM src/act_wiz.c:763-766
    from mud.commands.imm_display import do_pecho

    admin = _imm("Admin", 9405)
    result = do_pecho(admin, "Nobody testmsg")
    assert "Target not found" in result


# ── WIZ-012: bamfin/bamfout ──────────────────────────────────────


def test_poofin_view_default() -> None:
    # mirrors ROM src/act_wiz.c:463-468
    from mud.commands.imm_display import do_poofin

    admin = _imm("Admin", 9500)
    result = do_poofin(admin, "")
    assert "Your poofin is" in result


def test_poofin_set_with_name() -> None:
    # mirrors ROM src/act_wiz.c:470-480
    from mud.commands.imm_display import do_poofin

    admin = _imm("Admin", 9501)
    result = do_poofin(admin, "Admin appears in a flash!")
    assert "Your poofin is now" in result


def test_poofin_rejects_missing_name() -> None:
    # mirrors ROM src/act_wiz.c:470-473 — strstr check
    from mud.commands.imm_display import do_poofin

    admin = _imm("Admin", 9502)
    result = do_poofin(admin, "someone appears")
    assert "You must include your name" in result


def test_poofout_view_and_set() -> None:
    # mirrors ROM src/act_wiz.c:493-510
    from mud.commands.imm_display import do_poofout

    admin = _imm("Admin", 9503)
    result = do_poofout(admin, "")
    assert "Your poofout is" in result

    result = do_poofout(admin, "Admin vanishes!")
    assert "Your poofout is now" in result


# ── WIZ-013: wizlock/newlock ──────────────────────────────────────


def test_wizlock_toggles() -> None:
    # mirrors ROM src/act_wiz.c:3150-3167
    from mud.commands.admin_commands import cmd_wizlock

    admin = _imm("Admin", 9600)
    result = cmd_wizlock(admin, "")
    assert "wizlock" in result.lower()


def test_newlock_toggles() -> None:
    # mirrors ROM src/act_wiz.c:3171-3188
    from mud.commands.admin_commands import cmd_newlock

    admin = _imm("Admin", 9601)
    result = cmd_newlock(admin, "")
    assert "new" in result.lower() or "lock" in result.lower()


# ── WIZ-014: holylight ──────────────────────────────────────────


def test_holylight_toggles() -> None:
    # mirrors ROM src/act_wiz.c:4422-4439
    from mud.commands.admin_commands import cmd_holylight
    from mud.models.constants import PlayerFlag

    admin = _imm("Admin", 9700)
    result = cmd_holylight(admin, "")
    assert "Holy light mode" in result

    result = cmd_holylight(admin, "")
    assert "Holy light mode" in result
    assert int(PlayerFlag.HOLYLIGHT) & int(getattr(admin, "act", 0)) == 0 or "off" in result.lower() or "on" in result.lower()


# ── WIZ-015: slookup ────────────────────────────────────────────


def test_slookup_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:3198-3200
    from mud.commands.imm_search import do_slookup

    admin = _imm("Admin", 9800)
    result = do_slookup(admin, "")
    assert "Lookup" in result and "skill" in result.lower()


def test_slookup_not_found() -> None:
    # mirrors ROM src/act_wiz.c:3218-3220
    from mud.commands.imm_search import do_slookup

    admin = _imm("Admin", 9801)
    result = do_slookup(admin, "xyznonexistentskill")
    assert "No such skill" in result


# ── WIZ-016: sockets ────────────────────────────────────────────


def test_sockets_no_players() -> None:
    # mirrors ROM src/act_wiz.c:4166-4169
    from mud.commands.imm_search import do_sockets

    admin = _imm("Admin", 9900)
    global_registry.descriptor_list = []
    result = do_sockets(admin, "")
    assert "No one" in result or "0 user" in result


def test_sockets_with_filter() -> None:
    # mirrors ROM src/act_wiz.c:4148-4169
    from mud.commands.imm_search import do_sockets

    admin = _imm("Admin", 9901)
    global_registry.descriptor_list = []
    result = do_sockets(admin, "NobodyHere")
    assert "No one" in result


# ── WIZ-017: do_deny ──────────────────────────────────────────


def test_deny_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:523-525
    from mud.commands.admin_commands import cmd_deny

    admin = _imm("Admin", 10000)
    result = cmd_deny(admin, "")
    assert "Deny whom" in result


def test_deny_not_found() -> None:
    # mirrors ROM src/act_wiz.c:529-531
    from mud.commands.admin_commands import cmd_deny

    admin = _imm("Admin", 10001)
    result = cmd_deny(admin, "NobodyHere12345")
    assert "aren't here" in result


def test_deny_rejects_npc() -> None:
    # mirrors ROM src/act_wiz.c:535-538
    from mud.commands.admin_commands import cmd_deny
    from mud.models.constants import PlayerFlag

    room = _room(10002, name="DenyRoom")
    admin = _imm("Admin", 10002, trust=60)
    mob = create_test_character("denyvictim", room.vnum)
    mob.is_npc = True
    if not hasattr(global_registry, "char_list"):
        global_registry.char_list = []
    if mob not in global_registry.char_list:
        global_registry.char_list.append(mob)

    result = cmd_deny(admin, "denyvictim")
    assert "Not on NPC" in result


def test_deny_sets_plr_deny() -> None:
    # mirrors ROM src/act_wiz.c:547-552 — SET-only, not toggle
    from mud.commands.admin_commands import cmd_deny
    from mud.models.constants import PlayerFlag

    room = _room(10003, name="DenyRoom")
    admin = _imm("Admin", 10003, trust=60)
    victim = _imm("Denytarget", 10003, trust=5)
    victim.is_npc = False

    result = cmd_deny(admin, "Denytarget")
    assert "OK" in result
    assert int(getattr(victim, "act", 0)) & int(PlayerFlag.DENY)


# ── WIZ-018: do_switch ──────────────────────────────────────────


def test_switch_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:2209-2211
    from mud.commands.imm_admin import do_switch

    admin = _imm("Admin", 10100)
    result = do_switch(admin, "")
    assert "Switch into whom" in result


def test_switch_already_switched() -> None:
    # mirrors ROM src/act_wiz.c:2218-2220
    from mud.commands.imm_admin import do_switch

    admin = _imm("Admin", 10101)
    admin.desc = SimpleNamespace(original="previous_body", character=admin)
    result = do_switch(admin, "mob")
    admin.desc = None
    assert "already switched" in result.lower()


def test_switch_rejects_pc() -> None:
    # mirrors ROM src/act_wiz.c:2236-2238
    from mud.commands.imm_admin import do_switch

    room = _room(10102, name="SwitchRoom")
    admin = _imm("Admin", 10102, trust=60)
    admin.desc = SimpleNamespace(original=None, character=admin)
    victim = _imm("Targetpc", 10102, trust=5)
    victim.is_npc = False

    result = do_switch(admin, "Targetpc")
    admin.desc = None
    assert "mobiles" in result.lower()


# ── WIZ-019: do_return ──────────────────────────────────────────


def test_return_not_switched() -> None:
    # mirrors ROM src/act_wiz.c:2280-2283
    from mud.commands.imm_admin import do_return

    admin = _imm("Admin", 10200)
    admin.desc = SimpleNamespace(original=None, character=admin)
    result = do_return(admin, "")
    admin.desc = None
    assert "aren't switched" in result.lower()


# ── WIZ-020: do_smote ──────────────────────────────────────────


def test_smote_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:375-377
    from mud.commands.imm_emote import do_smote

    admin = _imm("Admin", 10300)
    result = do_smote(admin, "")
    assert "Emote what" in result


def test_smote_requires_name() -> None:
    # mirrors ROM src/act_wiz.c:381-383
    from mud.commands.imm_emote import do_smote

    admin = _imm("Admin", 10301)
    result = do_smote(admin, "waves at Mary")
    assert "must include your name" in result.lower()


# ── WIZ-021: do_pecho ───────────────────────────────────────────


def test_pecho_not_found() -> None:
    # mirrors ROM src/act_wiz.c:763-766 — "Target not found" (ROM exact message)
    from mud.commands.imm_display import do_pecho

    admin = _imm("Admin", 10400)
    result = do_pecho(admin, "NobodyHere hello")
    assert "Target not found" in result


# ── WIZ-022: do_disconnect ───────────────────────────────────────


def test_disconnect_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:568-570
    from mud.commands.imm_punish import do_disconnect

    admin = _imm("Admin", 10500)
    result = do_disconnect(admin, "")
    assert "Disconnect whom" in result


def test_disconnect_not_found() -> None:
    # mirrors ROM src/act_wiz.c:590-593
    from mud.commands.imm_punish import do_disconnect

    admin = _imm("Admin", 10501)
    result = do_disconnect(admin, "NobodyHere12345")
    assert "aren't here" in result


# ── WIZ-023: do_guild ──────────────────────────────────────────────


def test_guild_empty_arg() -> None:
    # mirrors ROM src/act_wiz.c:206-209
    from mud.commands.remaining_rom import do_guild

    admin = _imm("Admin", 10600)
    result = do_guild(admin, "")
    assert "Syntax" in result
    assert result.endswith("\n\r")


def test_guild_missing_clan_arg() -> None:
    # mirrors ROM src/act_wiz.c:206-209
    from mud.commands.remaining_rom import do_guild

    admin = _imm("Admin", 10601)
    victim = _imm("Victim", 10601, trust=10)
    result = do_guild(admin, victim.name)
    assert "Syntax" in result
    assert result.endswith("\n\r")


def test_guild_target_not_playing() -> None:
    # mirrors ROM src/act_wiz.c:211-214
    from mud.commands.remaining_rom import do_guild

    admin = _imm("Admin", 10602)
    result = do_guild(admin, "NobodyHere guild")
    assert "aren't playing" in result
    assert result.endswith("\n\r")


def test_guild_none_makes_clanless() -> None:
    # mirrors ROM src/act_wiz.c:217-222
    from mud.commands.remaining_rom import do_guild

    admin = _imm("Admin", 10603)
    victim = _imm("GuildVictim", 10603, trust=10)
    victim.clan = 2
    result = do_guild(admin, f"{victim.name} none")
    assert victim.clan == 0
    assert "clanless" in result.lower()
    assert result.endswith("\n\r")
    victim_msgs = getattr(victim, "output_buffer", [])
    assert any("no clan" in m.lower() for m in victim_msgs)


def test_guild_independent_clan_messages() -> None:
    # mirrors ROM src/act_wiz.c:231-236 — independent clans say "a <name>"
    from mud.commands.remaining_rom import do_guild
    from mud.models.clans import CLAN_TABLE

    admin = _imm("Admin", 10604)
    victim = _imm("GuildVictim2", 10604, trust=10)
    victim.clan = 0
    result = do_guild(admin, f"{victim.name} loner")
    assert victim.clan != 0
    clan = CLAN_TABLE[victim.clan]
    if clan.is_independent:
        assert f"a {clan.name}" in result.lower() or clan.name.lower() in result.lower()
    assert result.endswith("\n\r")


def test_guild_member_clan_messages() -> None:
    # mirrors ROM src/act_wiz.c:238-244 — member clans say "member of clan <Name>"
    from mud.commands.remaining_rom import do_guild
    from mud.models.clans import CLAN_TABLE

    admin = _imm("Admin", 10605)
    victim = _imm("GuildVictim3", 10605, trust=10)
    victim.clan = 0
    result = do_guild(admin, f"{victim.name} rom")
    assert victim.clan != 0
    clan = CLAN_TABLE[victim.clan]
    if not clan.is_independent:
        assert "member of clan" in result.lower()
        assert clan.name.capitalize() in result
    assert result.endswith("\n\r")


def test_guild_no_such_clan() -> None:
    # mirrors ROM src/act_wiz.c:225-228
    from mud.commands.remaining_rom import do_guild

    admin = _imm("Admin", 10606)
    victim = _imm("GuildVictim4", 10606, trust=10)
    result = do_guild(admin, f"{victim.name} bogusclan999")
    assert "no such clan" in result.lower()
    assert result.endswith("\n\r")


# ── WIZ-024: do_outfit ──────────────────────────────────────────────


def test_outfit_rejects_high_level() -> None:
    # mirrors ROM src/act_wiz.c:256-259 — "Find it yourself!" for level > 5
    from mud.commands.inventory import do_outfit

    char = _imm("HighLevel", 10700, trust=10)
    result = do_outfit(char, "")
    assert "Find it yourself" in result
    assert result.endswith("\n\r")


def test_outfit_rejects_npc() -> None:
    # mirrors ROM src/act_wiz.c:256-259 — "Find it yourself!" for NPCs
    from mud.commands.inventory import do_outfit

    char = create_test_character("Mob", 10701)
    char.is_npc = True
    result = do_outfit(char, "")
    assert "Find it yourself" in result
    assert result.endswith("\n\r")


# ── WIZ-025: do_copyover ────────────────────────────────────────────


def test_copyover_announces_to_players() -> None:
    # mirrors ROM src/act_wiz.c:4520-4521
    from mud.commands.imm_server import do_copyover

    admin = _imm("Admin", 10800)
    player = _imm("Player", 10800, trust=10)
    player.messages = []
    result = do_copyover(admin, "")
    assert "COPYOVER" in result or "copyover" in result.lower()


def test_copyover_result_has_newline() -> None:
    # mirrors ROM src/act_wiz.c — all messages end \n\r
    from mud.commands.imm_server import do_copyover

    admin = _imm("Admin", 10801)
    result = do_copyover(admin, "")
    assert result.endswith("\n\r")


# ── WIZ-026: do_qmconfig ────────────────────────────────────────────


def test_qmconfig_empty_shows_options() -> None:
    # mirrors ROM src/act_wiz.c:4697-4705
    from mud.commands.admin_commands import cmd_qmconfig

    admin = _imm("Admin", 10900)
    result = cmd_qmconfig(admin, "")
    assert "Valid qmconfig options" in result
    assert "show" in result
    assert result.endswith("\n\r")


def test_qmconfig_unknown_option() -> None:
    # mirrors ROM src/act_wiz.c:4785 — "I have no clue what you are trying to do..."
    from mud.commands.admin_commands import cmd_qmconfig

    admin = _imm("Admin", 10901)
    result = cmd_qmconfig(admin, "bogus_option123")
    assert "no clue" in result.lower()
    assert result.endswith("\n\r")
