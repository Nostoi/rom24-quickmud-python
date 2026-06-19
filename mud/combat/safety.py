"""
Combat safety checks - determine if it's safe to attack.

ROM Reference: src/fight.c is_safe
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mud.models.character import Character


def is_safe(char: Character, victim: Character) -> bool:  # noqa: C901
    """
    Check if it's safe to attack victim (i.e., shouldn't attack).

    ROM Reference: src/fight.c is_safe (lines 130-230)

    Returns True if:
    - Victim is in a SAFE room
    - Victim is a shopkeeper
    - Victim is a healer
    - A charmed NPC attacker would attack a PC its master is not fighting
    """
    from mud.models.constants import ActFlag, AffectFlag, RoomFlag

    if char is None or victim is None:
        return True

    # Ghost can't fight
    if getattr(char, "is_ghost", False):
        return True

    # Can't fight yourself
    if char is victim:
        return True

    # Check for safe room
    room = getattr(victim, "room", None)
    if room:
        room_flags = getattr(room, "room_flags", 0)
        if room_flags & RoomFlag.ROOM_SAFE:
            return True

    # Check if victim is a shopkeeper or healer
    victim_act = getattr(victim, "act", 0)
    if getattr(victim, "is_npc", False):
        # Check for special mob types that shouldn't be attacked
        if victim_act & ActFlag.IS_HEALER:
            return True
        if victim_act & ActFlag.IS_CHANGER:
            return True
        if victim_act & ActFlag.TRAIN:
            return True
        if victim_act & ActFlag.PRACTICE:
            return True
        if victim_act & ActFlag.GAIN:
            return True

        # PC-attacker-only guards — mirroring ROM src/fight.c:1056-1071
        if not getattr(char, "is_npc", False):
            # no attacking pets — mirroring ROM src/fight.c:1059
            if victim_act & ActFlag.PET:
                return True
            # no attacking charmed creatures unless owner — mirroring ROM src/fight.c:1067
            victim_affected = getattr(victim, "affected_by", 0)
            if victim_affected & AffectFlag.CHARM:
                if getattr(victim, "master", None) is not char:
                    return True

    # Check shop - if mob has a shop, it's a shopkeeper.
    # mirroring ROM src/fight.c:1040 — victim->pIndexData->pShop != NULL.
    # Python MobInstances carry no pShop directly; the field lives on the
    # MobIndex prototype.  Check both to handle any edge case where pShop
    # was set directly on the instance.
    if getattr(victim, "pShop", None) is not None:
        return True
    proto = getattr(victim, "prototype", None) or getattr(victim, "pIndexData", None)
    if proto is not None and getattr(proto, "pShop", None) is not None:
        return True

    # NPC attacking player — mirroring ROM src/fight.c:1075-1093 ("killing
    # players", IS_NPC(ch) branch). ROM has EXACTLY two guards here: the safe-room
    # check (handled above via victim.room ROOM_SAFE) and the charmed-pet-owner
    # check. There is NO level-difference gate — a fabricated
    # `victim_level < char_level - 10` over-block (FIGHT-077, INV-050) used to live
    # here and silently stopped any mob >10 levels above a player from aggressing.
    if getattr(char, "is_npc", False) and not getattr(victim, "is_npc", True):
        # charmed mobs and pets cannot attack players while master is not fighting them
        # mirroring ROM src/fight.c:1087-1093
        char_affected = getattr(char, "affected_by", 0)
        if char_affected & AffectFlag.CHARM:
            master = getattr(char, "master", None)
            if master is not None and getattr(master, "fighting", None) is not victim:
                return True

    return False


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
