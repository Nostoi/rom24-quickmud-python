"""
Combat safety checks - determine if it's safe to attack.

ROM Reference: src/fight.c is_safe
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def is_safe(char: Character, victim: Character) -> bool:
    """ROM ``is_safe(ch, victim)`` (``src/fight.c:1018-1124``) as a silent bool.

    INV-050: this is a thin wrapper over the single faithful mirror
    :func:`mud.commands.combat._kill_safety_message` — it returns ``True`` (the
    attack is forbidden) exactly when the mirror returns a rejection string, and
    ``False`` (not forbidden) when the mirror returns ``None``. It discards the
    string, so it stays *silent*: ROM's ``is_safe`` writes the rejection line via
    ``send_to_char``/``act`` BEFORE returning TRUE, and every player-facing
    offensive verb gate already routes through the mirror to surface that line.

    The sole remaining caller is the intentionally-silent ``apply_damage``
    re-check (``mud/combat/engine.py``, FIGHT-002, ROM ``src/fight.c:730``), where
    ROM itself calls ``is_safe`` as a backstop. Collapsing the two objects onto
    one source of truth removes the bool's old bidirectional divergence: it used
    to over-block (``is_ghost``/``ACT_GAIN``; ROOM_SAFE for *all* victims) and
    under-block (missing the immortal bypass at :1026, the retaliation bypass at
    :1023, and the entire PC-vs-PC clan PK ladder at :1096-1120).

    (Function-local import mirrors ``spec_funs._is_safe_mirror`` and avoids an
    engine→command import cycle.)
    """
    if char is None or victim is None:
        return True

    from mud.commands.combat import _kill_safety_message

    return _kill_safety_message(char, victim) is not None


def _spell_room_flags(room: object) -> int:
    """Best-effort runtime room flags (mirrors handlers._get_room_flags)."""
    try:
        return int(getattr(room, "room_flags", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        return 0


def _spell_act_flags(character: object) -> int:
    """Best-effort NPC act flags across instance + prototype.

    ROM stores ``act`` directly on the mob; the Python port may carry it on the
    instance or the index prototype, so check both (mirrors
    handlers._get_act_flags).
    """
    flags = 0
    for source in (
        getattr(character, "act", 0),
        getattr(character, "act_flags", 0),
        getattr(getattr(character, "prototype", None), "act", 0),
        getattr(getattr(character, "prototype", None), "act_flags", 0),
        getattr(getattr(character, "pIndexData", None), "act", 0),
        getattr(getattr(character, "pIndexData", None), "act_flags", 0),
    ):
        if source is None:
            continue
        try:
            flags |= int(source)
        except (TypeError, ValueError):  # pragma: no cover - defensive fallback
            continue
    return flags


def _spell_player_flags(character: object) -> int:
    """Best-effort PC act/plr flags (mirrors handlers._get_player_flags)."""
    if getattr(character, "is_npc", True):
        return 0
    try:
        return int(getattr(character, "act", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        return 0


def _spell_has_shop(character: object) -> bool:
    """Mirror ROM ``victim->pIndexData->pShop != NULL`` across instance + proto."""
    for source in (
        getattr(character, "pShop", None),
        getattr(getattr(character, "prototype", None), "pShop", None),
        getattr(getattr(character, "pIndexData", None), "pShop", None),
        getattr(character, "shop", None),
    ):
        if source is not None:
            return True
    return False


def _spell_is_immortal(character: object) -> bool:
    is_immortal = getattr(character, "is_immortal", None)
    if callable(is_immortal):
        try:
            return bool(is_immortal())
        except TypeError:  # pragma: no cover - defensive fallback
            return False
    return False


def _spell_level(character: object) -> int:
    try:
        return int(getattr(character, "level", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        return 0


def is_safe_spell(char: Character, victim: Character, area: bool = False) -> bool:  # noqa: C901
    """Check if it's safe to cast an offensive spell on ``victim``.

    This is a faithful port of ROM's STANDALONE ``is_safe_spell``
    (``src/fight.c:1126-1218``) — it is deliberately NOT a wrapper over
    :func:`is_safe`. ROM's two functions diverge in check order and clauses:
    ``is_safe_spell`` evaluates ``victim->fighting == ch`` BEFORE the NPC
    ROOM_SAFE branch, carries the immortal/area bypasses, the legal-kill
    ``is_same_group`` clauses, and the full PC-vs-PC clan PK ladder — none of
    which live in :func:`is_safe`. (INV-050.)

    Returns ``True`` when the cast is SAFE (i.e. blocked). ROM's function is
    silent — callers that need a player-facing line render their own.
    """
    from mud.characters import is_clan_member, is_same_group
    from mud.models.constants import LEVEL_IMMORTAL, ActFlag, AffectFlag, PlayerFlag, RoomFlag

    if char is None or victim is None:
        return True

    # ROM src/fight.c:1128 — victim->in_room == NULL || ch->in_room == NULL → TRUE
    if getattr(victim, "room", None) is None or getattr(char, "room", None) is None:
        return True

    # ROM :1131 — victim == ch && area → TRUE
    if victim is char and area:
        return True

    # ROM :1134 — victim->fighting == ch || victim == ch → FALSE (retaliation),
    # evaluated BEFORE the NPC ROOM_SAFE branch below.
    if getattr(victim, "fighting", None) is char or victim is char:
        return False

    # ROM :1137 — IS_IMMORTAL(ch) && ch->level > LEVEL_IMMORTAL && !area → FALSE
    if _spell_is_immortal(char) and _spell_level(char) > LEVEL_IMMORTAL and not area:
        return False

    victim_is_npc = bool(getattr(victim, "is_npc", True))
    char_is_npc = bool(getattr(char, "is_npc", True))

    if victim_is_npc:
        # ROM :1144 — ROOM_SAFE → TRUE
        if _spell_room_flags(getattr(victim, "room", None)) & int(RoomFlag.ROOM_SAFE):
            return True
        # ROM :1147 — pShop → TRUE
        if _spell_has_shop(victim):
            return True
        # ROM :1151 — TRAIN | PRACTICE | IS_HEALER | IS_CHANGER → TRUE
        act_flags = _spell_act_flags(victim)
        if act_flags & int(ActFlag.TRAIN | ActFlag.PRACTICE | ActFlag.IS_HEALER | ActFlag.IS_CHANGER):
            return True

        if not char_is_npc:
            # ROM :1160 — ACT_PET → TRUE
            if act_flags & int(ActFlag.PET):
                return True
            # ROM :1164 — AFF_CHARM && (area || ch != victim->master) → TRUE
            victim_affected = int(getattr(victim, "affected_by", 0) or 0)
            if victim_affected & int(AffectFlag.CHARM) and (area or getattr(victim, "master", None) is not char):
                return True
            # ROM :1169 — legal kill: victim fighting a non-group-member → TRUE
            victim_fighting = getattr(victim, "fighting", None)
            if victim_fighting is not None and not is_same_group(char, victim_fighting):
                return True
        else:
            # ROM :1175 — area effect spells do not hit other mobs
            if area and not is_same_group(victim, getattr(char, "fighting", None)):
                return True
    else:
        # ROM :1182 — area && IS_IMMORTAL(victim) && victim->level > LEVEL_IMMORTAL → TRUE
        if area and _spell_is_immortal(victim) and _spell_level(victim) > LEVEL_IMMORTAL:
            return True

        if char_is_npc:
            # ROM :1189 — charmed mob may only hit its master's target
            char_affected = int(getattr(char, "affected_by", 0) or 0)
            if char_affected & int(AffectFlag.CHARM):
                master = getattr(char, "master", None)
                if master is not None and getattr(master, "fighting", None) is not victim:
                    return True
            # ROM :1194 — ROOM_SAFE → TRUE
            if _spell_room_flags(getattr(victim, "room", None)) & int(RoomFlag.ROOM_SAFE):
                return True
            # ROM :1198 — legal kill: mob only hits players grouped with its opponent
            char_fighting = getattr(char, "fighting", None)
            if char_fighting is not None and not is_same_group(char_fighting, victim):
                return True
        else:
            # ROM :1205-1216 — PC-vs-PC clan PK ladder
            if not is_clan_member(char):
                return True
            if _spell_player_flags(victim) & int(PlayerFlag.KILLER | PlayerFlag.THIEF):
                return False
            if not is_clan_member(victim):
                return True
            if _spell_level(char) > _spell_level(victim) + 8:
                return True

    return False
