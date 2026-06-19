"""GROUP-005 — do_group display + add/remove broadcasts PERS-mask names.

ROM ``src/act_comm.c`` do_group bakes visibility masking into every name it
prints:

- Header (``:1784``): ``sprintf(buf, "%s's group:", PERS(leader, ch))`` — the
  leader's name is masked to "someone" (lowercase, *not* capitalized) when the
  viewer can't see them.
- Member line (``:1796``): ``capitalize(PERS(gch, ch))`` — each member's name is
  masked **and** capitalized to "Someone".
- Add/remove broadcasts (``:1841-1854``): rendered through ``act()`` so $n/$N are
  ``PERS(actor/victim, recipient)`` per recipient — an observer who can't see the
  actor sees "Someone", and the possessive uses ``$s`` (his/her), not a baked name.

Pre-fix Python baked ``short_descr``/``name`` directly, leaking an invisible
group member's identity to a viewer who shouldn't see it.
"""

from __future__ import annotations

from mud.commands.group_commands import do_group
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, Position, Sex
from mud.models.room import Room
from mud.registry import room_registry


def _make_room(vnum: int = 9430) -> Room:
    room = Room(vnum=vnum, name="Group Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_char(name: str, room: Room) -> Character:
    ch = Character(
        name=name,
        is_npc=False,
        level=10,
        room=room,
        position=int(Position.STANDING),
    )
    ch.messages = []
    ch.sex = Sex.MALE
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def test_group_005_display_masks_invisible_leader_and_member():
    """ROM src/act_comm.c:1784/1796 — header PERS(leader,ch) (lowercase),
    member capitalize(PERS(gch,ch)) (capitalized)."""
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()
        leader = _make_char("hiddenleader", room)
        viewer = _make_char("viewer", room)

        # viewer follows leader → same group; leader is its own leader.
        viewer.leader = leader
        leader.leader = None

        # Leader is invisible; viewer lacks DETECT_INVIS → viewer can't see leader.
        leader.add_affect(AffectFlag.INVISIBLE)

        out = do_group(viewer, "").lower()

        assert "hiddenleader" not in out, (
            f"invisible leader's name must be masked in header AND member line (ROM PERS gating); got:\n{out}"
        )
        # Header is PERS(leader, ch) — lowercase "someone's group:".
        assert "someone's group:" in out, f"header must mask leader to lowercase 'someone' (ROM :1784); got:\n{out}"
        # Member line is capitalize(PERS(gch, ch)) — "Someone" capitalized.
        assert "someone" in do_group(viewer, ""), (
            f"member line must mask invisible member; got:\n{do_group(viewer, '')}"
        )
        # The capitalized member form must be present (distinct from the lowercase header).
        assert "Someone" in do_group(viewer, ""), (
            f"member line must capitalize the masked name (ROM :1796 capitalize()); got:\n{do_group(viewer, '')}"
        )
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(9430, None)


def test_group_005_add_broadcast_masks_actor_to_blind_observer(monkeypatch):
    """ROM src/act_comm.c:1851 — TO_NOTVICT `$N joins $n's group.` renders $n via
    PERS(ch, recipient); a watcher who can't see the leader sees "someone"."""
    from mud.commands import group_commands as gc

    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()
        leader = _make_char("leader", room)
        follower = _make_char("follower", room)
        _make_char("watcher", room)

        follower.master = leader
        # Leader invisible; watcher (no DETECT_INVIS) can't see them.
        leader.add_affect(AffectFlag.INVISIBLE)

        sent: list[tuple[str, str]] = []
        monkeypatch.setattr(
            gc, "_send_to_char_sync", lambda c, m: sent.append((getattr(c, "name", "?"), m)), raising=False
        )

        do_group(leader, "follower")

        watcher_msgs = [m for n, m in sent if n == "watcher"]
        joined = "\n".join(watcher_msgs).lower()
        assert "follower joins someone's group" in joined, (
            f"TO_NOTVICT must mask the unseen leader as 'someone' per recipient "
            f"(ROM act PERS, src/act_comm.c:1851); watcher saw: {watcher_msgs!r}"
        )
        assert "leader" not in joined, f"invisible leader's name leaked to watcher: {watcher_msgs!r}"
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(9430, None)


def test_group_005_remove_to_vict_uses_possessive_pronoun(monkeypatch):
    """ROM src/act_comm.c:1843 — TO_VICT `$n removes you from $s group.` uses the
    possessive PRONOUN ($s = his/her), not the leader's name repeated."""
    from mud.commands import group_commands as gc

    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()
        leader = _make_char("leader", room)
        follower = _make_char("follower", room)

        leader.sex = Sex.FEMALE  # $s → "her"
        follower.master = leader
        follower.leader = leader  # already grouped → remove path

        sent: list[tuple[str, str]] = []
        monkeypatch.setattr(
            gc, "_send_to_char_sync", lambda c, m: sent.append((getattr(c, "name", "?"), m)), raising=False
        )

        do_group(leader, "follower")

        vict_msgs = [m for n, m in sent if n == "follower"]
        joined = " ".join(vict_msgs)
        assert "removes you from her group" in joined, (
            f"TO_VICT must use the $s possessive pronoun (ROM src/act_comm.c:1843), "
            f"not the leader's name; follower saw: {vict_msgs!r}"
        )
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(9430, None)
