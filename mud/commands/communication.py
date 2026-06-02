from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from mud import mobprog
from mud.characters import is_clan_member, is_same_clan
from mud.models.character import Character, character_registry
from mud.models.constants import CommFlag, Position
from mud.net.protocol import broadcast_global, send_to_char
from mud.utils.act import capitalize_act_line
from mud.utils.messaging import push_message

if TYPE_CHECKING:
    from mud.net.session import Session


def _get_session(char: Character) -> Session | None:
    """Return the active session backing *char* when connected."""

    desc = getattr(char, "desc", None)
    if desc is None:
        return None
    return cast("Session", desc)


def _queue_personal_message(target: Character, message: str) -> None:
    if hasattr(target, "messages"):
        target.messages.append(message)


def _has_mobprog_trigger(mob: Character, trigger: mobprog.Trigger) -> bool:
    programs = []
    direct = getattr(mob, "mob_programs", None)
    if direct:
        programs.extend(direct)
    proto = getattr(mob, "prototype", None) or getattr(mob, "mob_index", None)
    if proto:
        programs.extend(getattr(proto, "mprogs", []) or [])
    return any(int(getattr(prog, "trig_type", 0) or 0) & int(trigger) for prog in programs)


def _deliver_tell(sender: Character, target: Character, message: str) -> None:
    """Send the formatted tell *message* to *target* and record reply."""

    writer = getattr(target, "connection", None)
    # INV-001 (TELL-007): single-channel delivery — push_message routes a
    # connected target to the async send and the mailbox only for disconnected
    # chars (XOR). The prior _queue_personal_message + if-writer-async
    # double-delivered to a connected PC (the connection loop drains the mailbox
    # too). The linkdead/AFK/note-writing branches in do_tell keep the mailbox
    # queue — those targets are not actively receiving.
    push_message(target, message)
    # mirroring ROM src/act_comm.c:942 / src/comm.c:2384 — the
    # act_new(TO_VICT) tell line dispatches TRIG_ACT on NPC recipients
    # separately from the later TRIG_SPEECH hook.
    if (
        getattr(target, "is_npc", False)
        and not writer
        and mobprog.MOBtrigger
        and _has_mobprog_trigger(target, mobprog.Trigger.ACT)
    ):
        mobprog.mp_act_trigger(message, target, sender, None, target, mobprog.Trigger.ACT)
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
    # mirroring ROM src/act_comm.c:942 — `act_new("{k$n tells you '{K$t{k'{x", ...)`.
    # `$n` routes through PERS(ch, victim) per ROM's act() macro, so an
    # invisible sender renders as "someone" to a target without
    # DETECT_INVIS (TELL-003). Buffered tells (linkdead/AFK/note-writing
    # branches below) use the same formatted string per ROM's sprintf
    # calls at src/act_comm.c:891/924/935 which also wrap PERS(ch, victim).
    # No comma between `you` and the open quote (TELL-002). Wraps with
    # ROM charcoal/black colour codes ({k frame, {K message body, {x
    # reset) — the ANSI translation layer in mud/net/ansi.py consumes
    # them on websocket send (TELL-005).
    from mud.world.vision import pers

    sender_name = pers(sender, target)
    formatted = capitalize_act_line(f"{{k{sender_name} tells you '{{K{message}{{k'{{x")

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
    # mirroring ROM src/act_comm.c:776-777 — `act ("{6$n says '{7$T{6'{x", ...)`
    # and `act ("{6You say '{7$T{6'{x", ...)` (SAY-001 wording, SAY-003
    # colour). Frame in ROM cyan/say-channel ({6), switch to white ({7)
    # for the message body, return to {6 for the closing quote, then
    # reset with {x. The ANSI translation layer in mud/net/ansi.py
    # consumes these on websocket send.
    if char.room:
        # mirroring ROM src/act_comm.c:776 — single `act(..., TO_ROOM)`
        # delivers the message to every target in `ch->in_room->people`
        # exactly once (SAY-004 / INV-001). The act() macro renders
        # `$n` per-listener through PERS(), so an invisible speaker
        # appears as "someone" to listeners without DETECT_INVIS
        # (SAY-002). Each recipient gets its own substituted string.
        from mud.world.vision import pers

        for listener in list(char.room.people):
            if listener is char:
                continue
            speaker_name = pers(char, listener)
            per_message = capitalize_act_line(f"{{6{speaker_name} says '{{7{args}{{6'{{x")
            writer = getattr(listener, "connection", None)
            # INV-001 (SAY-005): single-channel delivery — push_message routes a
            # connected listener to the async send and the mailbox only for
            # disconnected chars (XOR). The prior if-writer-async + unconditional
            # append double-delivered to a connected PC (the connection loop
            # drains the mailbox too). SAY-004 fixed this once; the INV-025 PERS
            # rewrite re-introduced it as this hand-rolled loop.
            push_message(listener, per_message)
            # mirroring ROM src/act_comm.c:776 / src/comm.c:2384 — the
            # unsuppressed say TO_ROOM act() dispatches TRIG_ACT on NPC
            # listeners independently of the explicit TRIG_SPEECH loop below.
            if (
                getattr(listener, "is_npc", False)
                and writer is None
                and mobprog.MOBtrigger
                and _has_mobprog_trigger(listener, mobprog.Trigger.ACT)
            ):
                mobprog.mp_act_trigger(per_message, listener, char, None, args, mobprog.Trigger.ACT)
        # mirroring ROM src/act_comm.c:779 — `if (!IS_NPC (ch))` gate.
        # Only PC speakers enter the SPEECH listener loop; this prevents
        # mob-to-mob speech-trigger cascades (mob A says "X" → mob B's
        # SPEECH trigger fires → triggers another say → infinite loop).
        if not getattr(char, "is_npc", False):
            for mob in list(char.room.people):
                if mob is char or not getattr(mob, "is_npc", False):
                    continue
                default_pos = getattr(mob, "default_pos", getattr(mob, "position", Position.STANDING))
                if getattr(mob, "position", default_pos) != default_pos:
                    continue
                mobprog.mp_speech_trigger(args, mob, char)
    return capitalize_act_line(f"{{6You say '{{7{args}{{6'{{x")


def do_tell(char: Character, args: str) -> str:
    """
    Tell a character something privately.

    ROM Reference: src/act_comm.c do_tell
    ROM behavior: Can tell to PCs anywhere, but NPCs only in same room.
    """
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

    from mud.world.char_find import get_char_world

    target = get_char_world(char, target_name)
    if not target:
        return "They aren't here."

    if getattr(target, "is_npc", False):
        if getattr(target, "room", None) != getattr(char, "room", None):
            return "They aren't here."

    error = _validate_tell_target(char, target)
    if error:
        return error

    buffered_response = _handle_buffered_tell(char, target, message)
    if buffered_response:
        return buffered_response

    # mirroring ROM src/act_comm.c:946 — `if (!IS_NPC (ch) && IS_NPC (victim)
    # && HAS_TRIGGER (victim, TRIG_SPEECH))`. NPC tellers do not fire SPEECH
    # triggers on NPC targets; same anti-cascade gate as do_say.
    if not getattr(char, "is_npc", False) and getattr(target, "is_npc", False):
        default_pos = getattr(target, "default_pos", getattr(target, "position", Position.STANDING))
        if getattr(target, "position", default_pos) == default_pos:
            mobprog.mp_speech_trigger(message, target, char)
    # mirroring ROM src/act_comm.c:941 — `act("{kYou tell $N '{K$t{k'{x", ...)`.
    # `$N` routes through PERS(victim, ch) per ROM's act() macro, so a
    # target the sender cannot see (e.g. INVISIBLE target without
    # sender's DETECT_INVIS) renders as "someone" (TELL-004). No
    # comma between target name and the open quote (TELL-001). Wraps
    # with ROM charcoal/black colour codes ({k frame, {K message body,
    # {x reset) — the ANSI translation layer in mud/net/ansi.py
    # consumes them on websocket send (TELL-005).
    from mud.world.vision import pers

    target_name = pers(target, char)
    return capitalize_act_line(f"{{kYou tell {target_name} '{{K{message}{{k'{{x")


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
    # mirroring ROM src/act_comm.c:836 — `act("$n shouts '$t'", ...)`.
    # No comma between `shouts` and the open quote (SHOUT-002). `$n`
    # routes through PERS(ch, victim) per ROM's act() macro, so an
    # invisible shouter renders as "someone" to listeners without
    # DETECT_INVIS (SHOUT-003). Render per-listener instead of
    # broadcast_global, which only takes one fixed message.
    current_wait = getattr(char, "wait", 0) or 0
    char.wait = max(int(current_wait), 12)

    from mud.world.vision import pers

    for victim in list(character_registry):
        if victim is char:
            continue
        if _has_comm_flag(victim, CommFlag.SHOUTSOFF) or _has_comm_flag(victim, CommFlag.QUIET):
            continue
        if "shout" in getattr(victim, "muted_channels", set()):
            continue
        speaker_name = pers(char, victim)
        per_message = capitalize_act_line(f"{speaker_name} shouts '{cleaned}'")
        # INV-001 (SHOUT-004): single-channel delivery (XOR) — see SAY-005. The
        # prior if-writer-async + unconditional append double-delivered to a
        # connected PC.
        push_message(victim, per_message)
    # mirroring ROM src/act_comm.c:824 — `act("You shout '$T'", ...)`.
    # No comma between `shout` and the open quote (SHOUT-001).
    return capitalize_act_line(f"You shout '{cleaned}'")


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
        capitalize_act_line(f"{{a{char.name} auctions '{{A{cleaned}{{a'{{x"),
        channel="auction",
        exclude=char,
        should_send=_should_receive,
    )
    return capitalize_act_line(f"{{aYou auction '{{A{cleaned}{{a'{{x")


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
        capitalize_act_line(f"{{d{char.name} gossips '{{t{cleaned}{{d'{{x"),
        channel="gossip",
        exclude=char,
        should_send=_should_receive,
    )
    return capitalize_act_line(f"{{dYou gossip '{{t{cleaned}{{d'{{x")


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
        capitalize_act_line(f"{{t{char.name} grats '{cleaned}'{{x"),
        channel="grats",
        exclude=char,
        should_send=_should_receive,
    )
    return capitalize_act_line(f"{{tYou grats '{cleaned}'{{x")


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
        capitalize_act_line(f"{{h{char.name} quotes '{{H{cleaned}{{h'{{x"),
        channel="quote",
        exclude=char,
        should_send=_should_receive,
    )
    return capitalize_act_line(f"{{hYou quote '{{H{cleaned}{{h'{{x")


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
        capitalize_act_line(f"{{q{char.name} questions '{{Q{cleaned}{{q'{{x"),
        channel="question",
        exclude=char,
        should_send=_should_receive,
    )
    return capitalize_act_line(f"{{qYou question '{{Q{cleaned}{{q'{{x")


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
        capitalize_act_line(f"{{f{char.name} answers '{{F{cleaned}{{f'{{x"),
        channel="question",
        exclude=char,
        should_send=_should_receive,
    )
    return capitalize_act_line(f"{{fYou answer '{{F{cleaned}{{f'{{x")


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
        capitalize_act_line(f"{{e{char.name} MUSIC: '{{E{cleaned}{{e'{{x"),
        channel="music",
        exclude=char,
        should_send=_should_receive,
    )
    return capitalize_act_line(f"{{eYou MUSIC: '{{E{cleaned}{{e'{{x")


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

    message = capitalize_act_line(f"{char.name} clans, '{cleaned}'")
    broadcast_global(message, channel="clan", exclude=char, should_send=_should_receive)
    return capitalize_act_line(f"You clan '{cleaned}'")


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

    formatted = capitalize_act_line(f"{{i[{{I{char.name}{{i]: {cleaned}{{x")
    payload = f"{formatted}\n\r"
    broadcast_global(payload, channel="immtalk", exclude=char, should_send=_should_receive)
    return payload


def do_emote(char: Character, args: str) -> str:
    """
    Perform a custom emote action.

    ROM Reference: src/act_comm.c do_emote (lines 1067-1097)
    """
    # ROM C lines 1069-1073: NPCs bypass NOEMOTE; PCs cannot emote when flagged.
    if not getattr(char, "is_npc", False) and _has_comm_flag(char, CommFlag.NOEMOTE):
        return "You can't show your emotions."

    # NB: ROM does NOT strip leading whitespace; argument arrives via interpret().
    if not args:
        return "Emote what?"

    # ROM C lines 1082-1086: ',{' bug guard - first char must be alpha and not space.
    first = args[0]
    if not first.isalpha() or first.isspace():
        return "Moron!"

    # mirroring ROM src/act_comm.c:1091 — `act("$n $T", ..., TO_ROOM)`
    # substitutes `$n` per-listener through PERS() so an invisible
    # emoter renders as "someone" to listeners without DETECT_INVIS
    # (EMOTE-001). Build one substituted string per recipient.
    if char.room:
        from mud.world.vision import pers

        for listener in list(char.room.people):
            if listener is char:
                continue
            per_message = capitalize_act_line(f"{pers(char, listener)} {args}")
            # INV-001 (EMOTE-004): single-channel delivery (XOR) — see SAY-005.
            # The prior if-writer-async + unconditional append double-delivered
            # to a connected PC.
            push_message(listener, per_message)

        # EMOTE-003 / INV-025 — do_emote does NOT dispatch TRIG_ACT.  ROM
        # src/act_comm.c:1090-1093 wraps both `act("$n $T", …)` calls in
        # `MOBtrigger = FALSE; … ; MOBtrigger = TRUE;`, and the trigger
        # dispatch at src/comm.c:2384 fires only `else if (MOBtrigger)`.
        # The suppression is deliberate: emote text is free-form, so an
        # uncapped dispatch would let a player forge any act-trigger phrase
        # (`emote bows` tripping an NPC scripted on "bows").  Messages still
        # reach PCs (the fanout above); the trigger must not fire.

    # mirroring ROM src/act_comm.c:1092 — `act("$n $T", ..., TO_CHAR)`.
    # ROM act() substitutes `$n` to "You" on the TO_CHAR branch so the
    # actor sees `"You <args>"` rather than their own name (EMOTE-002).
    return capitalize_act_line(f"You {args}")


def do_pose(char: Character, args: str) -> str:
    """
    Random class+level pose from the ROM pose_table.

    ROM Reference: src/act_comm.c do_pose (lines 1411-1428) and
    ``pose_table`` in src/act_comm.c lines 1106-1409.
    """
    from mud.utils import rng_mm
    from mud.utils.poses import MAX_POSE_LEVEL, POSE_TABLE

    # ROM C line 1416-1417: NPCs cannot pose.
    if getattr(char, "is_npc", False):
        return ""

    # ROM C line 1419-1420: level = UMIN(ch->level, max_pose_index)
    level = min(int(getattr(char, "level", 0) or 0), MAX_POSE_LEVEL)
    if level < 0:
        level = 0

    pose = rng_mm.number_range(0, level)
    cls = int(getattr(char, "ch_class", 0) or 0)
    if cls < 0 or cls > 3:
        cls = 0

    to_char_fmt = POSE_TABLE[pose][2 * cls + 0]
    to_room_fmt = POSE_TABLE[pose][2 * cls + 1]

    from mud.utils.act import act_format, act_to_room

    self_msg = act_format(to_char_fmt, recipient=char, actor=char)

    if char.room:
        # ROM src/act_comm.c:1425 act(pose_table[...], ch, NULL, NULL, TO_ROOM).
        # INV-025/INV-027: act_to_room renders $n per recipient (invisible poser →
        # "Someone") and dispatches TRIG_ACT — was act_format(recipient=None) +
        # broadcast_room (one baked string, no per-recipient PERS masking).
        act_to_room(char.room, to_room_fmt, char)

    return self_msg


def do_yell(char: Character, args: str) -> str:
    """
    Yell to entire area (area-wide broadcast).

    ROM Reference: src/act_comm.c lines 1033-1065 (do_yell)

    Usage: yell <message>

    Shouts a message that can be heard by everyone in your current area.
    More local than 'shout' which is heard game-wide.
    """
    if _has_comm_flag(char, CommFlag.NOSHOUT):
        return "You can't yell."

    args = args.strip()
    if not args:
        return "Yell what?"

    # ROM C lines 1056-1061: Area-wide broadcast to all characters in same area
    # Check COMM_QUIET filtering and area matching
    if char.room and char.room.area:
        current_area = char.room.area

        # Broadcast to all characters in the same area
        for victim in list(character_registry):
            if victim is char:
                continue
            if not hasattr(victim, "room") or not victim.room:
                continue
            if victim.room.area != current_area:
                continue
            if _has_comm_flag(victim, CommFlag.QUIET):
                continue

            # Send yell message to victim (ROM C: act("$n yells '$t'", ch, argument, d->character, TO_VICT))
            # mirroring ROM src/act_comm.c:1059 — `act("$n yells '$t'", ..., TO_VICT)`.
            # `$n` routes through PERS(ch, victim) per ROM's act() macro,
            # so an invisible yeller renders as "someone" to listeners
            # without DETECT_INVIS (YELL-001).
            from mud.world.vision import pers as _pers

            yeller_name = _pers(char, victim)
            victim_message = capitalize_act_line(f"{yeller_name} yells '{args}'")
            writer = getattr(victim, "connection", None)
            if writer is not None:
                asyncio.create_task(send_to_char(victim, victim_message))
                continue
            _queue_personal_message(victim, victim_message)

    return capitalize_act_line(f"You yell '{args}'")


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
