from __future__ import annotations

import asyncio

from typing import TYPE_CHECKING, cast

from mud import mobprog
from mud.characters import is_clan_member, is_same_clan
from mud.models.character import Character, character_registry
from mud.models.constants import CommFlag, Position
from mud.net.protocol import broadcast_global, broadcast_room, send_to_char
from mud.mobprog import mp_speech_trigger

if TYPE_CHECKING:
    from mud.net.session import Session


def _get_session(char: Character) -> "Session | None":
    """Return the active session backing *char* when connected."""

    desc = getattr(char, "desc", None)
    if desc is None:
        return None
    return cast("Session", desc)


def _queue_personal_message(target: Character, message: str) -> None:
    if hasattr(target, "messages"):
        target.messages.append(message)


def _deliver_tell(sender: Character, target: Character, message: str) -> None:
    """Send the formatted tell *message* to *target* and record reply."""

    _queue_personal_message(target, message)
    writer = getattr(target, "connection", None)
    if writer:
        asyncio.create_task(send_to_char(target, message))
    target.reply = sender


def _is_player_linkdead(target: Character) -> bool:
    return bool(not getattr(target, "is_npc", False) and getattr(target, "desc", None) is None)


def _is_player_writing_note(target: Character) -> bool:
    session = _get_session(target)
    if session is None:
        return False
    editor = getattr(session, "editor", None)
    if not editor:
        return False
    normalized = str(editor).lower()
    return normalized.startswith("note")


def _validate_tell_target(sender: Character, target: Character) -> str | None:
    if target is sender:
        return "You tell yourself nothing new."
    if "tell" in target.muted_channels:
        return "They aren't listening."
    if (_has_comm_flag(target, CommFlag.QUIET) or _has_comm_flag(target, CommFlag.DEAF)) and not sender.is_immortal():
        return f"{target.name} is not receiving tells."
    if not sender.is_immortal() and not getattr(target, "is_awake", lambda: True)():
        return "They can't hear you."
    return None


def _handle_buffered_tell(sender: Character, target: Character, message: str) -> str | None:
    formatted = f"{sender.name} tells you, '{message}'"

    if _is_player_linkdead(target):
        _queue_personal_message(target, formatted)
        target.reply = sender
        return f"{target.name} seems to have misplaced their link...try again later."

    if _has_comm_flag(target, CommFlag.AFK):
        if getattr(target, "is_npc", False):
            return f"{target.name} is AFK, and not receiving tells."
        _queue_personal_message(target, formatted)
        target.reply = sender
        return f"{target.name} is AFK, but your tell will go through when they return."

    if _is_player_writing_note(target):
        _queue_personal_message(target, formatted)
        target.reply = sender
        return f"{target.name} is writing a note, but your tell will go through when they return."

    _deliver_tell(sender, target, formatted)
    return None


def _has_comm_flag(char: Character, flag: CommFlag) -> bool:
    if hasattr(char, "has_comm_flag"):
        try:
            return bool(char.has_comm_flag(flag))
        except Exception:
            pass
    try:
        return bool(int(getattr(char, "comm", 0) or 0) & int(flag))
    except Exception:
        return False


def _set_comm_flag(char: Character, flag: CommFlag) -> None:
    if hasattr(char, "set_comm_flag"):
        try:
            char.set_comm_flag(flag)
            return
        except Exception:
            pass
    current = int(getattr(char, "comm", 0) or 0)
    char.comm = current | int(flag)


def _clear_comm_flag(char: Character, flag: CommFlag) -> None:
    if hasattr(char, "clear_comm_flag"):
        try:
            char.clear_comm_flag(flag)
            return
        except Exception:
            pass
    current = int(getattr(char, "comm", 0) or 0)
    char.comm = current & ~int(flag)


def do_say(char: Character, args: str) -> str:
    if not args:
        return "Say what?"
    message = f"{char.name} says, '{args}'"
    if char.room:
        char.room.broadcast(message, exclude=char)
        broadcast_room(char.room, message, exclude=char)
        for mob in list(char.room.people):
            if mob is char or not getattr(mob, "is_npc", False):
                continue
            default_pos = getattr(mob, "default_pos", getattr(mob, "position", Position.STANDING))
            if getattr(mob, "position", default_pos) != default_pos:
                continue
            mobprog.mp_speech_trigger(args, mob, char)
    return f"You say, '{args}'"


def do_tell(char: Character, args: str) -> str:
    if "tell" in char.banned_channels:
        return "You are banned from tell."
    if _has_comm_flag(char, CommFlag.NOCHANNELS):
        return "The gods have revoked your channel privileges."
    if _has_comm_flag(char, CommFlag.NOTELL) or _has_comm_flag(char, CommFlag.DEAF):
        return "Your message didn't get through."
    if _has_comm_flag(char, CommFlag.QUIET):
        return "You must turn off quiet mode first."
    if not args:
        return "Tell whom what?"
    try:
        target_name, message = args.split(None, 1)
    except ValueError:
        return "Tell whom what?"
    target = next(
        (c for c in character_registry if c.name and c.name.lower() == target_name.lower()),
        None,
    )
    if not target:
        return "They aren't here."
    error = _validate_tell_target(char, target)
    if error:
        return error

    buffered_response = _handle_buffered_tell(char, target, message)
    if buffered_response:
        return buffered_response

    if getattr(target, "is_npc", False):
        default_pos = getattr(target, "default_pos", getattr(target, "position", Position.STANDING))
        if getattr(target, "position", default_pos) == default_pos:
            mobprog.mp_speech_trigger(message, target, char)
    return f"You tell {target.name}, '{message}'"


def do_reply(char: Character, args: str) -> str:
    if _has_comm_flag(char, CommFlag.NOTELL):
        return "Your message didn't get through."
    if not args:
        return "Reply to whom with what?"
    target = getattr(char, "reply", None)
    if target is None or target not in character_registry:
        return "They aren't here."
    return do_tell(char, f"{target.name} {args}")


def do_shout(char: Character, args: str) -> str:
    if "shout" in char.banned_channels:
        return "You are banned from shout."
    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.SHOUTSOFF):
            _clear_comm_flag(char, CommFlag.SHOUTSOFF)
            return "You can hear shouts again."
        _set_comm_flag(char, CommFlag.SHOUTSOFF)
        return "You will no longer hear shouts."
    if _has_comm_flag(char, CommFlag.NOCHANNELS):
        return "The gods have revoked your channel privileges."
    if _has_comm_flag(char, CommFlag.QUIET):
        return "You must turn off quiet mode first."
    if _has_comm_flag(char, CommFlag.NOSHOUT):
        return "You can't shout."
    if _has_comm_flag(char, CommFlag.SHOUTSOFF):
        return "You must turn shouts back on first."
    message = f"{char.name} shouts, '{cleaned}'"
    current_wait = getattr(char, "wait", 0) or 0
    char.wait = max(int(current_wait), 12)

    def _should_receive(target: Character) -> bool:
        return not (_has_comm_flag(target, CommFlag.SHOUTSOFF) or _has_comm_flag(target, CommFlag.QUIET))

    broadcast_global(message, channel="shout", exclude=char, should_send=_should_receive)
    return f"You shout, '{cleaned}'"


def _check_channel_blockers(char: Character, toggle_flag: CommFlag) -> str | None:
    if _has_comm_flag(char, CommFlag.QUIET):
        return "You must turn off quiet mode first."
    if _has_comm_flag(char, CommFlag.NOCHANNELS) and toggle_flag != CommFlag.NOWIZ:
        return "The gods have revoked your channel privileges."
    return None


def do_auction(char: Character, args: str) -> str:
    if "auction" in char.banned_channels:
        return "You are banned from auction."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOAUCTION):
            _clear_comm_flag(char, CommFlag.NOAUCTION)
            return "{aAuction channel is now ON.{x"
        _set_comm_flag(char, CommFlag.NOAUCTION)
        return "{aAuction channel is now OFF.{x"

    blocked = _check_channel_blockers(char, CommFlag.NOAUCTION)
    if blocked:
        return blocked

    _clear_comm_flag(char, CommFlag.NOAUCTION)

    def _should_receive(target: Character) -> bool:
        if _has_comm_flag(target, CommFlag.NOAUCTION) or _has_comm_flag(target, CommFlag.QUIET):
            return False
        return True

    broadcast_global(
        f"{{a{char.name} auctions '{{A{cleaned}{{a'{{x",
        channel="auction",
        exclude=char,
        should_send=_should_receive,
    )
    return f"{{aYou auction '{{A{cleaned}{{a'{{x"


def do_gossip(char: Character, args: str) -> str:
    if "gossip" in char.banned_channels:
        return "You are banned from gossip."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOGOSSIP):
            _clear_comm_flag(char, CommFlag.NOGOSSIP)
            return "Gossip channel is now ON."
        _set_comm_flag(char, CommFlag.NOGOSSIP)
        return "Gossip channel is now OFF."

    blocked = _check_channel_blockers(char, CommFlag.NOGOSSIP)
    if blocked:
        return blocked

    _clear_comm_flag(char, CommFlag.NOGOSSIP)

    def _should_receive(target: Character) -> bool:
        if _has_comm_flag(target, CommFlag.NOGOSSIP) or _has_comm_flag(target, CommFlag.QUIET):
            return False
        return True

    broadcast_global(
        f"{{d{char.name} gossips '{{t{cleaned}{{d'{{x",
        channel="gossip",
        exclude=char,
        should_send=_should_receive,
    )
    return f"{{dYou gossip '{{t{cleaned}{{d'{{x"


def do_grats(char: Character, args: str) -> str:
    if "grats" in char.banned_channels:
        return "You are banned from grats."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOGRATS):
            _clear_comm_flag(char, CommFlag.NOGRATS)
            return "Grats channel is now ON."
        _set_comm_flag(char, CommFlag.NOGRATS)
        return "Grats channel is now OFF."

    blocked = _check_channel_blockers(char, CommFlag.NOGRATS)
    if blocked:
        return blocked

    _clear_comm_flag(char, CommFlag.NOGRATS)

    def _should_receive(target: Character) -> bool:
        if _has_comm_flag(target, CommFlag.NOGRATS) or _has_comm_flag(target, CommFlag.QUIET):
            return False
        return True

    broadcast_global(
        f"{{t{char.name} grats '{cleaned}'{{x",
        channel="grats",
        exclude=char,
        should_send=_should_receive,
    )
    return f"{{tYou grats '{cleaned}'{{x"


def do_quote(char: Character, args: str) -> str:
    if "quote" in char.banned_channels:
        return "You are banned from quote."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOQUOTE):
            _clear_comm_flag(char, CommFlag.NOQUOTE)
            return "{hQuote channel is now ON.{x"
        _set_comm_flag(char, CommFlag.NOQUOTE)
        return "{hQuote channel is now OFF.{x"

    blocked = _check_channel_blockers(char, CommFlag.NOQUOTE)
    if blocked:
        return blocked

    _clear_comm_flag(char, CommFlag.NOQUOTE)

    def _should_receive(target: Character) -> bool:
        if _has_comm_flag(target, CommFlag.NOQUOTE) or _has_comm_flag(target, CommFlag.QUIET):
            return False
        return True

    broadcast_global(
        f"{{h{char.name} quotes '{{H{cleaned}{{h'{{x",
        channel="quote",
        exclude=char,
        should_send=_should_receive,
    )
    return f"{{hYou quote '{{H{cleaned}{{h'{{x"


def do_question(char: Character, args: str) -> str:
    if "question" in char.banned_channels:
        return "You are banned from question."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOQUESTION):
            _clear_comm_flag(char, CommFlag.NOQUESTION)
            return "Q/A channel is now ON."
        _set_comm_flag(char, CommFlag.NOQUESTION)
        return "Q/A channel is now OFF."

    blocked = _check_channel_blockers(char, CommFlag.NOQUESTION)
    if blocked:
        return blocked

    _clear_comm_flag(char, CommFlag.NOQUESTION)

    def _should_receive(target: Character) -> bool:
        if _has_comm_flag(target, CommFlag.NOQUESTION) or _has_comm_flag(target, CommFlag.QUIET):
            return False
        return True

    broadcast_global(
        f"{{q{char.name} questions '{{Q{cleaned}{{q'{{x",
        channel="question",
        exclude=char,
        should_send=_should_receive,
    )
    return f"{{qYou question '{{Q{cleaned}{{q'{{x"


def do_answer(char: Character, args: str) -> str:
    if "answer" in char.banned_channels:
        return "You are banned from answer."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOQUESTION):
            _clear_comm_flag(char, CommFlag.NOQUESTION)
            return "Q/A channel is now ON."
        _set_comm_flag(char, CommFlag.NOQUESTION)
        return "Q/A channel is now OFF."

    blocked = _check_channel_blockers(char, CommFlag.NOQUESTION)
    if blocked:
        return blocked

    _clear_comm_flag(char, CommFlag.NOQUESTION)

    def _should_receive(target: Character) -> bool:
        if _has_comm_flag(target, CommFlag.NOQUESTION) or _has_comm_flag(target, CommFlag.QUIET):
            return False
        return True

    broadcast_global(
        f"{{f{char.name} answers '{{F{cleaned}{{f'{{x",
        channel="question",
        exclude=char,
        should_send=_should_receive,
    )
    return f"{{fYou answer '{{F{cleaned}{{f'{{x"


def do_music(char: Character, args: str) -> str:
    if "music" in char.banned_channels:
        return "You are banned from music."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOMUSIC):
            _clear_comm_flag(char, CommFlag.NOMUSIC)
            return "Music channel is now ON."
        _set_comm_flag(char, CommFlag.NOMUSIC)
        return "Music channel is now OFF."

    blocked = _check_channel_blockers(char, CommFlag.NOMUSIC)
    if blocked:
        return blocked

    _clear_comm_flag(char, CommFlag.NOMUSIC)

    def _should_receive(target: Character) -> bool:
        if _has_comm_flag(target, CommFlag.NOMUSIC) or _has_comm_flag(target, CommFlag.QUIET):
            return False
        return True

    broadcast_global(
        f"{{e{char.name} MUSIC: '{{E{cleaned}{{e'{{x",
        channel="music",
        exclude=char,
        should_send=_should_receive,
    )
    return f"{{eYou MUSIC: '{{E{cleaned}{{e'{{x"


def do_clantalk(char: Character, args: str) -> str:
    if "clan" in char.banned_channels:
        return "You are banned from clan."
    if not is_clan_member(char):
        return "You aren't in a clan."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOCLAN):
            _clear_comm_flag(char, CommFlag.NOCLAN)
            return "Clan channel is now ON."
        _set_comm_flag(char, CommFlag.NOCLAN)
        return "Clan channel is now OFF."

    if _has_comm_flag(char, CommFlag.NOCHANNELS):
        return "The gods have revoked your channel privileges."

    _clear_comm_flag(char, CommFlag.NOCLAN)

    def _should_receive(target: Character) -> bool:
        if not is_same_clan(char, target):
            return False
        if _has_comm_flag(target, CommFlag.NOCLAN) or _has_comm_flag(target, CommFlag.QUIET):
            return False
        return True

    message = f"{char.name} clans, '{cleaned}'"
    broadcast_global(message, channel="clan", exclude=char, should_send=_should_receive)
    return f"You clan '{cleaned}'"


def do_immtalk(char: Character, args: str) -> str:
    if not char.is_immortal():
        return "You aren't an immortal."
    if "immtalk" in char.banned_channels:
        return "You are banned from immtalk."

    cleaned = args.strip()
    if not cleaned:
        if _has_comm_flag(char, CommFlag.NOWIZ):
            _clear_comm_flag(char, CommFlag.NOWIZ)
            return "Immortal channel is now ON."
        _set_comm_flag(char, CommFlag.NOWIZ)
        return "Immortal channel is now OFF."

    _clear_comm_flag(char, CommFlag.NOWIZ)

    def _should_receive(target: Character) -> bool:
        if not target.is_immortal():
            return False
        if _has_comm_flag(target, CommFlag.NOWIZ):
            return False
        return True

    formatted = f"{{i[{{I{char.name}{{i]: {cleaned}{{x"
    payload = f"{formatted}\n\r"
    broadcast_global(payload, channel="immtalk", exclude=char, should_send=_should_receive)
    return payload


def do_emote(char: Character, args: str) -> str:
    """
    Perform a custom emote action.

    ROM Reference: src/act_comm.c lines 1067-1090 (do_emote)

    Usage: emote <action>

    Displays "<your name> <action>" to everyone in the room.
    Example: "emote smiles happily" displays "Bob smiles happily"
    """
    args = args.strip()
    if not args:
        return "Emote what?"

    # Broadcast to room
    message = f"{char.name} {args}"
    if char.room:
        broadcast_room(char.room, message, exclude=char)

    return message


def do_pose(char: Character, args: str) -> str:
    """
    Perform a custom emote action (alias for emote).

    ROM Reference: pose is typically an alias to emote in ROM

    Usage: pose <action>

    Same as 'emote'. Displays "<your name> <action>" to everyone in the room.
    """
    return do_emote(char, args)


def do_yell(char: Character, args: str) -> str:
    """
    Yell to adjacent rooms.

    ROM Reference: src/act_comm.c lines 1033-1065 (do_yell)

    Usage: yell <message>

    Shouts a message that can be heard in your room and adjacent rooms.
    More local than 'shout' which is heard game-wide.
    """
    if _has_comm_flag(char, CommFlag.NOSHOUT):
        return "You can't yell."

    args = args.strip()
    if not args:
        return "Yell what?"

    # Yell to current room and adjacent rooms
    message = f"{char.name} yells '{args}'"

    # Broadcast to current room
    if char.room:
        broadcast_room(char.room, message, exclude=char)

        # Broadcast to adjacent rooms
        # In full implementation, would iterate through exits and broadcast there too
        # For now, just local room (can be enhanced later)

    return f"You yell '{args}'"


def do_cgossip(char: Character, args: str) -> str:
    """
    Colored gossip channel.

    ROM Reference: src/act_comm.c (cgossip is a color variant of gossip)

    Usage: cgossip <message>

    Like gossip but with color codes. Some MUDs have this as a separate channel.
    For now, this is an alias to gossip with color support.
    """
    # cgossip is typically just gossip with color
    # The gossip command already supports color codes
    return do_gossip(char, args)
