from __future__ import annotations

import shlex
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from mud.admin_logging.admin import is_log_all_enabled, log_admin_command
from mud.models.character import Character
from mud.models.constants import LEVEL_HERO, LEVEL_IMMORTAL, MAX_LEVEL, AffectFlag, PlayerFlag, Position
from mud.models.social import find_social
from mud.net.session import Session
from mud.wiznet import cmd_wiznet

from .admin_commands import (
    cmd_allow,
    cmd_ban,
    cmd_banlist,
    cmd_deny,
    cmd_holylight,
    cmd_incognito,
    cmd_log,
    cmd_newlock,
    cmd_permban,
    cmd_qmconfig,
    cmd_spawn,
    cmd_teleport,
    cmd_unban,
    cmd_who,
    cmd_wizlock,
)
from .advancement import do_practice, do_train
from .affects import do_affects
from .alias_cmds import do_alias, do_prefi, do_prefix, do_unalias
from .auto_settings import (
    do_autoall,
    do_autoassist,
    do_autoexit,
    do_autogold,
    do_autolist,
    do_autoloot,
    do_autosac,
    do_autosplit,
    do_brief,
    do_color,
    do_colour,
    do_combine,
    do_compact,
    do_prompt,
    do_telnetga,
)
from .build import (
    cmd_aedit,
    cmd_asave,
    cmd_goto,
    cmd_hedit,
    cmd_hesave,
    cmd_medit,
    cmd_mstat,
    cmd_oedit,
    cmd_ostat,
    cmd_redit,
    cmd_rstat,
    cmd_vlist,
    handle_aedit_command,
    handle_hedit_command,
    handle_medit_command,
    handle_oedit_command,
    handle_redit_command,
)
from .channels import do_channels
from .character import do_description, do_password, do_title
from .combat import (
    do_backstab,
    do_bash,
    do_berserk,
    do_cast,
    do_dirt,
    do_disarm,
    do_flee,
    do_kick,
    do_kill,
    do_rescue,
    do_surrender,
    do_trip,
)
from .communication import (
    do_answer,
    do_auction,
    do_cgossip,
    do_clantalk,
    do_emote,
    do_gossip,
    do_grats,
    do_immtalk,
    do_music,
    do_pose,
    do_question,
    do_quote,
    do_reply,
    do_say,
    do_shout,
    do_tell,
    do_yell,
)
from .compare import do_compare
from .consider import do_consider
from .consumption import do_drink, do_eat
from .doors import do_close, do_lock, do_open, do_pick, do_unlock
from .equipment import do_hold, do_wear, do_wield
from .feedback import do_bug, do_idea, do_typo
from .give import do_give
from .group_commands import do_follow, do_group, do_gtell, do_order, do_split
from .healer import do_heal
from .help import do_help, do_wizlist
from .imc import do_imc, try_imc_command
from .imm_admin import do_advance, do_freeze, do_return, do_snoop, do_switch, do_trust
from .imm_commands import do_at, do_force, do_goto, do_peace, do_transfer
from .imm_display import (
    do_echo,
    do_incognito,
    do_invis,
    do_pecho,
    do_poofin,
    do_poofout,
    do_recho,
    do_wizinvis,
    do_zecho,
)
from .imm_emote import do_gecho, do_pmote, do_smote
from .imm_load import do_load, do_mload, do_oload, do_purge, do_restore, do_sla, do_slay
from .imm_olc import do_alist, do_edit, do_mpedit, do_resets
from .imm_punish import do_disconnect, do_nochannels, do_noemote, do_noshout, do_notell, do_pardon
from .imm_search import (
    do_clone,
    do_memory,
    do_mfind,
    do_mwhere,
    do_ofind,
    do_owhere,
    do_slookup,
    do_sockets,
    do_stat,
    do_vnum,
)
from .imm_server import do_copyover, do_dump, do_protect, do_reboot, do_shutdown, do_violate
from .imm_set import do_mset, do_oset, do_rset, do_set, do_sset, do_string
from .info import do_areas, do_commands, do_credits, do_report, do_time, do_weather, do_where, do_who, do_wizhelp
from .info_extended import do_count, do_examine, do_read, do_whois, do_worth
from .inspection import do_exits, do_look, do_scan
from .inventory import do_drop, do_equipment, do_get, do_inventory, do_outfit
from .liquids import do_empty, do_fill, do_pour
from .magic_items import do_brandish, do_recite, do_zap
from .misc_info import do_imotd, do_motd, do_rent, do_rules, do_skills, do_socials, do_spells, do_story
from .misc_player import do_afk, do_config, do_peek, do_permit, do_replay, do_unread
from .mobprog_tools import do_mpdump, do_mpstat
from .movement import do_down, do_east, do_enter, do_north, do_south, do_up, do_west
from .murder import do_murder
from .notes import do_board, do_note
from .obj_manipulation import do_put, do_quaff, do_remove, do_sacrifice
from .player_config import do_delet, do_delete, do_nofollow, do_noloot, do_nosummon
from .player_info import do_info, do_play, do_scroll, do_show
from .position import do_rest, do_sit, do_sleep, do_stand, do_wake
from .remaining_rom import (
    do_bs,
    do_deaf,
    do_envenom,
    do_flag,
    do_gain,
    do_groups,
    do_guild,
    do_mob,
    do_qmread,
    do_quiet,
    do_teleport,
    do_wimpy,
)
from .session import do_quit, do_recall, do_save, do_score
from .shop import do_buy, do_list, do_sell, do_value
from .socials import perform_social
from .thief_skills import do_hide, do_sneak, do_steal, do_visible
from .typo_guards import do_alia, do_murde, do_qui, do_reboo, do_shutdow

CommandFunc = Callable[[Character, str], str]


class LogLevel(Enum):
    """Mirror ROM command log levels."""

    NORMAL = auto()
    ALWAYS = auto()
    NEVER = auto()


@dataclass(frozen=True)
class Command:
    name: str
    func: CommandFunc
    aliases: tuple[str, ...] = ()
    admin_only: bool = False
    min_position: Position = Position.DEAD
    log_level: LogLevel = LogLevel.NORMAL
    min_trust: int = 0
    show: bool = True


COMMANDS: list[Command] = [
    # Movement (require standing per ROM)
    Command(
        "north",
        do_north,
        aliases=("n",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
        show=False,
    ),
    Command(
        "east",
        do_east,
        aliases=("e",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
        show=False,
    ),
    Command(
        "south",
        do_south,
        aliases=("s",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
        show=False,
    ),
    Command(
        "west",
        do_west,
        aliases=("w",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
        show=False,
    ),
    Command(
        "up",
        do_up,
        aliases=("u",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
        show=False,
    ),
    Command(
        "down",
        do_down,
        aliases=("d",),
        min_position=Position.STANDING,
        log_level=LogLevel.NEVER,
        show=False,
    ),
    # ROM src/interp.c:263 — `go` is a cmd_table alias for do_enter.
    Command("enter", do_enter, aliases=("go",), min_position=Position.STANDING),
    # Position changes
    Command("sleep", do_sleep, min_position=Position.SLEEPING),
    Command("wake", do_wake, min_position=Position.SLEEPING),
    Command("rest", do_rest, min_position=Position.SLEEPING),
    Command("stand", do_stand, min_position=Position.SLEEPING),
    # Common actions
    Command("look", do_look, aliases=("l",), min_position=Position.RESTING),
    Command("exits", do_exits, aliases=("ex",), min_position=Position.RESTING),
    # ROM src/interp.c:226 — `take` is a cmd_table alias for do_get.
    Command("get", do_get, aliases=("g", "take"), min_position=Position.RESTING),
    Command("drop", do_drop, min_position=Position.RESTING),
    Command("inventory", do_inventory, aliases=("inv",), min_position=Position.DEAD),
    Command("equipment", do_equipment, aliases=("eq",), min_position=Position.DEAD),
    Command("outfit", do_outfit, min_position=Position.RESTING),
    # Communication
    Command("say", do_say, aliases=("'",), min_position=Position.RESTING),
    Command("tell", do_tell, min_position=Position.RESTING),
    Command("reply", do_reply, min_position=Position.RESTING),
    # ROM src/interp.c:200 — shout requires trust 3.
    Command("shout", do_shout, min_position=Position.RESTING, min_trust=3),
    Command("yell", do_yell, min_position=Position.RESTING),
    Command("emote", do_emote, aliases=(",",), min_position=Position.RESTING),
    Command("pose", do_pose, min_position=Position.RESTING),
    Command("auction", do_auction, min_position=Position.RESTING),
    Command("gossip", do_gossip, aliases=(".",), min_position=Position.RESTING),
    Command("cgossip", do_cgossip, min_position=Position.RESTING),
    Command("grats", do_grats, min_position=Position.RESTING),
    Command("quote", do_quote, min_position=Position.RESTING),
    Command("question", do_question, min_position=Position.RESTING),
    Command("answer", do_answer, min_position=Position.RESTING),
    Command("music", do_music, min_position=Position.RESTING),
    Command("clan", do_clantalk, min_position=Position.SLEEPING),
    Command("clantalk", do_clantalk, min_position=Position.SLEEPING),  # ROM alias
    # ROM src/interp.c:356 — `:` is a cmd_table alias for do_immtalk.
    Command(
        "immtalk",
        do_immtalk,
        aliases=(":",),
        min_position=Position.DEAD,
        min_trust=LEVEL_HERO,
    ),
    # Combat
    # ROM src/interp.c:88 — `hit` is a cmd_table alias for do_kill.
    Command("kill", do_kill, aliases=("attack", "hit"), min_position=Position.FIGHTING),
    Command("kick", do_kick, min_position=Position.FIGHTING),
    Command("rescue", do_rescue, min_position=Position.FIGHTING),
    Command("flee", do_flee, min_position=Position.FIGHTING),
    Command("backstab", do_backstab, aliases=("bs",), min_position=Position.STANDING),
    Command("bash", do_bash, min_position=Position.FIGHTING),
    Command("berserk", do_berserk, min_position=Position.FIGHTING),
    Command("dirt", do_dirt, min_position=Position.FIGHTING),
    Command("disarm", do_disarm, min_position=Position.FIGHTING),
    Command("trip", do_trip, min_position=Position.FIGHTING),
    Command("surrender", do_surrender, min_position=Position.FIGHTING),
    Command("murder", do_murder, min_position=Position.FIGHTING),
    Command("cast", do_cast, min_position=Position.RESTING),
    Command("consider", do_consider, aliases=("con",), min_position=Position.RESTING),
    # Group Commands
    Command("follow", do_follow, min_position=Position.RESTING),
    Command("group", do_group, min_position=Position.SLEEPING),
    Command("gtell", do_gtell, aliases=("gt", ";"), min_position=Position.SLEEPING),
    Command("split", do_split, min_position=Position.RESTING),
    Command("order", do_order, min_position=Position.RESTING),
    # Item Transfer
    Command("give", do_give, min_position=Position.RESTING),
    # Door Commands
    Command("open", do_open, min_position=Position.RESTING),
    Command("close", do_close, min_position=Position.RESTING),
    Command("lock", do_lock, min_position=Position.RESTING),
    Command("unlock", do_unlock, min_position=Position.RESTING),
    Command("pick", do_pick, min_position=Position.RESTING),
    # Magic Items
    Command("recite", do_recite, min_position=Position.RESTING),
    Command("brandish", do_brandish, min_position=Position.RESTING),
    Command("zap", do_zap, min_position=Position.RESTING),
    # Equipment
    Command("wear", do_wear, min_position=Position.RESTING),
    Command("wield", do_wield, min_position=Position.RESTING),
    Command("hold", do_hold, min_position=Position.RESTING),
    # Consumption
    Command("eat", do_eat, min_position=Position.RESTING),
    Command("drink", do_drink, min_position=Position.RESTING),
    # Liquid Commands
    Command("fill", do_fill, min_position=Position.RESTING),
    Command("pour", do_pour, min_position=Position.RESTING),
    Command("empty", do_empty, min_position=Position.RESTING),
    # Session/Character Info
    Command("save", do_save, min_position=Position.DEAD),
    Command("quit", do_quit, min_position=Position.SLEEPING),
    Command("score", do_score, min_position=Position.DEAD),
    Command("recall", do_recall, aliases=("/",), min_position=Position.STANDING),
    Command("password", do_password, min_position=Position.DEAD),
    Command("title", do_title, min_position=Position.DEAD),
    Command("description", do_description, min_position=Position.DEAD, aliases=("desc",)),
    # Info
    Command("scan", do_scan, min_position=Position.SLEEPING),
    Command("who", do_who, min_position=Position.DEAD),
    Command("areas", do_areas, min_position=Position.DEAD),
    Command("where", do_where, min_position=Position.RESTING),
    Command("time", do_time, min_position=Position.DEAD),
    Command("weather", do_weather, min_position=Position.RESTING),
    Command("credits", do_credits, min_position=Position.DEAD),
    Command("report", do_report, min_position=Position.RESTING),
    Command("affects", do_affects, min_position=Position.DEAD),
    Command("compare", do_compare, min_position=Position.RESTING),
    Command("channels", do_channels, min_position=Position.DEAD),
    # P1 - Thief Skills
    Command("sneak", do_sneak, min_position=Position.STANDING),
    Command("hide", do_hide, min_position=Position.RESTING),
    Command("visible", do_visible, min_position=Position.SLEEPING),
    Command("steal", do_steal, min_position=Position.STANDING),
    # P1 - Info Extended
    Command("examine", do_examine, aliases=("exa",), min_position=Position.RESTING),
    Command("read", do_read, min_position=Position.RESTING),
    Command("count", do_count, min_position=Position.SLEEPING),
    Command("whois", do_whois, min_position=Position.DEAD),
    Command("worth", do_worth, min_position=Position.SLEEPING),
    Command("sit", do_sit, min_position=Position.SLEEPING),
    # P2 - Auto Settings
    Command("autolist", do_autolist, min_position=Position.DEAD),
    Command("autoall", do_autoall, min_position=Position.DEAD),
    Command("autoassist", do_autoassist, min_position=Position.DEAD),
    Command("autoexit", do_autoexit, min_position=Position.DEAD),
    Command("autogold", do_autogold, min_position=Position.DEAD),
    Command("autoloot", do_autoloot, min_position=Position.DEAD),
    Command("autosac", do_autosac, min_position=Position.DEAD),
    Command("autosplit", do_autosplit, min_position=Position.DEAD),
    Command("brief", do_brief, min_position=Position.DEAD),
    Command("compact", do_compact, min_position=Position.DEAD),
    Command("combine", do_combine, min_position=Position.DEAD),
    Command("colour", do_colour, min_position=Position.DEAD),
    Command("color", do_color, min_position=Position.DEAD),
    Command("prompt", do_prompt, min_position=Position.DEAD),
    # P2 - Misc Info
    Command("motd", do_motd, min_position=Position.DEAD),
    Command("imotd", do_imotd, min_position=Position.DEAD, min_trust=LEVEL_HERO),
    Command("rules", do_rules, min_position=Position.DEAD),
    Command("story", do_story, min_position=Position.DEAD),
    Command("socials", do_socials, min_position=Position.DEAD),
    Command("skills", do_skills, min_position=Position.DEAD),
    Command("spells", do_spells, min_position=Position.DEAD),
    Command("rent", do_rent, min_position=Position.DEAD),
    # Player Essential - Object Manipulation
    Command("put", do_put, min_position=Position.RESTING),
    Command("remove", do_remove, min_position=Position.RESTING),
    # ROM src/interp.c:228-229 — `junk` and `tap` are cmd_table aliases for do_sacrifice.
    Command("sacrifice", do_sacrifice, aliases=("sac", "junk", "tap"), min_position=Position.RESTING),
    Command("quaff", do_quaff, min_position=Position.RESTING),
    # Player Essential - Info
    Command("scroll", do_scroll, min_position=Position.DEAD),
    Command("show", do_show, min_position=Position.DEAD),
    Command("play", do_play, min_position=Position.RESTING),
    Command("info", do_info, min_position=Position.SLEEPING),
    # Player Config
    Command("noloot", do_noloot, min_position=Position.DEAD),
    Command("nofollow", do_nofollow, min_position=Position.DEAD),
    Command("nosummon", do_nosummon, min_position=Position.DEAD),
    Command("delete", do_delete, min_position=Position.STANDING),
    Command("delet", do_delet, min_position=Position.DEAD, show=False),
    # Immortal Commands - Basic
    Command("at", do_at, min_position=Position.DEAD, min_trust=MAX_LEVEL - 6),
    Command("goto", do_goto, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("transfer", do_transfer, min_position=Position.DEAD, min_trust=MAX_LEVEL - 5),
    Command("force", do_force, min_position=Position.DEAD, min_trust=MAX_LEVEL - 7),
    Command("peace", do_peace, min_position=Position.DEAD, min_trust=MAX_LEVEL - 5),
    # Immortal Commands - Load/Purge
    Command("load", do_load, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    Command("mload", do_mload, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL, show=False),
    Command("oload", do_oload, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL, show=False),
    Command("purge", do_purge, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    Command("restore", do_restore, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    Command("slay", do_slay, min_position=Position.DEAD, min_trust=MAX_LEVEL - 3),
    Command("sla", do_sla, min_position=Position.DEAD, min_trust=MAX_LEVEL - 3, show=False),
    # Immortal Commands - Admin
    Command("advance", do_advance, min_position=Position.DEAD, min_trust=MAX_LEVEL),
    Command("trust", do_trust, min_position=Position.DEAD, min_trust=MAX_LEVEL),
    Command("freeze", do_freeze, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    Command("snoop", do_snoop, min_position=Position.DEAD, min_trust=MAX_LEVEL - 5),
    Command("switch", do_switch, min_position=Position.DEAD, min_trust=MAX_LEVEL - 6),
    Command("return", do_return, min_position=Position.DEAD, min_trust=MAX_LEVEL - 6),
    # Immortal Commands - Display
    Command("invis", do_invis, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("wizinvis", do_wizinvis, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("incognito", do_incognito, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("poofin", do_poofin, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("poofout", do_poofout, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("bamfin", do_poofin, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),  # ROM alias
    Command("bamfout", do_poofout, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),  # ROM alias
    Command("echo", do_echo, min_position=Position.DEAD, min_trust=MAX_LEVEL - 6),
    Command("recho", do_recho, min_position=Position.DEAD, min_trust=MAX_LEVEL - 6),
    Command("zecho", do_zecho, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    Command("pecho", do_pecho, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    # Immortal Commands - Punishment
    Command("nochannels", do_nochannels, min_position=Position.DEAD, min_trust=MAX_LEVEL - 5),
    Command("noemote", do_noemote, min_position=Position.DEAD, min_trust=MAX_LEVEL - 5),
    Command("noshout", do_noshout, min_position=Position.DEAD, min_trust=MAX_LEVEL - 5),
    Command("notell", do_notell, min_position=Position.DEAD, min_trust=MAX_LEVEL - 5),
    Command("pardon", do_pardon, min_position=Position.DEAD, min_trust=MAX_LEVEL - 3),
    Command("disconnect", do_disconnect, min_position=Position.DEAD, min_trust=MAX_LEVEL - 3),
    # Immortal Commands - Search/Info
    Command("vnum", do_vnum, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    Command("mfind", do_mfind, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("ofind", do_ofind, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("slookup", do_slookup, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("owhere", do_owhere, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("mwhere", do_mwhere, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("sockets", do_sockets, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    Command("memory", do_memory, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("clone", do_clone, min_position=Position.DEAD, min_trust=MAX_LEVEL - 5),
    Command("stat", do_stat, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    # Immortal Commands - Server Control
    Command("reboot", do_reboot, min_position=Position.DEAD, min_trust=MAX_LEVEL - 1),
    Command("shutdown", do_shutdown, min_position=Position.DEAD, min_trust=MAX_LEVEL - 1),
    Command("copyover", do_copyover, min_position=Position.DEAD, min_trust=MAX_LEVEL),
    Command("protect", do_protect, min_position=Position.DEAD, min_trust=MAX_LEVEL - 1),
    Command("violate", do_violate, min_position=Position.DEAD, min_trust=MAX_LEVEL),
    Command("dump", do_dump, min_position=Position.DEAD, min_trust=MAX_LEVEL),
    # Immortal Commands - Set/String
    Command("set", do_set, min_position=Position.DEAD, min_trust=MAX_LEVEL - 2),
    Command("mset", do_mset, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("oset", do_oset, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("rset", do_rset, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("sset", do_sset, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("string", do_string, min_position=Position.DEAD, min_trust=MAX_LEVEL - 5),
    # Immortal Commands - Emotes
    Command("smote", do_smote, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("pmote", do_pmote, min_position=Position.RESTING),
    Command("gecho", do_gecho, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    # Immortal Commands - OLC
    Command("resets", do_resets, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("alist", do_alist, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("edit", do_edit, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    Command("olc", do_edit, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),  # ROM alias for edit
    Command("mpedit", do_mpedit, min_position=Position.DEAD, min_trust=LEVEL_IMMORTAL),
    # Miscellaneous Player Commands
    Command("afk", do_afk, min_position=Position.SLEEPING),
    Command("replay", do_replay, min_position=Position.SLEEPING),
    Command("config", do_config, min_position=Position.DEAD),
    Command("permit", do_permit, min_position=Position.RESTING),
    Command("peek", do_peek, min_position=Position.STANDING),
    Command("unread", do_unread, min_position=Position.SLEEPING),
    # Remaining ROM Commands
    Command("wimpy", do_wimpy, min_position=Position.DEAD),
    Command("deaf", do_deaf, min_position=Position.DEAD),
    Command("quiet", do_quiet, min_position=Position.SLEEPING),
    Command("envenom", do_envenom, min_position=Position.RESTING),
    Command("gain", do_gain, min_position=Position.STANDING),
    Command("groups", do_groups, min_position=Position.SLEEPING),
    Command("guild", do_guild, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    Command("flag", do_flag, min_position=Position.DEAD, min_trust=MAX_LEVEL - 4),
    Command("mob", do_mob, min_position=Position.DEAD, show=False),
    # Alias Commands
    Command("bs", do_bs, min_position=Position.FIGHTING, show=False),
    Command("teleport", do_teleport, min_position=Position.DEAD, min_trust=MAX_LEVEL - 5, show=False),
    # Typo Guards
    Command("qui", do_qui, min_position=Position.DEAD, show=False),
    Command("murde", do_murde, min_position=Position.DEAD, show=False),
    Command("reboo", do_reboo, min_position=Position.DEAD, min_trust=MAX_LEVEL - 1, show=False),
    Command("shutdow", do_shutdow, min_position=Position.DEAD, min_trust=MAX_LEVEL - 1, show=False),
    Command("alia", do_alia, min_position=Position.DEAD, show=False),
    # Feedback
    Command("bug", do_bug, min_position=Position.DEAD),
    Command("idea", do_idea, min_position=Position.DEAD),
    Command("typo", do_typo, min_position=Position.DEAD),
    # Shops
    Command("list", do_list, min_position=Position.RESTING),
    Command("buy", do_buy, min_position=Position.RESTING),
    Command("sell", do_sell, min_position=Position.RESTING),
    Command("value", do_value, min_position=Position.RESTING),
    Command("heal", do_heal, min_position=Position.RESTING),
    # Advancement
    Command("practice", do_practice, min_position=Position.SLEEPING),
    Command("train", do_train, min_position=Position.RESTING),
    # Boards/Notes/Help
    Command("board", do_board, min_position=Position.SLEEPING),
    Command("note", do_note, min_position=Position.DEAD),
    Command("wizhelp", do_wizhelp, min_position=Position.DEAD, min_trust=LEVEL_HERO),
    Command("commands", do_commands, min_position=Position.DEAD),
    Command("wizlist", do_wizlist, min_position=Position.DEAD),
    Command("help", do_help, min_position=Position.DEAD),
    Command("telnetga", do_telnetga, min_position=Position.DEAD),
    # IMC and aliasing
    Command("imc", do_imc, min_position=Position.DEAD),
    Command("alias", do_alias, min_position=Position.DEAD),
    Command("unalias", do_unalias, min_position=Position.DEAD),
    Command("prefix", do_prefix, min_position=Position.DEAD),
    Command("prefi", do_prefi, min_position=Position.DEAD, show=False),
    # Admin (leave position as DEAD; admin-only gating applies separately)
    Command("@who", cmd_who, admin_only=True, min_trust=LEVEL_HERO),
    Command(
        "@teleport",
        cmd_teleport,
        admin_only=True,
        log_level=LogLevel.ALWAYS,
        min_trust=LEVEL_HERO,
    ),
    Command(
        "@spawn",
        cmd_spawn,
        admin_only=True,
        log_level=LogLevel.ALWAYS,
        min_trust=LEVEL_HERO,
    ),
    Command("ban", cmd_ban, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=MAX_LEVEL - 2),
    Command(
        "permban",
        cmd_permban,
        admin_only=True,
        log_level=LogLevel.ALWAYS,
        min_trust=MAX_LEVEL - 1,
    ),
    Command("deny", cmd_deny, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=MAX_LEVEL - 1),
    Command("allow", cmd_allow, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=MAX_LEVEL - 2),
    Command("unban", cmd_unban, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=LEVEL_HERO),
    Command("banlist", cmd_banlist, admin_only=True, min_trust=LEVEL_HERO),
    Command("log", cmd_log, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=MAX_LEVEL - 1),
    Command("incognito", cmd_incognito, admin_only=True, min_trust=LEVEL_HERO),
    Command("holylight", cmd_holylight, admin_only=True, min_trust=LEVEL_HERO),
    Command(
        "qmconfig",
        cmd_qmconfig,
        admin_only=True,
        log_level=LogLevel.ALWAYS,
        min_trust=MAX_LEVEL,
    ),
    Command(
        "qmread",
        do_qmread,
        admin_only=True,
        min_trust=MAX_LEVEL,
    ),
    # OLC Commands - ROM style (no @ prefix)
    Command("redit", cmd_redit, admin_only=True, min_trust=LEVEL_HERO),
    Command("aedit", cmd_aedit, admin_only=True, min_trust=LEVEL_HERO),
    Command("oedit", cmd_oedit, admin_only=True, min_trust=LEVEL_HERO),
    Command("medit", cmd_medit, admin_only=True, min_trust=LEVEL_HERO),
    Command("hedit", cmd_hedit, admin_only=True, min_trust=LEVEL_HERO),
    Command("asave", cmd_asave, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=LEVEL_HERO),
    Command("hesave", cmd_hesave, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=LEVEL_HERO),
    Command("rstat", cmd_rstat, admin_only=True, min_trust=LEVEL_HERO),
    Command("ostat", cmd_ostat, admin_only=True, min_trust=LEVEL_HERO),
    Command("mstat", cmd_mstat, admin_only=True, min_trust=LEVEL_HERO),
    Command("vlist", cmd_vlist, admin_only=True, min_trust=LEVEL_HERO),
    # OLC Commands - Legacy @ prefix (aliases)
    Command("@redit", cmd_redit, admin_only=True, min_trust=LEVEL_HERO, show=False),
    Command("@aedit", cmd_aedit, admin_only=True, min_trust=LEVEL_HERO, show=False),
    Command("@oedit", cmd_oedit, admin_only=True, min_trust=LEVEL_HERO, show=False),
    Command("@medit", cmd_medit, admin_only=True, min_trust=LEVEL_HERO, show=False),
    Command("@hedit", cmd_hedit, admin_only=True, min_trust=LEVEL_HERO, show=False),
    Command("@asave", cmd_asave, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=LEVEL_HERO, show=False),
    Command("@hesave", cmd_hesave, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=LEVEL_HERO, show=False),
    Command("@rstat", cmd_rstat, admin_only=True, min_trust=LEVEL_HERO, show=False),
    Command("@ostat", cmd_ostat, admin_only=True, min_trust=LEVEL_HERO, show=False),
    Command("@mstat", cmd_mstat, admin_only=True, min_trust=LEVEL_HERO, show=False),
    Command("@goto", cmd_goto, admin_only=True, min_trust=LEVEL_HERO, show=False),
    Command("@vlist", cmd_vlist, admin_only=True, min_trust=LEVEL_HERO, show=False),
    Command("wizlock", cmd_wizlock, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=MAX_LEVEL - 2),
    Command("newlock", cmd_newlock, admin_only=True, log_level=LogLevel.ALWAYS, min_trust=MAX_LEVEL - 4),
    Command("wiznet", cmd_wiznet, min_trust=LEVEL_IMMORTAL),
    Command(
        "mpdump",
        do_mpdump,
        admin_only=True,
        log_level=LogLevel.NEVER,
        min_trust=LEVEL_HERO,
    ),
    Command(
        "mpstat",
        do_mpstat,
        admin_only=True,
        log_level=LogLevel.NEVER,
        min_trust=LEVEL_HERO,
    ),
]


COMMAND_INDEX: dict[str, Command] = {}
for cmd in COMMANDS:
    COMMAND_INDEX[cmd.name] = cmd
    for alias in cmd.aliases:
        COMMAND_INDEX[alias] = cmd


# ROM cmd_table names in declaration order (src/interp.c:67-381). The
# prefix-match scan walks this list so the first ROM-table entry whose
# name starts with the user input wins — including ROM's hand-ordered
# block at the top "Placed here so one and two letter abbreviations
# work" (src/interp.c:74-104). Maintained by hand to match ROM; if the
# C table changes, regenerate via the parser in
# tests/integration/test_interp_prefix_order.py.
_ROM_CMD_TABLE_NAMES: tuple[str, ...] = (
    "north", "east", "south", "west", "up", "down",
    "at", "cast", "auction", "buy", "channels", "exits", "get", "goto",
    "group", "guild", "hit", "inventory", "kill", "look", "clan", "music",
    "order", "practice", "rest", "scan", "sit", "sockets", "stand", "tell",
    "unlock", "wield", "wizhelp",
    "affects", "areas", "board", "commands", "compare", "consider",
    "count", "credits", "equipment", "examine", "help", "info", "motd",
    "read", "report", "rules", "score", "skills", "socials", "show",
    "spells", "story", "time", "typo", "weather", "who", "whois",
    "wizlist", "worth",
    "alia", "alias", "autolist", "autoall", "autoassist", "autoexit",
    "autogold", "autoloot", "autosac", "autosplit", "brief", "colour",
    "color", "combine", "compact", "description", "delet", "delete",
    "nofollow", "noloot", "nosummon", "outfit", "password", "prompt",
    "scroll", "telnetga", "title", "unalias", "wimpy",
    "afk", "answer", "deaf", "emote", "pmote", ".", "gossip", ",", "grats",
    "gtell", ";", "note", "pose", "question", "quote", "quiet", "reply",
    "replay", "say", "'", "shout", "yell",
    "brandish", "close", "drink", "drop", "eat", "envenom", "fill", "give",
    "heal", "hold", "list", "lock", "open", "pick", "pour", "put", "quaff",
    "recite", "remove", "sell", "take", "sacrifice", "junk", "tap", "value",
    "wear", "zap",
    "backstab", "bash", "bs", "berserk", "dirt", "disarm", "flee", "kick",
    "murde", "murder", "rescue", "surrender", "trip",
    "mob", "enter", "follow", "gain", "go", "groups", "hide", "play", "qui",
    "quit", "recall", "/", "rent", "save", "sleep", "sneak", "split", "steal",
    "train", "visible", "wake", "where",
    "advance", "copyover", "dump", "trust", "violate", "allow", "ban", "deny",
    "disconnect", "flag", "freeze", "permban", "protect", "reboo", "reboot",
    "set", "shutdow", "shutdown", "wizlock", "force", "load", "newlock",
    "nochannels", "noemote", "noshout", "notell", "pecho", "pardon", "purge",
    "qmconfig", "restore", "sla", "slay", "teleport", "transfer",
    "poofin", "poofout", "gecho", "holylight", "incognito", "invis", "log",
    "memory", "mwhere", "owhere", "peace", "echo", "return", "snoop", "stat",
    "string", "switch", "wizinvis", "vnum", "zecho", "clone", "wiznet",
    "immtalk", "imotd", ":", "smote", "prefi", "prefix", "mpdump", "mpstat",
    "edit", "asave", "alist", "resets", "redit", "medit", "aedit", "oedit",
    "mpedit", "hedit",
)


def _build_prefix_table() -> list[tuple[str, Command]]:
    """Return [(rom_name, command), ...] for the prefix scan.

    ROM cmd_table names come first in declaration order (each pointing
    via COMMAND_INDEX to the Python Command that implements its do_fun).
    Python-only commands not in the ROM table are appended after, so
    their abbreviations still resolve via prefix lookup.
    """
    pairs: list[tuple[str, Command]] = []
    used_ids: set[int] = set()
    for rom_name in _ROM_CMD_TABLE_NAMES:
        cmd = COMMAND_INDEX.get(rom_name)
        if cmd is None:
            continue
        pairs.append((rom_name, cmd))
        used_ids.add(id(cmd))
    for cmd in COMMANDS:
        if id(cmd) not in used_ids:
            pairs.append((cmd.name, cmd))
            used_ids.add(id(cmd))
    return pairs


_PREFIX_TABLE: list[tuple[str, Command]] = _build_prefix_table()


def _prefix_table() -> list[tuple[str, Command]]:
    """Return the current prefix table, rebuilding if COMMANDS/COMMAND_INDEX
    were monkeypatched (e.g. by tests). Identity-keyed cache so production
    callers pay zero cost."""
    global _PREFIX_TABLE, _PREFIX_TABLE_KEY
    key = (id(COMMANDS), id(COMMAND_INDEX))
    if key != _PREFIX_TABLE_KEY:
        _PREFIX_TABLE = _build_prefix_table()
        _PREFIX_TABLE_KEY = key
    return _PREFIX_TABLE


_PREFIX_TABLE_KEY: tuple[int, int] = (id(COMMANDS), id(COMMAND_INDEX))


def _get_trust(char: Character) -> int:
    """Return the effective trust level mirroring ROM's `get_trust`."""

    try:
        trust = int(getattr(char, "trust", 0) or 0)
    except Exception:
        trust = 0
    if trust > 0:
        return trust
    try:
        level = int(getattr(char, "level", 0) or 0)
    except Exception:
        level = 0
    return level


def resolve_command(name: str, *, trust: int | None = None) -> Command | None:
    name = name.lower()
    # ROM has no exact-match shortcut (src/interp.c:442-453): interpret()
    # walks cmd_table linearly and the first row whose name starts with
    # the input AND whose level <= trust wins. An exact-name input is
    # naturally handled — the entry's own name is its own longest prefix
    # — but ordering matters: e.g. "go" must resolve to "goto" not the
    # later "go" cmd_table row, because "goto" appears earlier.
    for rom_name, cmd in _prefix_table():
        if not rom_name.startswith(name):
            continue
        if trust is not None and trust < cmd.min_trust:
            continue
        return cmd
    return None


def _split_command_and_args(input_str: str) -> tuple[str, str]:
    """Extract the leading command token and its remaining arguments."""

    stripped = input_str.lstrip()
    if not stripped:
        return "", ""

    first = stripped[0]
    # Handle special case for @ commands (admin commands like @teleport, @who, etc.)
    if first == "@":
        # For @ commands, split normally by whitespace to preserve full command names
        try:
            parts = shlex.split(stripped)
            if not parts:
                return "", ""
            head = parts[0]
            tail = " ".join(parts[1:]) if len(parts) > 1 else ""
            return head, tail
        except ValueError:
            fallback = stripped.split(None, 1)
            if not fallback:
                return "", ""
            head = fallback[0]
            tail = fallback[1] if len(fallback) > 1 else ""
            return head, tail
    elif not first.isalnum():
        return first, stripped[1:].lstrip()

    try:
        parts = shlex.split(stripped)
        if not parts:
            return "", ""
        head = parts[0]
        tail = " ".join(parts[1:]) if len(parts) > 1 else ""
        return head, tail
    except ValueError:
        fallback = stripped.split(None, 1)
        if not fallback:
            return "", ""
        head = fallback[0]
        tail = fallback[1] if len(fallback) > 1 else ""
        return head, tail


ALIAS_BLOCKED_PREFIXES = ("alias", "una", "prefix")


def _expand_aliases(char: Character, input_str: str, *, max_depth: int = 5) -> tuple[str, bool]:
    """Expand the first token using per-character aliases, up to max_depth.

    Returns the expanded string and whether any alias substitution occurred.

    ROM C parity: alias expansion is blocked for commands starting with
    "alias", "una" (unalias), or "prefix" (src/alias.c:63-69).
    """
    head, _ = _split_command_and_args(input_str)
    if head:
        lowered = head.lower()
        for blocked in ALIAS_BLOCKED_PREFIXES:
            if lowered.startswith(blocked):
                return input_str, False

    s = input_str
    alias_used = False
    for _ in range(max_depth):
        head, tail = _split_command_and_args(s)
        if not head:
            return s, alias_used
        expansion = char.aliases.get(head)
        if not expansion:
            return s, alias_used
        alias_used = True
        s = expansion + (" " + tail if tail else "")
    return s, alias_used


def process_command(char: Character, input_str: str) -> str:
    session = getattr(char, "desc", None)
    if isinstance(session, Session):
        if session.editor == "redit":
            return handle_redit_command(char, session, input_str)
        if session.editor == "aedit":
            return handle_aedit_command(char, session, input_str)
        if session.editor == "oedit":
            return handle_oedit_command(char, session, input_str)
        if session.editor == "medit":
            return handle_medit_command(char, session, input_str)
        if session.editor == "hedit":
            return handle_hedit_command(char, session, input_str)

    if not input_str.strip():
        # mirroring ROM src/interp.c:401-404 — interpret() strips leading
        # whitespace and returns silently on empty input.
        return ""

    remover = getattr(char, "remove_affect", None)
    if callable(remover):
        remover(AffectFlag.HIDE)
    else:
        affected = getattr(char, "affected_by", None)
        if affected is not None:
            try:
                char.affected_by = int(affected) & ~int(AffectFlag.HIDE)
            except Exception:
                pass

    act_bits = getattr(char, "act", 0)
    try:
        act_value = int(act_bits or 0)
    except Exception:
        act_value = 0
    if not getattr(char, "is_npc", False) and act_value & int(PlayerFlag.FREEZE):
        return "You're totally frozen!"

    trimmed = input_str.lstrip()
    # mirroring ROM src/interp.c:491-496 — forward the logline (input minus
    # leading whitespace, prefixed with "% ") to ch->desc->snoop_by.
    desc = getattr(char, "desc", None)
    snoop_desc = getattr(desc, "snoop_by", None) if desc is not None else None
    snooper = getattr(snoop_desc, "character", None) if snoop_desc is not None else None
    if snooper is not None and trimmed:
        snooper_messages = getattr(snooper, "messages", None)
        if snooper_messages is not None:
            snooper_messages.append(f"% {trimmed.rstrip()}")
    core = trimmed.rstrip()
    trailing_ws = trimmed[len(core) :]
    prefix_text = (getattr(char, "prefix", "") or "").strip()
    prefixed_applied = False
    if prefix_text:
        head, _ = _split_command_and_args(core)
        lowered = head.lower()
        blocked_prefixes = ("alias", "una", "pref")
        if lowered and not any(lowered.startswith(block) for block in blocked_prefixes):
            core = f"{prefix_text} {core}" if core else prefix_text
            prefixed_applied = True
    if core:
        raw_parts = core.split(None, 1)
        raw_head = raw_parts[0]
        raw_tail = raw_parts[1] if len(raw_parts) > 1 else ""
    else:
        raw_head = ""
        raw_tail = ""
    expanded, alias_used = _expand_aliases(char, core)
    cmd_name, arg_str = _split_command_and_args(expanded)
    if not cmd_name:
        return "What?"
    trust = _get_trust(char)
    lowered_name = cmd_name.lower()
    command = resolve_command(cmd_name, trust=trust)
    if command and trust < command.min_trust:
        command = None
    if alias_used:
        log_line = expanded + trailing_ws
    elif prefixed_applied:
        log_line = core + trailing_ws
    else:
        log_line = trimmed
    log_all_enabled = is_log_all_enabled()
    log_allowed = True
    should_log = False
    if command:
        if command.log_level is LogLevel.NEVER and not log_all_enabled:
            log_allowed = False
        if command.log_level is LogLevel.ALWAYS:
            should_log = True
    is_player = not getattr(char, "is_npc", False)
    if is_player and getattr(char, "log_commands", False):
        should_log = True
    if log_all_enabled:
        should_log = True
    if should_log and log_allowed and log_line:
        try:
            log_admin_command(
                getattr(char, "name", "?"),
                log_line,
                character=char,
            )
        except Exception:
            # Logging must never break command execution.
            pass
    if not command:
        if lowered_name == "immtalk" or cmd_name == ":":
            return do_immtalk(char, arg_str)
        # mirroring ROM src/interp.c:584-592 — str_prefix social lookup.
        social = find_social(lowered_name)
        if social:
            return perform_social(char, cmd_name, arg_str)
        imc_response = try_imc_command(char, cmd_name, arg_str)
        if imc_response is not None:
            return imc_response
        return "Huh?"
    if command.admin_only and not getattr(char, "is_admin", False):
        return "You do not have permission to use this command."
    # Position gating (ROM-compatible messages)
    if char.position < command.min_position:
        pos = char.position
        if pos == Position.DEAD:
            return "Lie still; you are DEAD."
        if pos in (Position.MORTAL, Position.INCAP):
            return "You are hurt far too bad for that."
        if pos == Position.STUNNED:
            return "You are too stunned to do that."
        if pos == Position.SLEEPING:
            return "In your dreams, or what?"
        if pos == Position.RESTING:
            return "Nah... You feel too relaxed..."
        if pos == Position.SITTING:
            return "Better stand up first."
        if pos == Position.FIGHTING:
            return "No way!  You are still fighting!"
        # Fallback (should not happen)
        return "You can't do that right now."
    command_args = arg_str
    if command.name == "prefix":
        command_args = raw_tail
    return command.func(char, command_args)


def run_test_session() -> list[str]:
    from mud.spawning.obj_spawner import spawn_object
    from mud.world import create_test_character, initialize_world

    initialize_world("area/area.lst")
    # Start in Temple Square (3005) so the scripted "north" walk has a
    # destination — Temple of Mota (3001) has no north exit in the loaded
    # area data.
    char = create_test_character("Tester", 3005)
    # Ensure sufficient movement points for the scripted walk
    char.move = char.max_move = 100
    sword = spawn_object(3022)
    if sword:
        char.room.add_object(sword)
    commands = ["look", "get sword", "north", "say hello"]
    outputs = []
    for line in commands:
        outputs.append(process_command(char, line))
    return outputs
