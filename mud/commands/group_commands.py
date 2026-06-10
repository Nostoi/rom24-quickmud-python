"""
Group-related commands: follow, group, gtell, order, split.

ROM Reference: src/act_comm.c (follow, group, order, gtell, split)
"""

from __future__ import annotations

from mud.characters.follow import add_follower, stop_follower
from mud.models.character import Character
from mud.models.constants import AffectFlag, PlayerFlag
from mud.world.char_find import get_char_room


def _send_to_char_sync(character: Character, message: str) -> None:
    """Single-channel delivery (mirrors AGENTS.md Message Delivery / ROM write_to_buffer).

    INV-001: push_message routes a connected char to the async send and the
    mailbox only for disconnected chars (XOR). The prior if-writer-async +
    unconditional append double-delivered to a connected PC.
    """
    from mud.utils.messaging import push_message

    push_message(character, message)


def _pers_gated(actor: Character, viewer: Character) -> str:
    """ROM ``pers(ch, vict)`` — returns actor's name to viewer, or "someone" if blind.

    Mirrors ROM ``src/handler.c:pers`` visibility gating used by ``act()``.
    """
    from mud.world.vision import can_see_character

    if not can_see_character(viewer, actor):
        return "someone"
    name = getattr(actor, "name", None)
    if isinstance(name, str) and name:
        return name
    short_descr = getattr(actor, "short_descr", None)
    if isinstance(short_descr, str) and short_descr:
        return short_descr
    return "someone"


def _display_name(character: Character | None) -> str:
    if character is None:
        return "Someone"
    name = getattr(character, "name", None)
    if isinstance(name, str) and name:
        return name
    short_descr = getattr(character, "short_descr", None)
    if isinstance(short_descr, str) and short_descr:
        return short_descr
    return "Someone"


def is_same_group(ach: Character, bch: Character) -> bool:
    """
    Check if two characters are in the same group.

    ROM Reference: src/act_comm.c:2018-2028 is_same_group — pointer
    identity comparison, not field equality.
    """
    if ach is None or bch is None:
        return False

    aleader = getattr(ach, "leader", None) or ach
    bleader = getattr(bch, "leader", None) or bch

    return aleader is bleader


def do_follow(char: Character, args: str) -> str:
    """
    Follow another character.

    ROM Reference: src/act_comm.c do_follow (lines 1536-1595)

    Usage:
    - follow <target> - Start following target
    - follow self - Stop following
    """
    args = args.strip()

    if not args:
        return "Follow whom?"

    # Find target in room
    victim = get_char_room(char, args)
    if not victim:
        return "They aren't here."

    # Check if charmed - can't change who you follow
    affected_by = getattr(char, "affected_by", 0)
    if affected_by & AffectFlag.CHARM and char.master is not None:
        master_name = getattr(char.master, "short_descr", None) or getattr(char.master, "name", "your master")
        return f"But you'd rather follow {master_name}!"

    # Following self = stop following
    if victim is char:
        if char.master is None:
            return "You already follow yourself."
        # mirroring ROM src/act_comm.c:1569-1570 — the self-target branch calls
        # stop_follower and returns SILENTLY; stop_follower is the sole emitter
        # of "You stop following $N." (with the master's name). Returning a bare
        # TO_CHAR string here would double the message (ACT_COMM-001).
        stop_follower(char)
        return ""

    # Check NOFOLLOW flag on target
    is_npc = getattr(victim, "is_npc", True)
    if not is_npc:
        act_flags = getattr(victim, "act", 0)
        if act_flags & PlayerFlag.NOFOLLOW:
            victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "They")
            return f"{victim_name} doesn't seem to want any followers."

    # Remove NOFOLLOW from self
    if not getattr(char, "is_npc", True):
        char.act = getattr(char, "act", 0) & ~PlayerFlag.NOFOLLOW

    # Stop following current master first
    if char.master is not None:
        stop_follower(char)

    # Start following new master
    # mirroring ROM src/act_comm.c:1586-1587 — the success path calls add_follower
    # and `return;` (void). add_follower's act("You now follow $N.", …TO_CHAR)
    # (src/act_comm.c:1605) is the SOLE emitter of the follower's confirmation;
    # it already appended the named line to char.messages. Returning a TO_CHAR
    # string here too would double the message (ACT_COMM-002).
    add_follower(char, victim)
    return ""


def do_group(char: Character, args: str) -> str:
    """
    Manage group membership.

    ROM Reference: src/act_comm.c do_group (lines 1770-1850)

    Usage:
    - group - Show group status
    - group <target> - Add/remove target from group
    """
    args = args.strip()

    # No argument - show group status
    if not args:
        # Determine leader
        leader = char.leader if char.leader else char
        leader_name = getattr(leader, "short_descr", None) or getattr(leader, "name", "Someone")

        lines = [f"{leader_name}'s group:"]

        # Find all group members
        members_found = []
        seen_ids = set()

        def add_member(gch):
            if id(gch) not in seen_ids:
                members_found.append(gch)
                seen_ids.add(id(gch))

        # Always include self
        if is_same_group(char, char):
            add_member(char)

        # Check room for group members
        room = getattr(char, "room", None)
        if room:
            for occupant in getattr(room, "people", []):
                if is_same_group(occupant, char):
                    add_member(occupant)

        # Check followers
        if hasattr(leader, "followers"):
            for follower in leader.followers:
                if is_same_group(follower, char):
                    add_member(follower)

        # Also include leader
        add_member(leader)

        for gch in members_found:
            gch_name = getattr(gch, "short_descr", None) or getattr(gch, "name", "someone")
            gch_level = getattr(gch, "level", 1)
            is_npc = getattr(gch, "is_npc", False)
            class_name = "Mob" if is_npc else getattr(gch, "class_name", "???")[:3]

            hit = getattr(gch, "hit", 100)
            max_hit = getattr(gch, "max_hit", 100)
            mana = getattr(gch, "mana", 100)
            max_mana = getattr(gch, "max_mana", 100)
            move = getattr(gch, "move", 100)
            max_move = getattr(gch, "max_move", 100)
            exp = getattr(gch, "exp", 0)

            lines.append(
                f"[{gch_level:2d} {class_name:3s}] {gch_name:16s} "
                f"{hit:4d}/{max_hit:4d} hp {mana:4d}/{max_mana:4d} mana "
                f"{move:4d}/{max_move:4d} mv {exp:5d} xp"
            )

        return "\n".join(lines)

    # Argument provided - add/remove from group
    victim = get_char_room(char, args)
    if not victim:
        return "They aren't here."

    # Check if char is leader (not following anyone else)
    if char.master is not None or (char.leader is not None and char.leader is not char):
        return "But you are following someone else!"

    # Can't group someone who isn't following you (unless it's yourself)
    if victim.master is not char and char is not victim:
        victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "They")
        return f"{victim_name} isn't following you."

    # Can't remove charmed mobs
    affected_by = getattr(victim, "affected_by", 0)
    if affected_by & AffectFlag.CHARM:
        return "You can't remove charmed mobs from your group."

    # Check if char is charmed
    char_affected = getattr(char, "affected_by", 0)
    if char_affected & AffectFlag.CHARM:
        return "You like your master too much to leave!"

    leader_name = _display_name(char)
    victim_name_str = _display_name(victim)

    # Already in group - remove (ROM src/act_comm.c:1838-1847)
    if is_same_group(victim, char) and char is not victim:
        victim.leader = None
        # mirroring ROM src/act_comm.c:1842-1846 — TO_VICT and TO_NOTVICT via act()
        _send_to_char_sync(victim, f"{leader_name} removes you from {leader_name}'s group.")
        room = getattr(char, "room", None)
        if room is not None:
            notvict_msg = f"{leader_name} removes {victim_name_str} from {leader_name}'s group."
            for occupant in list(getattr(room, "people", []) or []):
                if occupant is char or occupant is victim:
                    continue
                _send_to_char_sync(occupant, notvict_msg)
        return f"You remove {victim_name_str} from your group."

    # Add to group (ROM src/act_comm.c:1850-1854)
    victim.leader = char
    # mirroring ROM src/act_comm.c:1850-1854 — TO_VICT and TO_NOTVICT via act()
    _send_to_char_sync(victim, f"You join {leader_name}'s group.")
    room = getattr(char, "room", None)
    if room is not None:
        notvict_msg = f"{victim_name_str} joins {leader_name}'s group."
        for occupant in list(getattr(room, "people", []) or []):
            if occupant is char or occupant is victim:
                continue
            _send_to_char_sync(occupant, notvict_msg)
    return f"{victim_name_str} joins your group."


def do_gtell(char: Character, args: str) -> str:
    """
    Send a message to all group members.

    ROM Reference: src/act_comm.c lines 1984-2008 (do_gtell)

    Usage: gtell <message>
    """
    from mud.models.character import character_registry
    from mud.models.constants import CommFlag
    from mud.net.protocol import send_to_char

    args = args.strip()

    if not args:
        return "Tell your group what?"

    # ROM C lines 1994-1998: Check COMM_NOTELL flag
    comm_flags = int(getattr(char, "comm", 0) or 0)
    if comm_flags & CommFlag.NOTELL:
        return "Your message didn't get through!"

    # ROM C lines 2000-2005: Broadcast to all group members
    char_name = getattr(char, "short_descr", None) or getattr(char, "name", "Someone")

    for gch in list(character_registry):
        if is_same_group(gch, char):
            # Send message to group member (ROM C: act_new("$n tells the group '$t'", ...))
            message = f"{char_name} tells the group '{args}'"
            send_to_char(message, gch)

    return f"You tell the group '{args}'"


def do_split(char: Character, args: str) -> str:
    """Split silver and gold among group members in the room.

    ROM Reference: src/act_comm.c do_split (lines 1863-1981).

    Argument forms:
    - ``split <silver>`` -> split that many silver coins
    - ``split <silver> <gold>`` -> split silver AND gold simultaneously

    Legacy QuickMUD callers that used ``"<amount> silver"`` or
    ``"<amount> gold"`` keyword form are still accepted: ``silver``/``coin``/
    ``coins`` is treated as silver-only, ``gold`` as gold-only.
    """
    from mud.math.c_compat import c_div, c_mod

    raw = args.strip()
    parts = raw.split()

    if not parts:
        return "Split how much?"

    # Parse first amount. ROM uses atoi() which returns 0 for non-numeric input.
    try:
        amount_silver = int(parts[0])
    except ValueError:
        amount_silver = 0

    amount_gold = 0
    if len(parts) > 1:
        keyword = parts[1].lower()
        if keyword in ("silver", "coin", "coins"):
            # Legacy keyword form: amount is silver, gold remains 0.
            pass
        elif keyword == "gold":
            # Legacy keyword form: amount was gold-only.
            amount_gold = amount_silver
            amount_silver = 0
        else:
            try:
                amount_gold = int(parts[1])
            except ValueError:
                amount_gold = 0

    # ROM C lines 1881-1885: negative amounts -> "Your group wouldn't like that."
    if amount_silver < 0 or amount_gold < 0:
        return "Your group wouldn't like that."

    # ROM C lines 1887-1891: zero on both -> "You hand out zero coins..."
    if amount_silver == 0 and amount_gold == 0:
        return "You hand out zero coins, but no one notices."

    # ROM C lines 1893-1897: insufficient funds.
    char_silver = int(getattr(char, "silver", 0) or 0)
    char_gold = int(getattr(char, "gold", 0) or 0)
    if char_gold < amount_gold or char_silver < amount_silver:
        return "You don't have that much to split."

    # Count members in room (ROM C lines 1899-1907).
    room = getattr(char, "room", None)
    if not room:
        return "Just keep it all."

    members = 0
    for occupant in getattr(room, "people", []):
        if not is_same_group(occupant, char):
            continue
        occupant_aff = int(getattr(occupant, "affected_by", 0) or 0)
        if occupant_aff & int(AffectFlag.CHARM):
            continue
        members += 1

    if members < 2:
        return "Just keep it all."

    # Use C integer division/modulo (ROM lines 1915-1919).
    share_silver = c_div(amount_silver, members)
    extra_silver = c_mod(amount_silver, members)
    share_gold = c_div(amount_gold, members)
    extra_gold = c_mod(amount_gold, members)

    # ROM C lines 1921-1924: both shares zero -> cheapskate refusal.
    if share_gold == 0 and share_silver == 0:
        return "Don't even bother, cheapskate."

    # Deduct from char, then add own share + extras (ROM lines 1926-1929).
    char.silver = char_silver - amount_silver + share_silver + extra_silver
    char.gold = char_gold - amount_gold + share_gold + extra_gold

    # Compose the actor's TO_CHAR feedback (ROM lines 1931-1944).
    out_lines: list[str] = []
    if share_silver > 0:
        out_lines.append(f"You split {amount_silver} silver coins. Your share is {share_silver + extra_silver} silver.")
    if share_gold > 0:
        out_lines.append(f"You split {amount_gold} gold coins. Your share is {share_gold + extra_gold} gold.")

    # Build the per-member broadcast (ROM lines 1946-1962).
    # ROM uses act(buf, ch, NULL, gch, TO_VICT) which resolves $n through
    # PERS(ch, gch) per recipient and caps the first letter via act_new
    # (src/comm.c:2376). FIGHT-034: per-recipient PERS + capitalize.
    from mud.utils.act import capitalize_act_line
    from mud.world.vision import pers

    # Distribute to other non-charmed group members in the room.
    for occupant in getattr(room, "people", []):
        if occupant is char or not is_same_group(occupant, char):
            continue
        occupant_aff = int(getattr(occupant, "affected_by", 0) or 0)
        if occupant_aff & int(AffectFlag.CHARM):
            continue
        occupant.silver = int(getattr(occupant, "silver", 0) or 0) + share_silver
        occupant.gold = int(getattr(occupant, "gold", 0) or 0) + share_gold

        # Per-recipient PERS substitution + capitalize (ROM act_new caps buf).
        splitter_name = pers(char, occupant)
        if share_gold == 0:
            member_msg = capitalize_act_line(
                f"{splitter_name} splits {amount_silver} silver coins. Your share is {share_silver} silver."
            )
        elif share_silver == 0:
            member_msg = capitalize_act_line(
                f"{splitter_name} splits {amount_gold} gold coins. Your share is {share_gold} gold."
            )
        else:
            member_msg = capitalize_act_line(
                f"{splitter_name} splits {amount_silver} silver and {amount_gold} "
                f"gold coins, giving you {share_silver} silver and {share_gold} gold."
            )

        # INV-001: _send_to_char_sync already delivers (push_message XOR); the
        # prior extra mailbox append double-delivered the split line.
        _send_to_char_sync(occupant, member_msg)

    return "\n".join(out_lines) if out_lines else ""


def do_order(char: Character, args: str) -> str:
    """
    Order charmed followers to perform an action.

    ROM Reference: src/act_comm.c lines 1684-1766 (do_order)

    Usage:
    - order <target> <command>
    - order all <command>
    """
    import mud.commands.dispatcher as _dispatcher

    args = args.strip()
    parts = args.split(None, 1)

    if len(parts) < 2:
        return "Order whom to do what?"

    target_name, command = parts

    # ROM C lines 1697-1701: Block dangerous commands
    command_parts = command.split(None, 1)
    if command_parts:
        first_word = command_parts[0].lower()
        if first_word in ("delete", "mob"):
            return "That will NOT be done."

    # ROM C lines 1709-1713: Charmed characters can't give orders
    affected_by_char = getattr(char, "affected_by", 0)
    if affected_by_char & AffectFlag.CHARM:
        return "You feel like taking, not giving, orders."

    # Find target(s)
    if target_name.lower() == "all":
        # ROM C lines 1715-1756: Order all charmed followers
        found = False
        room = getattr(char, "room", None)
        if room:
            for occupant in list(getattr(room, "people", [])):
                affected_by = getattr(occupant, "affected_by", 0)
                master = getattr(occupant, "master", None)

                if affected_by & AffectFlag.CHARM and master is char:
                    found = True
                    # mirroring ROM src/act_comm.c:1752-1753 — act() pers(ch, vict) gates $n on visibility
                    actor_name = _pers_gated(char, occupant)
                    order_message = f"{actor_name} orders you to '{command}'."
                    _send_to_char_sync(occupant, order_message)

                    # ROM C line 1754: interpret(och, argument) - Execute command
                    try:
                        _dispatcher.process_command(occupant, command)
                    except Exception:
                        # Silently handle execution errors (ROM C doesn't error-check interpret())
                        pass

        if found:
            # ROM C lines 1760-1761: WAIT_STATE and confirmation
            # Note: WAIT_STATE not implemented yet, just return confirmation
            return "Ok."
        else:
            # ROM C line 1764: No followers
            return "You have no followers here."
    else:
        # ROM C lines 1720-1740: Order single target
        victim = get_char_room(char, target_name)
        if not victim:
            return "They aren't here."

        if victim is char:
            return "Aye aye, right away!"

        # Check if victim is charmed by char
        affected_by = getattr(victim, "affected_by", 0)
        master = getattr(victim, "master", None)

        # ROM C lines 1735-1740: Validate charm and master relationship
        if not (affected_by & AffectFlag.CHARM) or master is not char:
            return "Do it yourself!"

        # mirroring ROM src/act_comm.c:1752-1753 — act() pers(ch, vict) gates $n on visibility
        actor_name = _pers_gated(char, victim)
        order_message = f"{actor_name} orders you to '{command}'."
        _send_to_char_sync(victim, order_message)

        # ROM C line 1754: interpret(och, argument) - Execute command
        try:
            _dispatcher.process_command(victim, command)
        except Exception:
            # Silently handle execution errors (ROM C doesn't error-check interpret())
            pass

        # ROM C lines 1760-1761: WAIT_STATE and confirmation
        return "Ok."
