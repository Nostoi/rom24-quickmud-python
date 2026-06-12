"""
Immortal wizard commands - load, purge, restore, slay.

ROM Reference: src/act_wiz.c, src/fight.c
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mud.commands.imm_commands import MAX_LEVEL, get_char_room, get_char_world, get_trust
from mud.mob_cmds import _extract_character
from mud.models.character import Character
from mud.models.constants import ActFlag, ExtraFlag
from mud.utils.act import act_format, act_to_room

if TYPE_CHECKING:
    pass


def do_load(char: Character, args: str) -> str:
    """
    Load a mobile or object into the game.

    ROM Reference: src/act_wiz.c do_load (lines 2459-2486)

    Usage:
    - load mob <vnum>          - Load a mobile
    - load obj <vnum> [level]  - Load an object
    """
    # mirrors ROM src/act_wiz.c:2465-2470
    if not args or not args.strip():
        return "Syntax:\n\r  load mob <vnum>\n\r  load obj <vnum> <level>\n\r"

    parts = args.strip().split()
    load_type = parts[0].lower()

    if load_type in ("mob", "char"):
        if len(parts) < 2:
            return "Syntax: load mob <vnum>.\n\r"
        return do_mload(char, parts[1])

    if load_type == "obj":
        if len(parts) < 2:
            return "Syntax: load obj <vnum> <level>.\n\r"
        level_arg = parts[2] if len(parts) > 2 else None
        return do_oload(char, parts[1], level_arg)

    # mirrors ROM src/act_wiz.c:2484-2486
    return do_load(char, "")


def do_mload(char: Character, vnum_arg: str) -> str:
    """
    Load a mobile by vnum.

    ROM Reference: src/act_wiz.c do_mload (lines 2489-2517)
    """
    # mirrors ROM src/act_wiz.c:2498-2501
    if not vnum_arg or not vnum_arg.isdigit():
        return "Syntax: load mob <vnum>.\n\r"

    vnum = int(vnum_arg)

    from mud import registry

    # mirrors ROM src/act_wiz.c:2504-2507
    # WIZLOAD-001: canonical attribute is ``mob_registry`` (not
    # ``mob_prototypes``). Prior name typo always early-returned.
    mob_index = getattr(registry, "mob_registry", {}).get(vnum)
    if mob_index is None:
        return "No mob has that vnum.\n\r"

    # Create the mobile
    from mud.spawning.mob_spawner import spawn_mob

    victim = spawn_mob(vnum)

    if victim is None:
        return "No mob has that vnum.\n\r"

    # Place in room
    room = getattr(char, "room", None)
    if room:
        victim.room = room
        people = getattr(room, "people", None)
        if people is None:
            room.people = []
        room.people.append(victim)

    # BCAST-014: TO_ROOM broadcast mirroring ROM
    # src/act_wiz.c:2512 act("$n has created $N!", ch, NULL, victim, TO_ROOM).
    # INV-025/INV-027: act_to_room renders $n per recipient (invisible loader →
    # "Someone") and dispatches TRIG_ACT; $N is the created mob (always visible).
    proto_short = getattr(getattr(victim, "prototype", None), "short_descr", None)
    victim_short = getattr(victim, "short_descr", None) or proto_short or getattr(victim, "name", None) or "something"
    if room is not None:
        act_to_room(room, "$n has created $N!", char, arg2=victim)

    # mirrors ROM src/act_wiz.c:2512-2515
    _send_to_char(char, "Ok.\n\r")
    from mud.wiznet import WiznetFlag, wiznet

    wiznet(f"$N loads {victim_short}.", char, None, WiznetFlag.WIZ_LOAD, WiznetFlag.WIZ_SECURE, get_trust(char))
    return "Ok.\n\r"


def do_oload(char: Character, vnum_arg: str, level_arg: str | None = None) -> str:
    """
    Load an object by vnum.

    ROM Reference: src/act_wiz.c do_oload (lines 2521-2570)
    """
    # mirrors ROM src/act_wiz.c:2531-2534
    if not vnum_arg or not vnum_arg.isdigit():
        return "Syntax: load obj <vnum> <level>.\n\r"

    vnum = int(vnum_arg)
    # mirrors ROM src/act_wiz.c:2537 — default level is trust
    level = get_trust(char)

    if level_arg:
        # mirrors ROM src/act_wiz.c:2539-2552
        if not level_arg.isdigit():
            return "Syntax: load obj <vnum> <level>.\n\r"
        level = int(level_arg)
        if level < 0 or level > get_trust(char):
            return "Level must be be between 0 and your level.\n\r"

    from mud import registry

    # mirrors ROM src/act_wiz.c:2555-2558
    # WIZLOAD-001: canonical attribute is ``obj_registry`` and the
    # spawner is ``spawn_object`` (no level arg). Prior names always
    # early-returned or ImportErrored.
    obj_index = getattr(registry, "obj_registry", {}).get(vnum)
    if obj_index is None:
        return "No object has that vnum.\n\r"

    # Create the object
    from mud.spawning.obj_spawner import spawn_object

    obj = spawn_object(vnum)
    if obj is not None:
        # mirrors ROM src/act_wiz.c:2560 obj = create_object(pObjIndex, level)
        obj.level = level

    if obj is None:
        return "No object has that vnum.\n\r"

    # mirrors ROM src/act_wiz.c:2562-2565
    wear_flags = getattr(obj, "wear_flags", 0)
    if not hasattr(obj, "wear_flags"):
        proto = getattr(obj, "prototype", None)
        if proto:
            wear_flags = getattr(proto, "wear_flags", 0)

    ITEM_TAKE = 1
    if wear_flags & ITEM_TAKE:
        # INV-039 / class-13: ROM src/act_wiz.c obj_to_char head-inserts.
        add_obj = getattr(char, "add_object", None)
        if callable(add_obj):
            add_obj(obj)
        else:
            inventory = getattr(char, "inventory", None)
            if inventory is None:
                char.inventory = []
            inventory = char.inventory
            inventory.insert(0, obj)
        obj.carried_by = char
    else:
        room = getattr(char, "room", None)
        if room:
            # INV-039 / class-13: ROM src/act_wiz.c obj_to_room head-inserts.
            room.add_object(obj)
            obj.in_room = room

    # BCAST-015: TO_ROOM broadcast mirroring ROM
    # src/act_wiz.c:2566 act("$n has created $p!", ch, obj, NULL, TO_ROOM).
    # INV-025/INV-027: act_to_room renders $n per recipient (invisible loader →
    # "Someone") and dispatches TRIG_ACT; $p is the created object.
    actor_room = getattr(char, "room", None)
    if actor_room is not None:
        act_to_room(actor_room, "$n has created $p!", char, arg1=obj)

    # mirrors ROM src/act_wiz.c:2566-2568
    from mud.wiznet import WiznetFlag, wiznet

    wiznet("$N loads $p.", char, obj, WiznetFlag.WIZ_LOAD, WiznetFlag.WIZ_SECURE, get_trust(char))
    return "Ok.\n\r"


def do_purge(char: Character, args: str) -> str:
    """
    Purge mobiles and objects from a room, or a specific target.

    ROM Reference: src/act_wiz.c do_purge (lines 2574-2648)

    Usage:
    - purge           - Purge all mobs/objects in room
    - purge <target>  - Purge specific mob or player (kicks them)
    """
    room = getattr(char, "room", None)
    if not room:
        return "You're not in a room.\n\r"

    if not args or not args.strip():
        # mirrors ROM src/act_wiz.c:2584-2607 — purge room
        people = list(getattr(room, "people", []))
        for victim in people:
            if victim is char:
                continue
            if not getattr(victim, "is_npc", False):
                continue
            act_flags = getattr(victim, "act", 0)
            if act_flags & int(ActFlag.NOPURGE):
                continue
            # PURGE-001: route through the canonical extract_char
            # chokepoint so nuke_pets + die_follower run (INV-020).
            # Mirrors ROM src/act_wiz.c:2595 extract_char(victim, TRUE).
            _extract_character(victim)

        contents = list(getattr(room, "contents", []))
        for obj in contents:
            extra_flags = getattr(obj, "extra_flags", 0)
            if extra_flags & int(ExtraFlag.NOPURGE):
                continue
            _extract_obj(obj)

        # BCAST-035: TO_ROOM mirroring ROM src/act_wiz.c:2605 —
        # act("$n purges the room!", ch, NULL, NULL, TO_ROOM). INV-025/INV-027:
        # act_to_room renders $n per recipient (invisible purger → "Someone") and
        # dispatches TRIG_ACT. The act() fires after purge extraction, so only
        # remaining NPCs (ACT_NOPURGE) can receive it.
        act_to_room(room, "$n purges the room!", char)

        return "Ok.\n\r"

    # Purge specific target
    target_name = args.strip().split()[0]
    # mirrors ROM src/act_wiz.c:2610-2613
    victim = get_char_world(char, target_name)

    if victim is None:
        return "They aren't here.\n\r"

    if not getattr(victim, "is_npc", False):
        # mirrors ROM src/act_wiz.c:2619-2622
        if victim is char:
            return "Ho ho ho.\n\r"

        # mirrors ROM src/act_wiz.c:2625-2631
        if get_trust(char) <= get_trust(victim):
            _send_to_char(victim, f"{getattr(char, 'name', 'Someone')} tried to purge you!\n\r")
            return "Maybe that wasn't a good idea...\n\r"

        # BCAST-035: TO_NOTVICT mirroring ROM src/act_wiz.c:2633 —
        # act("$n disintegrates $N.", ch, 0, victim, TO_NOTVICT). INV-025/INV-027:
        # act_to_room renders $n per recipient (invisible actor → "Someone") and
        # dispatches TRIG_ACT; act_to_room auto-excludes the actor and exclude=victim
        # gives ROM TO_NOTVICT (victim is about to be extracted).
        act_to_room(room, "$n disintegrates $N.", char, arg2=victim, exclude=victim)

        # PURGE-001: route through canonical chokepoint (INV-020).
        # Mirrors ROM src/act_wiz.c:2638 extract_char(victim, TRUE).
        _extract_character(victim)
        return "Ok.\n\r"

    # BCAST-035: TO_NOTVICT mirroring ROM src/act_wiz.c:2645 —
    # act("$n purges $N.", ch, NULL, victim, TO_NOTVICT). INV-025/INV-027:
    # act_to_room renders $n per recipient (invisible actor → "Someone") and
    # dispatches TRIG_ACT; act_to_room auto-excludes the actor and exclude=victim
    # gives ROM TO_NOTVICT (victim is about to be extracted).
    npc_room = getattr(char, "room", None)
    if npc_room is not None:
        act_to_room(npc_room, "$n purges $N.", char, arg2=victim, exclude=victim)

    # Purge NPC — mirrors ROM src/act_wiz.c:2645-2647 extract_char(victim, TRUE).
    _extract_character(victim)
    return "Ok.\n\r"


def do_restore(char: Character, args: str) -> str:
    """
    Restore a character to full health/mana/move and remove afflictions.

    ROM Reference: src/act_wiz.c do_restore (lines 2785-2869)

    Usage:
    - restore         - Restore everyone in room
    - restore room    - Restore everyone in room
    - restore <char>  - Restore specific character
    - restore all     - Restore all online players (MAX_LEVEL - 1 required)
    """
    # mirrors ROM src/act_wiz.c:2792-2817
    if not args or not args.strip() or args.strip().lower() == "room":
        room = getattr(char, "room", None)
        if not room:
            return "You're not in a room.\n\r"

        for victim in list(getattr(room, "people", [])):
            _restore_char(victim)
            # mirrors ROM src/act_wiz.c:2809 — act("$n has restored you.", ch,
            # NULL, victim, TO_VICT). INV-025/INV-027: act_format PERS-masks an
            # invisible restorer per the victim's sight; self-restore renders the
            # name (ROM PERS(ch,ch) → name, can_see(self) is TRUE).
            message = act_format("$n has restored you.", recipient=victim, actor=char)
            _send_to_char(victim, f"{message}\n\r")
            if getattr(victim, "is_npc", False):
                # ROM src/act_wiz.c:2809 / src/comm.c:2384 — TO_VICT act()
                # on NPC victims dispatches TRIG_ACT.
                import mud.mobprog as mobprog

                mobprog.mp_act_trigger(message, victim, char, None, victim, mobprog.Trigger.ACT)

        from mud.wiznet import WiznetFlag, wiznet

        wiznet(
            f"$N restored room {getattr(room, 'vnum', 0)}.",
            char,
            None,
            WiznetFlag.WIZ_RESTORE,
            WiznetFlag.WIZ_SECURE,
            get_trust(char),
        )

        return "Room restored.\n\r"

    arg = args.strip().lower()

    # mirrors ROM src/act_wiz.c:2820-2845
    if arg == "all":
        if get_trust(char) < MAX_LEVEL - 1:
            return "Not at your level!\n\r"

        from mud import registry

        # mirrors ROM src/act_wiz.c:2842 — act("$n has restored you.", ch, NULL,
        # victim, TO_VICT). INV-025/INV-027: PERS-mask the restorer per victim sight.
        # INV-046: descriptor_list is the ONLY structure ROM walks here
        # (src/act_wiz.c:2825-2844); the old phantom registry.players fallback
        # could never fire in production and is gone.
        for desc in getattr(registry, "descriptor_list", []):
            victim = getattr(desc, "character", None)
            if victim is None or getattr(victim, "is_npc", False):
                continue
            _restore_char(victim)
            _send_to_char(victim, f"{act_format('$n has restored you.', recipient=victim, actor=char)}\n\r")

        return "All active players restored.\n\r"

    # mirrors ROM src/act_wiz.c:2848-2868
    victim = get_char_world(char, args.strip())
    if victim is None:
        return "They aren't here.\n\r"

    _restore_char(victim)
    # mirrors ROM src/act_wiz.c:2863 — act("$n has restored you.", ch, NULL,
    # victim, TO_VICT). INV-025/INV-027: PERS-mask the restorer per victim sight.
    message = act_format("$n has restored you.", recipient=victim, actor=char)
    _send_to_char(victim, f"{message}\n\r")
    if getattr(victim, "is_npc", False):
        # ROM src/act_wiz.c:2863 / src/comm.c:2384 — TO_VICT act() on NPC
        # victims dispatches TRIG_ACT.
        import mud.mobprog as mobprog

        mobprog.mp_act_trigger(message, victim, char, None, victim, mobprog.Trigger.ACT)

    from mud.wiznet import WiznetFlag, wiznet

    victim_name = (
        getattr(victim, "short_descr", None) if getattr(victim, "is_npc", False) else getattr(victim, "name", "someone")
    )
    wiznet(f"$N restored {victim_name}", char, None, WiznetFlag.WIZ_RESTORE, WiznetFlag.WIZ_SECURE, get_trust(char))

    return "Ok.\n\r"


def do_slay(char: Character, args: str) -> str:
    """
    Instantly kill a target.

    ROM Reference: src/fight.c do_slay (lines 3252-3290)

    Usage: slay <target>
    """
    if not args or not args.strip():
        return "Slay whom?"

    target_name = args.strip().split()[0]
    victim = get_char_room(char, target_name)

    if victim is None:
        return "They aren't here."

    if victim is char:
        return "Suicide is a mortal sin."

    # Check trust for players
    if not getattr(victim, "is_npc", False):
        if getattr(victim, "level", 1) >= get_trust(char):
            return "You failed."

    # Slay the victim
    victim_name = getattr(victim, "name", "someone")
    victim_short = getattr(victim, "short_descr", None) or victim_name
    char_name = getattr(char, "name", "someone")

    # SLAY-002: broadcast TO_VICT and TO_NOTVICT before raw_kill removes
    # the victim from the room. Mirrors ROM src/fight.c:3282-3284 — the
    # three act() calls fire in CHAR/VICT/NOTVICT order before raw_kill.
    _send_to_char(victim, f"{char_name} slays you in cold blood!\n\r")
    room = getattr(char, "room", None)
    if room is not None:
        for bystander in list(getattr(room, "people", [])):
            if bystander is char or bystander is victim:
                continue
            _send_to_char(bystander, f"{char_name} slays {victim_short} in cold blood!\n\r")

    # SLAY-001: route through raw_kill so the slain victim gets the
    # full death pipeline — corpse, death_cry, gold/silver drop, and
    # INV-020 cleanup chain (nuke_pets + die_follower). Mirrors ROM
    # src/fight.c:3285 raw_kill(victim). The previous local
    # _extract_char stub only stopped fighting and unlinked from the
    # room, leaking pets/followers and producing no corpse.
    from mud.combat.death import raw_kill

    raw_kill(victim)

    return f"You slay {victim_name} in cold blood!"


def do_sla(char: Character, args: str) -> str:
    """
    Typo guard for slay - prevents accidental slaying.

    ROM Reference: interp.c - sla is a separate command that does nothing
    """
    return "If you want to SLAY, spell it out."


# Helper functions


def _restore_char(char: Character) -> None:
    """Fully restore a character.

    Mirrors ROM ``src/act_wiz.c:2807, 2839, 2861`` — strip the five named
    negative affects, then refill hit/mana/move and re-evaluate position.
    """
    # RESTORE-001: strip the five negative affects ROM cures.
    for affect_name in ("plague", "poison", "blindness", "sleep", "curse"):
        char.strip_affect(affect_name)

    # Restore stats
    char.hit = getattr(char, "max_hit", 100)
    char.mana = getattr(char, "max_mana", 100)
    char.move = getattr(char, "max_move", 100)

    # Update position
    from mud.models.constants import Position

    if getattr(char, "position", Position.STANDING) < Position.STANDING:
        char.position = Position.STANDING


# DUPL-003 — canonical at mud/game_loop.py:_extract_obj.
from mud.game_loop import _extract_obj  # noqa: E402

# DUPL-001a — canonical at mud/utils/messaging.py:send_to_char_buffered.
from mud.utils.messaging import send_to_char_buffered as _send_to_char  # noqa: E402
