from __future__ import annotations

from typing import TYPE_CHECKING

from mud.models.constants import AffectFlag

if TYPE_CHECKING:  # pragma: no cover - import for type checkers only
    from mud.models.character import Character


def _display_name(character: "Character" | None) -> str:
    if character is None:
        return "Someone"
    name = getattr(character, "name", None)
    if isinstance(name, str) and name:
        return name
    short_descr = getattr(character, "short_descr", None)
    if isinstance(short_descr, str) and short_descr:
        return short_descr
    return "Someone"


def add_follower(follower: "Character", master: "Character") -> None:
    """Attach ``follower`` to ``master`` mirroring ROM ``add_follower``."""

    if getattr(follower, "master", None) is master:
        return
    if getattr(follower, "master", None) not in (None, master):
        stop_follower(follower)

    follower.master = master
    follower.leader = None

    master_messages = getattr(master, "messages", None)
    if isinstance(master_messages, list):
        master_messages.append(f"{_display_name(follower)} now follows you.")

    follower_messages = getattr(follower, "messages", None)
    if isinstance(follower_messages, list):
        follower_messages.append(f"You now follow {_display_name(master)}.")


def stop_follower(follower: "Character") -> None:
    """Detach ``follower`` from its master and clear charm effects."""

    master = getattr(follower, "master", None)
    if master is None:
        return

    if follower.has_spell_effect("charm person"):
        follower.remove_spell_effect("charm person")
    elif follower.has_affect(AffectFlag.CHARM):
        follower.remove_affect(AffectFlag.CHARM)

    master_messages = getattr(master, "messages", None)
    if isinstance(master_messages, list):
        master_messages.append(f"{_display_name(follower)} stops following you.")

    follower_messages = getattr(follower, "messages", None)
    if isinstance(follower_messages, list):
        follower_messages.append(f"You stop following {_display_name(master)}.")

    if getattr(master, "pet", None) is follower:
        master.pet = None

    follower.master = None
    follower.leader = None


__all__ = ["add_follower", "stop_follower"]
