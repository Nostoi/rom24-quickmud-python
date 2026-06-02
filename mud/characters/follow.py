from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import AffectFlag
from mud.utils.messaging import push_message

if TYPE_CHECKING:  # pragma: no cover - import for type checkers only
    from mud.models.character import Character


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


def add_follower(follower: Character, master: Character) -> None:
    """Attach ``follower`` to ``master`` mirroring ROM ``add_follower``."""
    # mirroring ROM src/act_comm.c:1591-1607
    from mud.world.vision import can_see_character

    if getattr(follower, "master", None) is master:
        return
    if getattr(follower, "master", None) not in (None, master):
        stop_follower(follower)

    follower.master = master
    follower.leader = None

    # ROM lines 1602-1603: TO_VICT gated on can_see(master, ch).
    if can_see_character(master, follower):
        # mirroring ROM src/act_comm.c:1602-1603 — act(..., TO_VICT)
        # writes immediately to the descriptor; mailbox is fallback only.
        push_message(master, f"{_display_name(follower)} now follows you.")

    # ROM line 1605: TO_CHAR is unconditional.
    push_message(follower, f"You now follow {_display_name(master)}.")


def stop_follower(follower: Character) -> None:
    """Detach ``follower`` from its master and clear charm effects."""
    # mirroring ROM src/act_comm.c:1612-1636
    from mud.world.vision import can_see_character

    master = getattr(follower, "master", None)
    if master is None:
        return

    if follower.has_spell_effect("charm person"):
        follower.remove_spell_effect("charm person")
    elif follower.has_affect(AffectFlag.CHARM):
        follower.remove_affect(AffectFlag.CHARM)

    # ROM lines 1625-1629: both messages gated on
    # can_see(ch->master, ch) && ch->in_room != NULL.
    if can_see_character(master, follower) and getattr(follower, "room", None) is not None:
        # ROM src/act_comm.c:1626-1627 — act(..., TO_VICT)/act(..., TO_CHAR) write
        # immediately to the descriptor; push_message routes a connected PC to the
        # async send and falls back to the mailbox only for disconnected chars
        # (matching add_follower above — ACT_COMM-003 / INV-001 wrong-channel).
        push_message(master, f"{_display_name(follower)} stops following you.")
        push_message(follower, f"You stop following {_display_name(master)}.")

    if getattr(master, "pet", None) is follower:
        master.pet = None

    follower.master = None
    follower.leader = None


def die_follower(char: Character) -> None:
    """Detach a dying character from its group and followers.

    Mirrors ROM ``src/act_comm.c:1658-1680``:

    1. If ``ch`` is following someone, detach ``ch`` from its master
       (releasing ``master->pet`` if it pointed at ``ch``).
    2. Clear ``ch->leader``.
    3. For every other character, if it follows ``ch`` (``master == ch``)
       stop the follow; if it groups under ``ch`` (``leader == ch``), reset
       its leader to itself so it becomes its own independent group leader
       — NOT NULL, otherwise ``is_same_group`` would still equate two
       former members via their dangling pointer at the extracted corpse.
    """
    from mud.models.character import character_registry

    if getattr(char, "master", None) is not None:
        master = char.master
        if getattr(master, "pet", None) is char:
            master.pet = None
        stop_follower(char)

    char.leader = None

    for fch in list(character_registry):
        if getattr(fch, "master", None) is char:
            stop_follower(fch)
        if getattr(fch, "leader", None) is char:
            fch.leader = fch


__all__ = ["add_follower", "stop_follower", "die_follower"]
