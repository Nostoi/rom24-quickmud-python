from __future__ import annotations

from mud import mobprog
from mud.account.account_manager import save_character
from mud.advancement import exp_per_level, gain_exp
from mud.affects.saves import _check_immune as _riv_check
from mud.affects.saves import saves_spell
from mud.characters import is_clan_member, is_same_clan, is_same_group
from mud.characters.follow import stop_follower
from mud.combat.death import raw_kill
from mud.combat.messages import TYPE_HIT, DamageMessages, dam_message
from mud.groups.xp import group_gain
from mud.magic import SpellTarget, cold_effect, fire_effect, shock_effect
from mud.math.c_compat import c_div
from mud.math.stat_apps import get_ac, get_damroll, get_hitroll
from mud.models.character import Character, SpellEffect, character_registry
from mud.models.constants import (
    AC_BASH,
    AC_EXOTIC,
    AC_PIERCE,
    AC_SLASH,
    LEVEL_IMMORTAL,
    WEAPON_FLAMING,
    WEAPON_FROST,
    WEAPON_POISON,
    WEAPON_SHOCKING,
    WEAPON_VAMPIRIC,
    ActFlag,
    AffectFlag,
    DamageType,
    ItemType,
    OffFlag,
    PlayerFlag,
    Position,
    Stat,
    WeaponType,
    WearFlag,
    WearLocation,
    attack_damage_type,
)
from mud.models.weapon_table import weapon_skill_name_for_type
from mud.skills import check_improve
from mud.utils import rng_mm
from mud.utils.act import capitalize_act_line
from mud.wiznet import WiznetFlag, wiznet
from mud.world.vision import can_see_object, pers

HAND_TO_HAND_SKILL = "hand to hand"


def _coerce_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def get_wielded_weapon(attacker: Character | None):
    """Return the currently wielded weapon for an attacker."""

    if attacker is None:
        return None

    wield = getattr(attacker, "wielded_weapon", None)
    if wield is not None:
        return wield

    equipment = getattr(attacker, "equipment", None)
    if isinstance(equipment, dict):
        candidate = equipment.get(int(WearLocation.WIELD))
        if candidate is not None:
            return candidate
    return None


def _weapon_values(weapon) -> list[int]:
    values = getattr(weapon, "value", None)
    if values is None and hasattr(weapon, "prototype"):
        values = getattr(weapon.prototype, "value", None)
    if isinstance(values, list | tuple):
        return [int(v) for v in values]
    return []


def _weapon_type(weapon) -> WeaponType | None:
    values = _weapon_values(weapon)
    if not values:
        return None
    try:
        return WeaponType(int(values[0]))
    except (ValueError, TypeError):
        return None


def _weapon_attack_index(weapon) -> int:
    values = _weapon_values(weapon)
    if len(values) > 3:
        try:
            return int(values[3])
        except (TypeError, ValueError):
            return 0
    return 0


def _weapon_is_new_format(weapon) -> bool:
    if hasattr(weapon, "new_format"):
        return bool(weapon.new_format)
    if hasattr(weapon, "prototype") and hasattr(weapon.prototype, "new_format"):
        return bool(weapon.prototype.new_format)
    return False


def _weapon_level(weapon) -> int:
    if hasattr(weapon, "level"):
        try:
            return int(weapon.level)
        except (TypeError, ValueError):
            return 0
    if hasattr(weapon, "prototype") and hasattr(weapon.prototype, "level"):
        try:
            return int(weapon.prototype.level)
        except (TypeError, ValueError):
            return 0
    return 0


def _is_weapon(weapon) -> bool:
    item_type = getattr(weapon, "item_type", None)
    if item_type == int(ItemType.WEAPON) or item_type == ItemType.WEAPON:
        return True
    if isinstance(item_type, str) and item_type.lower() == "weapon":
        return True
    if hasattr(weapon, "prototype"):
        proto_type = getattr(weapon.prototype, "item_type", None)
        if proto_type == int(ItemType.WEAPON) or proto_type == ItemType.WEAPON:
            return True
        if isinstance(proto_type, str) and proto_type.lower() == "weapon":
            return True
    return False


def _has_shield_equipped(attacker: Character) -> bool:
    has_attr = getattr(attacker, "has_shield_equipped", None)
    if has_attr is not None:
        return bool(has_attr)
    equipment = getattr(attacker, "equipment", None)
    if isinstance(equipment, dict):
        return equipment.get(int(WearLocation.SHIELD)) is not None
    return False


def get_weapon_sn(attacker: Character, weapon=None) -> str | None:
    """Return the weapon skill name for the attacker's wielded weapon."""

    weapon = weapon if weapon is not None else get_wielded_weapon(attacker)
    if weapon is None or not _is_weapon(weapon):
        return HAND_TO_HAND_SKILL

    wtype = _weapon_type(weapon)
    if wtype is None:
        return None
    if wtype == WeaponType.EXOTIC:
        return None
    return weapon_skill_name_for_type(wtype) or HAND_TO_HAND_SKILL


def _lookup_skill_percent(attacker: Character, skill_name: str) -> int:
    skills = getattr(attacker, "skills", {})
    if not isinstance(skills, dict):
        return 0
    lowered = skill_name.lower()
    for key, value in skills.items():
        try:
            if str(key).lower() != lowered:
                continue
            percent = int(value)
        except (TypeError, ValueError):
            continue
        return max(0, min(100, percent))
    return 0


def _get_skill_percent(attacker: Character, skill_name: str, fallback_attr: str | None = None) -> int:
    """Return the learned percentage for a skill with optional attribute fallback."""

    percent = _lookup_skill_percent(attacker, skill_name)
    if percent <= 0 and fallback_attr is not None:
        fallback_val = getattr(attacker, fallback_attr, None)
        if fallback_val is not None:
            try:
                percent = int(fallback_val)
            except (TypeError, ValueError):
                percent = 0
    return max(0, min(100, percent))


from mud.utils.messaging import push_message as _push_message  # noqa: E402


def _broadcast_damage_messages(
    attacker: Character,
    victim: Character,
    messages: DamageMessages | None,
) -> None:
    """Render `dam_message` templates per-recipient through ROM PERS.

    Mirrors ROM `src/fight.c:2218-2228` — three `act()` calls
    (TO_NOTVICT/TO_CHAR/TO_VICT) each evaluate `PERS(ch, looker)`
    and `PERS(victim, looker)` independently for each observer.
    Python previously emitted pre-rendered strings keyed on
    `attacker.name`/`victim.name`, leaking identities to every
    recipient regardless of `can_see` (DAMMSG-001/002/003).
    """
    from mud.combat.messages import render_for as _render

    if messages is None:
        return

    if messages.attacker:
        # TO_CHAR — render with observer=attacker (attacker sees own
        # actor as "You" in template; $N renders victim through
        # PERS(victim, attacker)).
        _push_message(attacker, _render(messages.attacker, attacker, victim, attacker) or "")

    if not messages.self_inflicted and messages.victim:
        # TO_VICT — render with observer=victim (victim sees $n
        # attacker through PERS(attacker, victim)).
        _push_message(victim, _render(messages.victim, attacker, victim, victim) or "")

    if not messages.room:
        return

    room = getattr(victim, "room", None)
    if room is None:
        return

    # TO_NOTVICT — iterate room.people and PERS-render per recipient
    # so each observer sees attacker/victim per their own visibility.
    for occupant in list(getattr(room, "people", [])):
        if occupant is attacker or occupant is victim:
            continue
        _push_message(occupant, _render(messages.room, attacker, victim, occupant) or "")

    # ROM src/fight.c:2217/2222 — dam_message's TO_ROOM (self-inflicted) /
    # TO_NOTVICT act() calls carry no MOBtrigger=FALSE wrap, so per
    # src/comm.c:2384 every NPC recipient in the room fires TRIG_ACT against
    # the formatted line. Mirror that so mob ACT-progs respond to combat.
    from mud.mobprog import mp_act_trigger_room

    canonical = messages.room.format(
        attacker=getattr(attacker, "name", "Someone"),
        victim=getattr(victim, "name", "Someone"),
    )
    mp_act_trigger_room(canonical, room, attacker, exclude=victim)


# Back-compat alias — the old name is referenced in older session
# notes and some test files. Both names invoke the same logic.
_dispatch_damage_messages = _broadcast_damage_messages


def get_weapon_skill(attacker: Character, weapon_sn: str | None) -> int:
    """Return the attacker's proficiency for the given weapon skill."""

    level = int(getattr(attacker, "level", 0) or 0)
    if weapon_sn is None:
        return max(0, min(100, 3 * level))

    if getattr(attacker, "is_npc", False):
        if weapon_sn == HAND_TO_HAND_SKILL:
            return max(0, min(100, 40 + 2 * level))
        return max(0, min(100, 40 + (5 * level) // 2))

    return _lookup_skill_percent(attacker, weapon_sn)


def _normalize_dt(dt: str | int | None) -> str | None:
    """Return a normalized string identifier for a damage type/skill token."""

    if dt is None:
        return None
    if isinstance(dt, str):
        return dt.lower()
    try:
        # Many callers pass gsn indices.  We only need special handling for
        # backstab right now, and the skills.json entry uses the same name.
        return str(dt).lower()
    except Exception:  # pragma: no cover - defensive
        return None


def _should_check_weapon_defenses(dt: str | int | None) -> bool:
    """Return True when ROM weapon defenses should be consulted for this attack.

    ROM C (fight.c:793) gates defense checks with ``dt >= TYPE_HIT``.
    For base weapon attacks from violence_update, dt is TYPE_UNDEFINED,
    so defense checks are skipped.
    """
    if isinstance(dt, int):
        return dt >= TYPE_HIT
    if isinstance(dt, str):
        return False
    # dt=None mirrors ROM C's TYPE_UNDEFINED — no defense checks.
    return False


def multi_hit(attacker: Character, victim: Character, dt: str | int | None = None) -> list[str]:
    """Perform multiple attacks following ROM multi_hit mechanics.

    Returns a list of attack result messages.
    """
    results: list[str] = []

    # Position check - no attacks if position too low
    if attacker.position < Position.RESTING:
        return results

    # ROM src/fight.c multi_hit: NPC attackers resolve their round through the
    # separate mob_hit() path — `if (IS_NPC(ch)) { mob_hit(ch,victim,dt); return; }`
    # — which adds the OFF_AREA_ATTACK sweep, the OFF_FAST extra swing, and the
    # mob spell/skill rolls after the 2nd/3rd attacks (FIGHT-022).
    if getattr(attacker, "is_npc", False):
        return mob_hit(attacker, victim, dt)

    # First attack always happens
    result = attack_round(attacker, victim, dt=dt)
    results.append(result)

    # Check if victim died or combat ended
    if victim.position == Position.DEAD or not hasattr(attacker, "fighting") or attacker.fighting != victim:
        return results

    # check_assist dispatch moved to mud.game_loop.violence_tick (ROM
    # src/fight.c:90 — check_assist is called from violence_update after
    # multi_hit returns, NOT inside multi_hit). Same shape as INV-026 —
    # non-violence callers (assist itself, spec_funs, mob_cmds) must not
    # provoke another assist round.

    # ROM allows only a single strike for backstab.
    if _normalize_dt(dt) == "backstab":
        return results

    # Haste gives extra attack
    if getattr(attacker, "has_affect", None) and attacker.has_affect(AffectFlag.HASTE):
        result = attack_round(attacker, victim)
        results.append(result)
        if victim.position == Position.DEAD or not hasattr(attacker, "fighting") or attacker.fighting != victim:
            return results

    # Second attack — ROM src/fight.c multi_hit/mob_hit resolve the extra attack
    # with `if (number_percent() < chance)`. number_percent() is the LEFT operand,
    # so the RNG draw fires UNCONDITIONALLY — even when chance==0 for a skill-less
    # attacker (most mobs, every low-level mage). FIGHT-021: do not guard the draw
    # behind `skill > 0`; that drew two fewer values than ROM and desynced the
    # shared combat RNG stream for every later swing in the tick.
    second_attack_skill = getattr(attacker, "second_attack_skill", 0)
    chance = second_attack_skill // 2  # skill is 0..100 (non-negative) → bare // == C truncation

    # Slow reduces chances
    if getattr(attacker, "has_affect", None) and attacker.has_affect(AffectFlag.SLOW):
        chance //= 2

    if rng_mm.number_percent() < chance:
        result = attack_round(attacker, victim)
        results.append(result)
        check_improve(attacker, "second attack", True, 5)
        if victim.position == Position.DEAD or not hasattr(attacker, "fighting") or attacker.fighting != victim:
            return results

    # Third attack — ROM src/fight.c: same unconditional number_percent() draw.
    third_attack_skill = getattr(attacker, "third_attack_skill", 0)
    chance = third_attack_skill // 4  # non-negative → bare // == C truncation

    # Slow prevents third attack entirely
    if getattr(attacker, "has_affect", None) and attacker.has_affect(AffectFlag.SLOW):
        chance = 0

    if rng_mm.number_percent() < chance:
        result = attack_round(attacker, victim)
        results.append(result)
        check_improve(attacker, "third attack", True, 6)

    # INV-026: TRIG_FIGHT / TRIG_HPCNT dispatch moved to
    # mud.game_loop.violence_tick (the ROM violence_update analog) so
    # non-violence callers (assist, spec_funs, mob_cmds) do not provoke
    # the triggers and a victim killed during the round is skipped.
    # Mirrors ROM src/fight.c:84-98.

    return results


def mob_hit(attacker: Character, victim: Character, dt: str | int | None = None) -> list[str]:
    """ROM src/fight.c ``mob_hit`` — the NPC combat round (FIGHT-022).

    Distinct from ``multi_hit``'s PC path: an NPC gets an OFF_AREA_ATTACK sweep and
    an OFF_FAST extra swing, and after its (unconditional, see FIGHT-021) 2nd/3rd
    attacks it rolls two more values **when not waiting** — ``number_range(0, 2)``
    (mob spell-cast check; the casts are stubbed in ROM too) and
    ``number_range(0, 8)`` (the off-skill dispatch: bash / berserk / disarm / kick /
    kick-dirt / trip / backstab by OFF_ flag). Those two ``number_range`` draws MUST
    fire even for a flag-less mob: they are part of the shared combat RNG stream, so
    skipping them desyncs every later swing in the tick (the drunk-vs-player case in
    differential FINDING-009 facet 1).
    """
    results: list[str] = []

    # one_hit (ROM src/fight.c mob_hit:1).
    result = attack_round(attacker, victim, dt=dt)
    results.append(result)
    if victim.position == Position.DEAD or not hasattr(attacker, "fighting") or attacker.fighting != victim:
        return results

    off_flags = int(getattr(attacker, "off_flags", 0) or 0)
    has_affect = getattr(attacker, "has_affect", None)
    is_haste = bool(has_affect and attacker.has_affect(AffectFlag.HASTE))
    is_slow = bool(has_affect and attacker.has_affect(AffectFlag.SLOW))

    # Area attack — ROM: one extra swing at every OTHER char fighting this mob.
    if off_flags & OffFlag.AREA_ATTACK and getattr(attacker, "room", None) is not None:
        for vch in list(getattr(attacker.room, "people", []) or []):
            if vch is not victim and getattr(vch, "fighting", None) is attacker:
                results.append(attack_round(attacker, vch, dt=dt))

    # Haste OR (OFF_FAST and not slowed) → extra swing at the main victim.
    if is_haste or (off_flags & OffFlag.FAST and not is_slow):
        results.append(attack_round(attacker, victim, dt=dt))

    # ROM: single strike for backstab; bail if combat ended.
    if not hasattr(attacker, "fighting") or attacker.fighting != victim or _normalize_dt(dt) == "backstab":
        return results

    # Second attack — unconditional number_percent() draw (FIGHT-021). For an NPC,
    # slow halves the chance only when the mob is not OFF_FAST.
    chance = getattr(attacker, "second_attack_skill", 0) // 2  # non-negative → bare // == C
    if is_slow and not (off_flags & OffFlag.FAST):
        chance //= 2
    if rng_mm.number_percent() < chance:
        results.append(attack_round(attacker, victim, dt=dt))
        if victim.position == Position.DEAD or not hasattr(attacker, "fighting") or attacker.fighting != victim:
            return results

    # Third attack — unconditional draw; slow (and not OFF_FAST) zeroes the chance.
    chance = getattr(attacker, "third_attack_skill", 0) // 4  # non-negative → bare // == C
    if is_slow and not (off_flags & OffFlag.FAST):
        chance = 0
    if rng_mm.number_percent() < chance:
        results.append(attack_round(attacker, victim, dt=dt))
        if victim.position == Position.DEAD or not hasattr(attacker, "fighting") or attacker.fighting != victim:
            return results

    # "oh boy! Fun stuff!" — ROM rolls the mob spell/skill checks only when the mob
    # is not waiting. The draws are part of the shared RNG stream regardless of
    # whether any action fires.
    if int(getattr(attacker, "wait", 0) or 0) > 0:
        return results

    act_flags = int(getattr(attacker, "act", 0) or 0)

    # number_range(0, 2): mob spell-cast check. mob_cast_mage / mob_cast_cleric are
    # commented out in ROM, so the draw is consumed and no cast fires.
    cast_roll = rng_mm.number_range(0, 2)
    if (cast_roll == 1 and act_flags & ActFlag.MAGE) or (cast_roll == 2 and act_flags & ActFlag.CLERIC):
        pass  # ROM: mob_cast_* stubbed — draw consumed, no action

    # number_range(0, 8): mob off-skill dispatch by OFF_ flag.
    skill_roll = rng_mm.number_range(0, 8)
    _mob_offensive_skill(attacker, skill_roll, off_flags, act_flags)

    return results


def _mob_offensive_skill(attacker: Character, roll: int, off_flags: int, act_flags: int) -> None:
    """ROM src/fight.c ``mob_hit`` switch — fire a mob's offensive skill by OFF_ flag.

    Output flows through each command's own ``act()`` / push, so the return value is
    discarded exactly as ROM's ``do_function(ch, &do_x, "")``. Cases 5 (tail) and 7
    (crush) are no-ops in ROM (commented out). The dispatch only fires when the
    matching OFF_ flag is set; a flag-less mob (the differential's drunk) takes no
    action. The mob-on-do_X invocation is faithful to ROM's structure but its own
    RNG/draw fidelity is unverified for flagged mobs — if a do_X is later found to
    diverge from ROM's draw pattern, file a follow-up gap rather than absorbing it.
    """
    # Lazy import: mud.commands.combat imports multi_hit from mud.combat (circular).
    from mud.commands.combat import do_backstab, do_bash, do_berserk, do_dirt, do_disarm, do_kick, do_trip

    has_affect = getattr(attacker, "has_affect", None)
    if roll == 0:
        if off_flags & OffFlag.BASH:
            do_bash(attacker, "")
    elif roll == 1:
        if off_flags & OffFlag.BERSERK and not (has_affect and attacker.has_affect(AffectFlag.BERSERK)):
            do_berserk(attacker, "")
    elif roll == 2:
        # ROM: OFF_DISARM, or an armed warrior/thief (get_weapon_sn != hand_to_hand).
        weapon_sn = get_weapon_sn(attacker)
        armed_class = weapon_sn not in (None, "hand to hand") and act_flags & (ActFlag.WARRIOR | ActFlag.THIEF)
        if off_flags & OffFlag.DISARM or armed_class:
            do_disarm(attacker, "")
    elif roll == 3:
        if off_flags & OffFlag.KICK:
            do_kick(attacker, "")
    elif roll == 4:
        if off_flags & OffFlag.KICK_DIRT:
            do_dirt(attacker, "")
    elif roll == 6:
        if off_flags & OffFlag.TRIP:
            do_trip(attacker, "")
    elif roll == 8:
        if off_flags & OffFlag.BACKSTAB:
            do_backstab(attacker, "")
    # roll == 5 (OFF_TAIL) and roll == 7 (OFF_CRUSH): no-op in ROM (do_tail/do_crush
    # commented out).


def attack_round(attacker: Character, victim: Character, dt: str | int | None = None) -> str:
    """Resolve a single attack round.

    The attacker attempts to hit the victim.  Hit chance is derived from a
    base 50% modified by the attacker's ``hitroll``.  Successful hits apply
    ``damroll`` damage.  Living combatants are placed into FIGHTING position.
    If the victim dies, they are removed from the room and their position set
    to ``DEAD``.
    """

    # Capture victim's pre-attack position for ROM-like modifiers
    _victim_pos_before = victim.position

    wield = get_wielded_weapon(attacker)
    weapon_sn = get_weapon_sn(attacker, wield)
    weapon_skill = get_weapon_skill(attacker, weapon_sn)
    skill_total = 20 + weapon_skill
    if skill_total <= 0:
        skill_total = 1

    attack_index = attacker.dam_type or 0
    if wield is not None:
        attack_index = _weapon_attack_index(wield)
    attack_dt = dt
    if attack_dt is None or attack_dt == -1:
        attack_dt = TYPE_HIT + attack_index
    dam_type_lookup = attack_damage_type(attack_index)
    dam_type = int(dam_type_lookup) if dam_type_lookup is not None else int(DamageType.BASH)
    ac_idx = ac_index_for_dam_type(dam_type)
    # ROM src/merc.h:2104-2106 GET_AC adds dex_app[DEX].defensive when IS_AWAKE.
    victim_ac = get_ac(victim, ac_idx)
    # Visibility and position modifiers (ROM-inspired)
    if getattr(victim, "has_affect", None) and victim.has_affect(AffectFlag.INVISIBLE):
        victim_ac -= 4
    if _victim_pos_before < Position.FIGHTING:
        victim_ac += 4
    if _victim_pos_before < Position.RESTING:
        victim_ac += 6

    # ROM AC clamping for very negative values
    if victim_ac < -15:
        victim_ac = c_div(victim_ac + 15, 5) - 15

    # FIGHT-019: ROM one_hit has a single attack-roll model — the THAC0 /
    # number_bits(5) roll (src/fight.c:508-516). The legacy percent model
    # (50 + hitroll + AC/2 via number_percent) was a non-ROM divergence in both
    # the RNG draw and the hit/miss decision; retired here so combat is faithful
    # by default.
    # ROM src/fight.c:508 — `while ((diceroll = number_bits(5)) >= 20);`
    while True:
        diceroll = rng_mm.number_bits(5)
        if diceroll < 20:
            break
    # Compute thac0 with hitroll/skill contributions.
    # ROM src/merc.h:2107-2108 GET_HITROLL adds str_app[STR].tohit to ch->hitroll.
    if getattr(attacker, "is_npc", False):
        # ROM src/fight.c:445-457 — NPC attackers use thac0_00 = 20 and a
        # thac0_32 keyed off their ACT class flag ("as good as a thief" default).
        act_flags = int(getattr(attacker, "act", 0))
        if act_flags & ActFlag.WARRIOR:
            npc_t32 = -10
        elif act_flags & ActFlag.THIEF:
            npc_t32 = -4
        elif act_flags & ActFlag.CLERIC:
            npc_t32 = 2
        elif act_flags & ActFlag.MAGE:
            npc_t32 = 6
        else:
            npc_t32 = -4
        th = compute_thac0(
            attacker.level, 0, hitroll=get_hitroll(attacker), skill=skill_total, thac0_pair=(20, npc_t32)
        )
    else:
        th = compute_thac0(
            attacker.level, attacker.ch_class, hitroll=get_hitroll(attacker), skill=skill_total
        )
    vac = c_div(victim_ac, 10)
    # ROM src/fight.c:510 — miss on nat 0, or (not 19 and diceroll < thac0 - victim_ac).
    if diceroll == 0 or (diceroll != 19 and diceroll < (th - vac)):
        # Miss — ROM C calls damage(ch, victim, 0, dt, dam_type, TRUE).
        return apply_damage(attacker, victim, 0, int(dam_type), dt=attack_dt)

    # Hit determined - calculate weapon damage following C src/fight.c:one_hit logic
    damage = calculate_weapon_damage(
        attacker,
        victim,
        dam_type,
        wield=wield,
        skill=skill_total,
        dt=attack_dt,
    )

    # Apply damage reduction modifiers (sanctuary, protection, drunk) following C src/fight.c:damage logic
    damage = apply_damage_reduction(attacker, victim, damage)

    # Apply RIV (IMMUNE/RESIST/VULN) scaling before any side-effects.
    riv = _riv_check(victim, dam_type)
    immune = riv == 1
    if immune:  # IS_IMMUNE
        damage = 0
    elif riv == 2:  # IS_RESISTANT: dam -= dam/3 (ROM)
        damage = damage - c_div(damage, 3)
    elif riv == 3:  # IS_VULNERABLE: dam += dam/2 (ROM)
        damage = damage + c_div(damage, 2)

    # Invoke any on-hit effects with scaled damage (can be monkeypatched in tests).
    on_hit_effects(attacker, victim, damage)

    # Process weapon special attacks following C src/fight.c:one_hit L600-680
    weapon_special_messages = process_weapon_special_attacks(attacker, victim)

    # Apply damage and update fighting state (defenses checked inside apply_damage)
    main_message = apply_damage(attacker, victim, damage, dam_type, dt=attack_dt, immune=immune)

    # Combine main attack message with weapon special messages
    if weapon_special_messages:
        parts = [msg for msg in (main_message,) if msg]
        parts.extend(weapon_special_messages)
        return " ".join(parts)
    return main_message


def apply_damage(
    attacker: Character,
    victim: Character,
    damage: int,
    dam_type: int = None,
    *,
    dt: str | int | None = None,
    immune: bool = False,
    show: bool = True,
) -> str:
    """Apply damage and manage fighting state following C src/fight.c:damage logic.

    Handles:
    - Defense checks (parry, dodge, shield_block) - ROM checks these AFTER hit but BEFORE damage
    - Damage type resistance/vulnerability (ROM fight.c:804-816)
    - Damage application and hit point reduction
    - Position updates based on remaining hit points
    - Fighting state management (set_fighting, stop_fighting)
    - Position change messaging
    - Death handling

    Args:
        attacker: Character dealing damage
        victim: Character receiving damage
        damage: Final damage amount after all reductions
        dam_type: Damage type for defense checks

    Returns:
        Combat message describing the result
    """
    if victim.position == Position.DEAD:
        return "Already dead."

    if attacker != victim:
        from mud.combat.safety import is_safe

        # mirroring ROM src/fight.c:725-733 — damage() re-checks is_safe at entry
        if is_safe(attacker, victim):
            return ""

    # Set up fighting state BEFORE defense checks (ROM parity: src/fight.c:damage sets fighting before parry/dodge)
    if victim != attacker:
        if victim.position > Position.STUNNED:
            if victim.fighting is None:
                set_fighting(victim, attacker)
                if getattr(victim, "is_npc", False):
                    mobprog.mp_kill_trigger(victim, attacker)
            if getattr(victim, "timer", 0) <= 4:
                victim.position = Position.FIGHTING

        if victim.position > Position.STUNNED:
            if attacker.fighting is None:
                set_fighting(attacker, victim)

    # Check for parry, dodge, and shield block following C src/fight.c:790-800.
    # These are checked AFTER hit determination but BEFORE damage application.
    # Order is critical: parry → dodge → shield_block.
    if dam_type is not None and attacker != victim and _should_check_weapon_defenses(dt):
        if check_parry(attacker, victim):
            return f"{victim.name} parries your attack."
        if check_dodge(attacker, victim):
            return f"{victim.name} dodges your attack."
        if check_shield_block(attacker, victim):
            return f"{victim.name} blocks your attack with a shield."

    # Apply damage type resistance/vulnerability modifiers (ROM fight.c:804-816)
    # This must happen AFTER defense checks but BEFORE damage application
    if dam_type is not None:
        IS_IMMUNE = 1
        IS_RESISTANT = 2
        IS_VULNERABLE = 3

        immune_check = _riv_check(victim, dam_type)
        if immune_check == IS_IMMUNE:
            immune = True
            damage = 0
        elif immune_check == IS_RESISTANT:
            # ROM: dam -= dam / 3 (reduces damage by 33%)
            damage -= c_div(damage, 3)
        elif immune_check == IS_VULNERABLE:
            # ROM: dam += dam / 2 (increases damage by 50%)
            damage += c_div(damage, 2)

    message_bundle: DamageMessages | None = None
    if show:
        message_bundle = dam_message(attacker, victim, damage, dt, immune)
        _dispatch_damage_messages(attacker, victim, message_bundle)

    if damage <= 0:
        if message_bundle and message_bundle.attacker:
            from mud.combat.messages import render_for as _render
            return _render(message_bundle.attacker, attacker, victim, attacker) or ""
        return "Your attack has no effect."

    # Apply damage
    old_pos = victim.position
    victim.hit -= damage

    # Immortals don't die (ROM IS_IMMORTAL check)
    if not victim.is_npc and victim.is_immortal() and victim.hit < 1:
        victim.hit = 1

    # Update position based on hit points
    update_pos(victim)

    # Handle position change messages
    apply_position_change(victim, old_pos)

    # Stop fighting if unconscious
    if not is_awake(victim):
        stop_fighting(victim, False)

    # Handle death
    if victim.position == Position.DEAD:
        if getattr(victim, "is_npc", False):
            old_pos = victim.position
            victim.position = Position.STANDING
            try:
                mobprog.mp_death_trigger(victim, attacker)
            finally:
                victim.position = old_pos
        message = _handle_death(attacker, victim)
        return message

    if message_bundle and message_bundle.attacker:
        from mud.combat.messages import render_for as _render
        return _render(message_bundle.attacker, attacker, victim, attacker) or ""
    return ""


def set_fighting(ch: Character, victim: Character) -> None:
    """Start fighting following C src/fight.c:set_fighting logic.

    Sets ch->fighting = victim and ch->position = POS_FIGHTING.
    Strips sleep affect if present.
    """
    if ch.fighting is not None:
        # In ROM this would be a bug() call, but we'll handle gracefully
        return

    # Strip sleep affect if present
    if ch.has_affect(AffectFlag.SLEEP):
        ch.strip_affect("sleep")

    ch.fighting = victim
    ch.position = Position.FIGHTING


def stop_fighting(ch: Character, both: bool = True) -> None:
    """Stop fighting following C src/fight.c:stop_fighting logic."""

    def _default_position(target: Character) -> Position:
        default = getattr(target, "default_pos", Position.STANDING)
        try:
            return Position(default)
        except (TypeError, ValueError):
            return Position.STANDING

    candidates = list(character_registry)
    if not any(candidate is ch for candidate in candidates):
        candidates.append(ch)

    for fighter in candidates:
        if fighter is ch or (both and getattr(fighter, "fighting", None) is ch):
            fighter.fighting = None
            if getattr(fighter, "is_npc", False):
                fighter.position = _default_position(fighter)
            else:
                fighter.position = Position.STANDING
            update_pos(fighter)


def update_pos(victim: Character) -> None:
    """Update character position based on hit points following C src/fight.c:update_pos logic."""
    if victim.hit > 0:
        if victim.position <= Position.STUNNED:
            victim.position = Position.STANDING
        return

    # NPCs die immediately when hit <= 0
    if getattr(victim, "is_npc", True) and victim.hit < 1:
        victim.position = Position.DEAD
        return

    # PC death thresholds
    if victim.hit <= -11:
        victim.position = Position.DEAD
    elif victim.hit <= -6:
        victim.position = Position.MORTAL
    elif victim.hit <= -3:
        victim.position = Position.INCAP
    else:
        victim.position = Position.STUNNED


def is_awake(character: Character) -> bool:
    """ROM IS_AWAKE macro: position > POS_SLEEPING"""
    return character.position > Position.SLEEPING


def _broadcast_pos_change(victim: Character, template: str, **extra: object) -> None:
    """Render `$n`-style room broadcasts per-listener via ROM PERS.

    Mirrors ROM's `act(..., TO_ROOM)` macro, which evaluates
    ``PERS(victim, looker)`` once per recipient (see src/comm.c:act_new
    around the `$n` case). Each room observer gets its own substituted
    message, so an invisible victim renders as "someone" to anyone
    without DETECT_INVIS — matches the channel-arc fix pattern
    (mud/world/vision.py:pers).

    `template` must contain a `{name}` placeholder for the
    PERS-rendered victim name; any additional substitutions (e.g.
    `{weapon}` for ROM `$p`) come from `**extra`. Weapons are not
    `can_see`-gated, so they pass through verbatim.
    """
    from mud.mobprog import mp_act_trigger_room
    from mud.utils.messaging import push_message

    room = getattr(victim, "room", None)
    if room is None:
        return
    for listener in list(getattr(room, "people", [])):
        if listener is victim:
            continue
        # ROM src/comm.c:2376-2379 — act_new caps the first visible char of the
        # per-recipient buffer (INV-029 / FIGHT-031). PERS can render a different
        # name token per listener ("the orc" vs "someone"), so each rendered line
        # is capitalized individually, exactly as ROM caps each recipient's buf.
        message = capitalize_act_line(template.format(name=pers(victim, listener), **extra))
        # INV-001: single-channel delivery (push_message XOR) — the prior
        # if-writer-async + unconditional append double-delivered to a connected
        # PC. TRIG_ACT is dispatched separately below via mp_act_trigger_room.
        push_message(listener, message)
    # ROM src/fight.c:837-861 / src/comm.c:2384 — position-transition act()
    # calls have no MOBtrigger wrap; TRIG_ACT dispatches per recipient against
    # the already-capitalized buffer (the cap at :2376 precedes the trigger
    # dispatch at :2384, so the mob ACT-prog matches the capped line).
    canonical = capitalize_act_line(template.format(name=getattr(victim, "name", "Someone"), **extra))
    mp_act_trigger_room(canonical, room, victim, exclude=victim)


def apply_position_change(victim: Character, old_pos: Position) -> None:
    """Emit ROM position-transition messages after ``update_pos``.

    Mirrors ``src/fight.c:837-861`` — when ``damage()`` updates a
    victim's position, it broadcasts an ``act(... TO_ROOM)`` line
    and sends the to-self line via ``send_to_char``. ROM funnels
    every damage path through ``damage()``, so the broadcast is the
    natural consequence of any hp drop that crosses a threshold.

    Python's spell handlers in ``mud/skills/handlers.py`` bypass
    :func:`apply_damage` and call :func:`update_pos` directly — they
    must call this helper after ``update_pos`` to deliver the same
    room + self lines (INV-016 BCAST-ON-POSITION-TRANSITION).
    """
    if victim.position == old_pos:
        return
    message = _position_change_message(victim, old_pos)
    if message:
        _push_message(victim, message)


def _position_change_message(victim: Character, old_pos: Position) -> str:
    """Generate position change message following ROM logic."""
    if victim.position == Position.MORTAL:
        # mirroring ROM src/fight.c:837-838 — `act("$n is mortally
        # wounded, and will die soon, if not aided.", victim, NULL,
        # NULL, TO_ROOM)`. The act() macro renders `$n` per-listener
        # through PERS(victim, looker), so an invisible victim
        # appears as "someone" to room observers without
        # DETECT_INVIS (FIGHT-004). Each recipient gets its own
        # substituted string — `_broadcast_room` with a baked
        # f-string would leak the victim's name.
        if hasattr(victim, "room") and victim.room is not None:
            _broadcast_pos_change(
                victim,
                "{name} is mortally wounded, and will die soon, if not aided.",
            )
        return "You are mortally wounded, and will die soon, if not aided."
    elif victim.position == Position.INCAP:
        # mirroring ROM src/fight.c:845-846 — `act("$n is incapacitated
        # and will slowly die, if not aided.", victim, NULL, NULL,
        # TO_ROOM)`. PERS substitution per-listener (FIGHT-005).
        if hasattr(victim, "room") and victim.room is not None:
            _broadcast_pos_change(
                victim,
                "{name} is incapacitated and will slowly die, if not aided.",
            )
        return "You are incapacitated and will slowly die, if not aided."
    elif victim.position == Position.STUNNED:
        # mirroring ROM src/fight.c:853-854 — `act("$n is stunned, but
        # will probably recover.", victim, NULL, NULL, TO_ROOM)`. PERS
        # substitution per-listener (FIGHT-006).
        if hasattr(victim, "room") and victim.room is not None:
            _broadcast_pos_change(
                victim,
                "{name} is stunned, but will probably recover.",
            )
        return "You are stunned, but will probably recover."
    elif victim.position == Position.DEAD:
        # mirroring ROM src/fight.c:860 — `act("{R$n is DEAD!!{x",
        # victim, 0, 0, TO_ROOM)`. PERS substitution per-listener
        # (FIGHT-007), wrapped in ROM red colour codes ({R...{x) the
        # ANSI translation layer consumes on websocket send, and ROM
        # uses exactly two exclamation marks (not three).
        if hasattr(victim, "room") and victim.room is not None:
            _broadcast_pos_change(victim, "{{R{name} is DEAD!!{{x")
        # mirroring ROM src/fight.c:861 — `send_to_char("{RYou have
        # been KILLED!!{x\n\r\n\r", victim)`. ROM's two trailing
        # \n\r pairs render as the death notice + one blank line.
        # Python's protocol layer auto-appends one \r\n to every
        # message, so the embedded trailing \n here gives the blank
        # line on the wire (FIGHT-008). Red colour wrap {R...{x is
        # consumed by mud/net/ansi.py on websocket send.
        return "{RYou have been KILLED!!{x\n"
    return ""


def _player_has_flag(character: Character | None, flag: PlayerFlag) -> bool:
    """Return True when *character* is a PC with *flag* set."""

    if character is None or getattr(character, "is_npc", False):
        return False
    try:
        return bool(int(getattr(character, "act", 0) or 0) & int(flag))
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return False


def _corpse_is_npc(corpse) -> bool:
    try:
        return int(getattr(corpse, "item_type", 0)) == int(ItemType.CORPSE_NPC)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return False


def _object_has_wear_flag(obj, flag: WearFlag) -> bool:
    """Return True when *obj* or its prototype includes the provided wear flag."""

    try:
        wear_flags = int(getattr(obj, "wear_flags", 0) or 0)
    except (TypeError, ValueError):
        wear_flags = 0
    if wear_flags & int(flag):
        return True

    proto = getattr(obj, "prototype", None)
    if proto is None:
        return False

    try:
        proto_flags = int(getattr(proto, "wear_flags", 0) or 0)
    except (TypeError, ValueError):
        proto_flags = 0
    return bool(proto_flags & int(flag))


def _transfer_corpse_coins(attacker: Character, corpse) -> bool:
    """Extract gold/silver from money objects and add to attacker's purse.

    ROM Reference: src/fight.c auto_loot handles money extraction.
    QuickMUD uses actual money objects (ItemType.MONEY) instead of corpse attributes.
    Money objects may already be in attacker's inventory if AUTOLOOT moved them.
    """
    from mud.models.constants import ItemType

    contained = list(getattr(corpse, "contained_items", []) or [])
    attacker_inv = list(getattr(attacker, "inventory", []) or [])

    money_in_corpse = [obj for obj in contained if getattr(obj, "item_type", None) == int(ItemType.MONEY)]
    money_in_inventory = [obj for obj in attacker_inv if getattr(obj, "item_type", None) == int(ItemType.MONEY)]

    all_money_objects = money_in_corpse + money_in_inventory

    if not all_money_objects:
        return False

    total_gold = 0
    total_silver = 0

    for money_obj in all_money_objects:
        values = list(getattr(money_obj, "value", [0, 0]) or [0, 0])
        while len(values) < 2:
            values.append(0)

        silver = int(values[0] or 0)
        gold = int(values[1] or 0)

        total_silver += silver
        total_gold += gold

        if money_obj in money_in_corpse:
            try:
                corpse.contained_items.remove(money_obj)
            except (AttributeError, ValueError):
                pass
        else:
            try:
                attacker.remove_object(money_obj)
            except (AttributeError, ValueError):
                pass

    attacker.gold = int(getattr(attacker, "gold", 0) or 0) + total_gold
    attacker.silver = int(getattr(attacker, "silver", 0) or 0) + total_silver

    return True


def _auto_collect_loot(attacker: Character, corpse) -> bool:
    """Auto-loot NPC corpses when the attacker has PLR_AUTOLOOT enabled."""

    if not _player_has_flag(attacker, PlayerFlag.AUTOLOOT):
        return False
    if not _corpse_is_npc(corpse):
        return False

    moved = False
    contained = list(getattr(corpse, "contained_items", []) or [])
    for obj in contained:
        try:
            corpse.contained_items.remove(obj)
        except (AttributeError, ValueError):  # pragma: no cover - defensive guard
            continue
        attacker.add_object(obj)
        if hasattr(obj, "location"):
            obj.location = attacker
        moved = True

    if _transfer_corpse_coins(attacker, corpse):
        moved = True

    if moved:
        _push_message(attacker, "You quickly gather the loot from the corpse.")
    return moved


def _auto_collect_coins(attacker: Character, corpse) -> bool:
    """Auto-gather corpse coins when only AUTOGOLD is toggled."""

    if not _player_has_flag(attacker, PlayerFlag.AUTOGOLD):
        return False
    if _player_has_flag(attacker, PlayerFlag.AUTOLOOT):
        return False
    if not _corpse_is_npc(corpse):
        return False
    if not _transfer_corpse_coins(attacker, corpse):
        return False

    _push_message(attacker, "You quickly gather the loot from the corpse.")
    return True


def _auto_sacrifice(attacker: Character, corpse) -> None:
    """Sacrifice empty NPC corpses when AUTOSAC is enabled, mirroring ROM."""

    if not _player_has_flag(attacker, PlayerFlag.AUTOSAC):
        return
    if not _corpse_is_npc(corpse):
        return
    if _player_has_flag(attacker, PlayerFlag.AUTOLOOT) and getattr(corpse, "contained_items", []):
        return

    if not can_see_object(attacker, corpse):
        return

    room = getattr(corpse, "location", None) or getattr(attacker, "room", None)
    if room is None:
        return

    if not _object_has_wear_flag(corpse, WearFlag.TAKE):
        return
    if _object_has_wear_flag(corpse, WearFlag.NO_SAC):
        return

    corpse_level = max(0, int(getattr(corpse, "level", 0) or 0))
    silver_reward = max(1, corpse_level * 3)
    current_silver = max(0, int(getattr(attacker, "silver", 0) or 0))

    attacker.silver = current_silver + silver_reward
    if silver_reward == 1:
        _push_message(attacker, "Mota gives you one silver coin for your sacrifice.")
    else:
        _push_message(attacker, f"Mota gives you {silver_reward} silver coins for your sacrifice.")

    corpse_name = getattr(corpse, "short_descr", None) or getattr(corpse, "name", "") or "corpse"
    # mirroring ROM src/act_obj.c:1856 dispatched from
    # src/fight.c:961-970 — `act("$n sacrifices $p to Mota.", ch,
    # obj, NULL, TO_ROOM)`. PERS substitution on $n (attacker)
    # per-listener (FIGHT-014). The helper's first arg is named
    # `victim` for historical reasons but the function just
    # PERS-renders that character for each room observer — works
    # equally for an attacker. Corpse name passes through verbatim
    # ($p is not can_see-gated).
    _broadcast_pos_change(
        attacker,
        "{name} sacrifices {corpse} to Mota.",
        corpse=corpse_name,
    )
    wiznet(
        "$N sends up $p as a burnt offering.",
        attacker,
        corpse,
        WiznetFlag.WIZ_SACCING,
        None,
        0,
    )

    try:
        from mud.game_loop import _extract_obj as _legacy_extract_obj
    except ImportError:  # pragma: no cover - defensive guard
        _legacy_extract_obj = None

    if _legacy_extract_obj is not None:
        _legacy_extract_obj(corpse)
    else:  # pragma: no cover - fallback for isolated tests
        for item in list(getattr(corpse, "contained_items", []) or []):
            if hasattr(item, "location") and getattr(item, "location", None) is corpse:
                item.location = None
        if hasattr(corpse, "contained_items"):
            try:
                corpse.contained_items.clear()
            except AttributeError:
                corpse.contained_items = []
        corpse.gold = 0
        corpse.silver = 0

    if hasattr(corpse, "contained_items"):
        try:
            corpse.contained_items.clear()
        except AttributeError:  # pragma: no cover - defensive guard
            corpse.contained_items = []
    corpse.gold = 0
    corpse.silver = 0

    if hasattr(room, "contents") and corpse in room.contents:
        room.contents.remove(corpse)
    if hasattr(corpse, "location"):
        corpse.location = None

    if not _player_has_flag(attacker, PlayerFlag.AUTOSPLIT):
        return

    people = list(getattr(room, "people", []) or [])
    group_members: list[Character] = []
    for member in people:
        if not is_same_group(member, attacker):
            continue
        if hasattr(member, "has_affect") and member.has_affect(AffectFlag.CHARM):
            continue
        group_members.append(member)

    member_count = len(group_members)
    if member_count < 2:
        _push_message(attacker, "Just keep it all.")
        return
    if silver_reward <= 1:
        return

    share = silver_reward // member_count
    remainder = silver_reward % member_count
    if share == 0:
        _push_message(attacker, "Don't even bother, cheapskate.")
        return

    attacker.silver = current_silver + share + remainder
    _push_message(attacker, f"You split {silver_reward} silver coins. Your share is {share + remainder} silver.")

    # ROM src/act_comm.c:1946-1962 — per-member act("$n splits %d silver coins. Your
    # share is %d silver.", ch, NULL, gch, TO_VICT). $n resolves through PERS(ch, gch)
    # per recipient (masking invisible actors) and act_new caps the first letter
    # (src/comm.c:2376). FIGHT-034.
    from mud.utils.messaging import push_message

    for member in group_members:
        if member is attacker:
            continue
        member.silver = max(0, int(getattr(member, "silver", 0) or 0)) + share
        # Per-recipient PERS + capitalize, matching ROM act(TO_VICT).
        member_msg = capitalize_act_line(f"{pers(attacker, member)} splits {silver_reward} silver coins. Your share is {share} silver.")
        # INV-001: single-channel delivery (push_message XOR).
        push_message(member, member_msg)


def _handle_auto_actions(attacker: Character, corpse) -> None:
    if attacker is None or corpse is None:
        return
    if getattr(attacker, "is_npc", False):
        return
    if not _corpse_is_npc(corpse):
        return

    message_sent = _auto_collect_loot(attacker, corpse)
    if not message_sent:
        _auto_collect_coins(attacker, corpse)
    _auto_sacrifice(attacker, corpse)


def _clear_pk_flags(attacker: Character, victim: Character) -> None:
    if attacker is victim or attacker is None:
        return
    if getattr(attacker, "is_npc", False):
        return
    if is_same_clan(attacker, victim):
        return

    try:
        act_value = int(getattr(victim, "act", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return

    if act_value & int(PlayerFlag.KILLER):
        victim.act = act_value & ~int(PlayerFlag.KILLER)
    elif act_value & int(PlayerFlag.THIEF):
        victim.act = act_value & ~int(PlayerFlag.THIEF)


def _character_is_charmed(character: Character | None) -> bool:
    if character is None:
        return False
    if hasattr(character, "has_spell_effect") and character.has_spell_effect("charm person"):
        return True
    return hasattr(character, "has_affect") and character.has_affect(AffectFlag.CHARM)


def check_killer(attacker: Character | None, victim: Character | None) -> None:
    if attacker is None or victim is None:
        return

    resolved_victim = victim
    while _character_is_charmed(resolved_victim) and getattr(resolved_victim, "master", None) is not None:
        resolved_victim = resolved_victim.master

    if getattr(resolved_victim, "is_npc", False):
        return

    victim_act = _coerce_int(getattr(resolved_victim, "act", 0))
    if victim_act & int(PlayerFlag.KILLER) or victim_act & int(PlayerFlag.THIEF):
        return

    if _character_is_charmed(attacker):
        master = getattr(attacker, "master", None)
        if master is None:
            if attacker.strip_affect("charm person") and hasattr(attacker, "has_affect"):
                attacker.remove_affect(AffectFlag.CHARM)
        stop_follower(attacker)
        return

    if getattr(attacker, "is_npc", False):
        return

    if attacker is resolved_victim:
        return

    attacker_level = _coerce_int(getattr(attacker, "level", 0))
    if attacker_level >= LEVEL_IMMORTAL:
        return

    if not is_clan_member(attacker):
        return

    attacker_act = _coerce_int(getattr(attacker, "act", 0))
    if attacker_act & int(PlayerFlag.KILLER):
        return

    if getattr(attacker, "fighting", None) is resolved_victim:
        return

    _push_message(attacker, "*** You are now a KILLER!! ***")
    attacker.act = attacker_act | int(PlayerFlag.KILLER)
    victim_name = getattr(resolved_victim, "name", None) or "someone"
    wiznet(f"$N is attempting to murder {victim_name}", attacker, None, WiznetFlag.WIZ_FLAGS, None, 0)
    save_character(attacker)


def _send_wiznet_death(attacker: Character, victim: Character) -> None:
    victim_name = getattr(victim, "short_descr", None) or getattr(victim, "name", "Someone")
    if attacker is not None:
        attacker_name = (
            getattr(attacker, "short_descr", None)
            if getattr(attacker, "is_npc", False)
            else getattr(attacker, "name", None)
        )
    else:
        attacker_name = None
    if not attacker_name:
        attacker_name = "Someone"

    room = getattr(attacker, "room", None) if attacker is not None else None
    if room is None:
        room = getattr(victim, "room", None)
    room_name = getattr(room, "name", "somewhere")
    room_vnum = getattr(room, "vnum", 0)

    message = f"{victim_name} got toasted by {attacker_name} at {room_name} [room {room_vnum}]"
    flag = WiznetFlag.WIZ_MOBDEATHS if getattr(victim, "is_npc", False) else WiznetFlag.WIZ_DEATHS
    wiznet(message, attacker, victim, flag, None, 0)


def _handle_death(attacker: Character, victim: Character) -> str:
    """Handle character death following ROM logic."""
    # Defensive bidirectional clear of fighting pointers. ROM
    # src/fight.c:damage death branch relies on raw_kill →
    # stop_fighting(victim, TRUE) to sweep char_list and clear every
    # fighter whose fighting == victim. We do the same via
    # _stop_fighting(victim, True) in mud/combat/death.py:561. The
    # explicit clears here cover the killing-blow attacker even before
    # the sweep runs; redundant in the single-attacker case but cheap
    # and load-bearing for read clarity.
    attacker.fighting = None
    victim.fighting = None
    attacker.position = Position.STANDING

    group_gain(attacker, victim)
    if not getattr(victim, "is_npc", False):
        # mirroring ROM src/fight.c:887-893 — player deaths lose
        # 2/3 of the surplus back toward the previous level, plus 50.
        base = exp_per_level(victim)
        floor = base * _coerce_int(getattr(victim, "level", 0))
        if _coerce_int(getattr(victim, "exp", 0)) > floor:
            gain_exp(victim, c_div(2 * (floor - victim.exp), 3) + 50)
    _send_wiznet_death(attacker, victim)

    corpse = raw_kill(victim)

    _clear_pk_flags(attacker, victim)
    _handle_auto_actions(attacker, corpse)

    victim_name = getattr(victim, "name", None) or getattr(victim, "short_descr", "them")
    return f"You kill {victim_name}."


def calculate_weapon_damage(
    attacker: Character,
    victim: Character,
    dam_type: int,
    *,
    wield=None,
    skill: int | None = None,
    dt: str | int | None = None,
) -> int:
    """Calculate weapon damage following C src/fight.c:one_hit logic.

    This includes:
    - Weapon dice rolling with skill modifiers
    - Shield bonus (11/10 multiplier when no shield equipped)
    - Sharpness weapon effect
    - Enhanced damage skill
    - Position-based multipliers (sleeping/resting victims)
    - Damroll bonus application
    """
    if wield is None:
        wield = get_wielded_weapon(attacker)

    if skill is None:
        weapon_sn = get_weapon_sn(attacker, wield)
        weapon_skill = get_weapon_skill(attacker, weapon_sn)
        skill_total = 20 + weapon_skill
    else:
        skill_total = int(skill)

    if skill_total <= 0:
        skill_total = 1

    # Base damage calculation
    if wield is not None and _is_weapon(wield):
        # Weapon damage from dice
        values = _weapon_values(wield)
        if _weapon_is_new_format(wield) and len(values) > 2:
            dice_number = max(0, values[1])
            dice_type = max(0, values[2])
            dam = rng_mm.dice(dice_number, dice_type) * skill_total // 100
        else:
            min_val = values[1] if len(values) > 1 else 0
            max_val = values[2] if len(values) > 2 else 0
            min_dam = min_val * skill_total // 100
            max_dam = max_val * skill_total // 100
            dam = rng_mm.number_range(min_dam, max_dam)

        # Shield bonus - no shield equipped gives 11/10 multiplier
        if not _has_shield_equipped(attacker):
            dam = c_div(dam * 11, 10)

        # Sharpness weapon effect
        if hasattr(wield, "weapon_stats") and "sharp" in wield.weapon_stats:
            percent = rng_mm.number_percent()
            if percent <= (skill_total // 8):
                dam = 2 * dam + (dam * 2 * percent // 100)
    elif getattr(attacker, "is_npc", False):
        # NPC with no wielded weapon — ROM src/fight.c:522-530 rolls the mob's own
        # damage dice: `dam = dice(ch->damage[DICE_NUMBER], ch->damage[DICE_TYPE])`.
        # Source of truth is the MobInstance.damage tuple == (DICE_NUMBER, DICE_TYPE,
        # bonus); the bonus is applied below via damroll (MobInstance.damroll ==
        # damage[2]). Do NOT key on the proto `new_format` flag — it is unreliable in
        # the Python loader (False even on dice-carrying mobs like the drunk #3064);
        # the loader populates valid dice regardless (verified: all 986 mob protos
        # resolve to non-zero damage[0]/damage[1], so dice() never collapses to 0→1
        # here). This mirrors ROM at runtime, where convert_mobile (src/db.c) upgrades
        # every mob to new_format at load, making the `!new_format`
        # `number_range(level/2, level*3/2)` sub-branch dead code.
        dice_spec = getattr(attacker, "damage", (0, 0, 0)) or (0, 0, 0)
        dam = rng_mm.dice(int(dice_spec[0]), int(dice_spec[1]))
    else:
        # PC unarmed damage from ROM C: number_range(1 + 4*skill/100, 2*ch->level/3*skill/100)
        # This is the exact ROM formula from src/fight.c:556-559
        min_dam = 1 + (4 * skill_total // 100)
        max_dam = (2 * attacker.level // 3) * skill_total // 100
        # ROM allows max_dam to be less than min_dam for very low levels
        dam = rng_mm.number_range(min_dam, max_dam)

    # Enhanced damage skill
    enhanced_damage_skill = _get_skill_percent(attacker, "enhanced damage", "enhanced_damage_skill")
    if enhanced_damage_skill > 0:
        diceroll = rng_mm.number_percent()
        if diceroll <= enhanced_damage_skill:
            check_improve(attacker, "enhanced damage", True, 6)
            dam += 2 * (dam * diceroll // 300)

    # Position-based damage multipliers
    # IS_AWAKE in ROM means position > POS_SLEEPING
    if victim.position <= Position.SLEEPING:
        dam *= 2
    elif victim.position < Position.FIGHTING:
        dam = dam * 3 // 2

    dt_name = _normalize_dt(dt)
    if dt_name == "backstab" and wield is not None:
        weapon_type = _weapon_type(wield)
        level = int(getattr(attacker, "level", 0) or 0)
        if weapon_type == WeaponType.DAGGER:
            multiplier = 2 + c_div(level, 8)
        else:
            multiplier = 2 + c_div(level, 10)
        dam *= max(2, multiplier)

    # Add damroll bonus - ROM: GET_DAMROLL(ch) * UMIN(100, skill) / 100
    # ROM src/merc.h:2109-2110 GET_DAMROLL adds str_app[STR].todam to ch->damroll.
    # MATH-001: ROM C `/` truncates toward zero; Python `//` floors toward
    # negative infinity. With cursed gear get_damroll can be negative, so the
    # product can be negative — must use c_div to match ROM.
    dam += c_div(get_damroll(attacker) * min(100, skill_total), 100)

    # Ensure minimum damage - ROM: if (dam <= 0) dam = 1
    if dam <= 0:
        dam = 1

    return dam


def apply_damage_reduction(attacker: Character, victim: Character, damage: int) -> int:
    """Apply damage reduction following C src/fight.c:damage logic.

    Order of reductions (all use C integer division):
    1. Drunk condition: 9/10 damage if victim drunk > 10
    2. Sanctuary: halve damage if victim has sanctuary affect
    3. Protection spells: -25% if victim has protect_evil/good vs opposing alignment

    Args:
        attacker: Character dealing damage
        victim: Character receiving damage
        damage: Base damage before reductions

    Returns:
        Reduced damage amount
    """
    # Drunk condition reduces damage (victim only, PC only)
    if (
        damage > 1
        and victim.pcdata is not None
        and len(victim.pcdata.condition) > 0  # COND_DRUNK = 0
        and victim.pcdata.condition[0] > 10
    ):
        damage = c_div(9 * damage, 10)

    # Sanctuary halves damage
    if damage > 1 and victim.has_affect(AffectFlag.SANCTUARY):
        damage = c_div(damage, 2)

    # Protection spells reduce damage by 25% vs opposing alignment
    if damage > 1:
        victim_protect_evil = victim.has_affect(AffectFlag.PROTECT_EVIL)
        victim_protect_good = victim.has_affect(AffectFlag.PROTECT_GOOD)

        # Check attacker alignment and apply reductions
        if (victim_protect_evil and is_evil(attacker)) or (victim_protect_good and is_good(attacker)):
            damage -= c_div(damage, 4)

    return damage


def is_good(character: Character) -> bool:
    """ROM IS_GOOD macro: alignment >= 350"""
    return character.alignment >= 350


def is_evil(character: Character) -> bool:
    """ROM IS_EVIL macro: alignment <= -350"""
    return character.alignment <= -350


def is_neutral(character: Character) -> bool:
    """ROM IS_NEUTRAL macro: !IS_GOOD && !IS_EVIL"""
    return not is_good(character) and not is_evil(character)


def on_hit_effects(attacker: Character, victim: Character, damage: int) -> None:  # pragma: no cover - default no-op
    """Hook for on-hit side-effects; receives RIV-scaled damage."""
    return None


# --- Defense checks following C src/fight.c logic ---
def check_shield_block(attacker: Character, victim: Character) -> bool:
    """Shield block check following C src/fight.c:check_shield_block logic.

    Requirements:
    - Victim must be awake (position > POS_SLEEPING)
    - Victim must have a shield equipped
    - Base chance = get_skill(victim, gsn_shield_block) / 5 + 3
    - Modified by level difference: chance + victim.level - attacker.level
    """
    if not is_awake(victim):
        return False

    if not _has_shield_equipped(victim):
        return False

    shield_skill = _get_skill_percent(victim, "shield block", "shield_block_skill")
    chance = c_div(shield_skill, 5) + 3

    # Level difference modifier
    chance += victim.level - attacker.level

    if rng_mm.number_percent() >= chance:
        return False

    # ROM src/fight.c:1343-1346 — act("You block $n's attack with your shield.", …, TO_VICT)
    # and act("$N blocks your attack with a shield.", …, TO_CHAR). Both route $n/$N through
    # PERS(ch/victim, looker), which masks invisible actors to "someone" and uses short_descr
    # for NPCs. FIGHT-032.
    _push_message(victim, f"You block {pers(attacker, victim)}'s attack with your shield.")
    # ROM src/fight.c:1346 — the defender name leads, so ROM act_new caps it (FIGHT-031).
    _push_message(attacker, capitalize_act_line(f"{pers(victim, attacker)} blocks your attack with a shield."))
    check_improve(victim, "shield block", True, 6)
    return True


def check_parry(attacker: Character, victim: Character) -> bool:
    """Parry check following C src/fight.c:check_parry logic.

    Requirements:
    - Victim must be awake (position > POS_SLEEPING)
    - Victim should have weapon equipped (NPCs can parry unarmed at half chance)
    - Base chance = get_skill(victim, gsn_parry) / 2
    - Halved if victim can't see attacker
    - Modified by level difference: chance + victim.level - attacker.level
    """
    if not is_awake(victim):
        return False

    parry_skill = _get_skill_percent(victim, "parry", "parry_skill")
    chance = c_div(parry_skill, 2)

    has_weapon = getattr(victim, "has_weapon_equipped", False)
    if not has_weapon:
        if getattr(victim, "is_npc", False):
            chance = c_div(chance, 2)  # NPCs can parry unarmed at half chance
        else:
            return False  # PCs need weapons to parry

    # Visibility modifier
    if not getattr(victim, "can_see", lambda x: True)(attacker):
        chance = c_div(chance, 2)

    # Level difference modifier
    chance += victim.level - attacker.level

    if rng_mm.number_percent() >= chance:
        return False

    # ROM src/fight.c:1316-1318 — act("You parry $n's attack.", …, TO_VICT)
    # and act("$N parries your attack.", …, TO_CHAR). Both route $n/$N through
    # PERS(ch/victim, looker), masking invisible actors and using short_descr for NPCs.
    # FIGHT-032.
    _push_message(victim, f"You parry {pers(attacker, victim)}'s attack.")
    # ROM src/fight.c:1318 — defender name leads, ROM act_new caps it (FIGHT-031).
    _push_message(attacker, capitalize_act_line(f"{pers(victim, attacker)} parries your attack."))
    check_improve(victim, "parry", True, 6)
    return True


def check_dodge(attacker: Character, victim: Character) -> bool:
    """Dodge check following C src/fight.c:check_dodge logic.

    Requirements:
    - Victim must be awake (position > POS_SLEEPING)
    - Base chance = get_skill(victim, gsn_dodge) / 2
    - Halved if victim can't see attacker
    - Modified by level difference: chance + victim.level - attacker.level
    """
    if not is_awake(victim):
        return False

    dodge_skill = _get_skill_percent(victim, "dodge", "dodge_skill")
    chance = c_div(dodge_skill, 2)

    # Visibility modifier
    if not getattr(victim, "can_see", lambda x: True)(attacker):
        chance = c_div(chance, 2)

    # Level difference modifier
    chance += victim.level - attacker.level

    if rng_mm.number_percent() >= chance:
        return False

    # ROM src/fight.c:1362-1370 — act("You dodge $n's attack.", …, TO_VICT)
    # and act("$N dodges your attack.", …, TO_CHAR). Both route $n/$N through
    # PERS(ch/victim, looker), masking invisible actors and using short_descr for NPCs.
    # FIGHT-032.
    _push_message(victim, f"You dodge {pers(attacker, victim)}'s attack.")
    # ROM src/fight.c:1370 — defender name leads, ROM act_new caps it (FIGHT-031).
    _push_message(attacker, capitalize_act_line(f"{pers(victim, attacker)} dodges your attack."))
    check_improve(victim, "dodge", True, 6)
    return True


# --- AC mapping helpers ---
def ac_index_for_dam_type(dam_type: int) -> int:
    """Map a damage type to the correct AC index.

    ROM maps: PIERCE→AC_PIERCE, BASH→AC_BASH, SLASH→AC_SLASH, everything else→AC_EXOTIC.
    Unarmed (NONE) is treated as BASH.
    """
    dt = DamageType(dam_type) if not isinstance(dam_type, DamageType) else dam_type
    if dt == DamageType.PIERCE:
        return AC_PIERCE
    if dt == DamageType.BASH or dt == DamageType.NONE:
        return AC_BASH
    if dt == DamageType.SLASH:
        return AC_SLASH
    return AC_EXOTIC


def is_better_ac(ac_a: int, ac_b: int) -> bool:
    """Return True if ac_a is better protection than ac_b (more negative)."""
    return ac_a < ac_b


# --- THAC0 interpolation (ROM-inspired) ---
# Class ids align with FMANA mapping used elsewhere: 0:mage, 1:cleric, 2:thief, 3:warrior
THAC0_TABLE: dict[int, tuple[int, int]] = {
    0: (20, 6),  # mage
    1: (20, 2),  # cleric
    2: (20, -4),  # thief
    3: (20, -10),  # warrior
}


def interpolate(level: int, v00: int, v32: int) -> int:
    """ROM-like integer interpolate between level 0 and 32 using C division."""
    return v00 + c_div((v32 - v00) * level, 32)


def compute_thac0(
    level: int, ch_class: int, *, hitroll: int = 0, skill: int = 100, thac0_pair: tuple[int, int] | None = None
) -> int:
    """Compute THAC0 following ROM fight.c adjustments.

    - interpolate(level, thac0_00, thac0_32)
    - if thac0 < 0: thac0 = thac0 / 2 (C div)
    - if thac0 < -5: thac0 = -5 + (thac0 + 5)/2 (C div)
    - thac0 -= hitroll * skill / 100
    - thac0 += 5 * (100 - skill) / 100

    ``thac0_pair`` overrides the (thac0_00, thac0_32) source — used for NPC
    attackers, whose pair comes from ACT flags rather than the PC class table
    (ROM src/fight.c:445-457).
    """
    t00, t32 = thac0_pair if thac0_pair is not None else THAC0_TABLE.get(ch_class, (20, 6))
    th = interpolate(level, t00, t32)
    if th < 0:
        th = c_div(th, 2)
    if th < -5:
        th = -5 + c_div(th + 5, 2)
    th -= c_div(hitroll * skill, 100)
    th += c_div(5 * (100 - skill), 100)
    return th


def process_weapon_special_attacks(attacker: Character, victim: Character) -> list[str]:
    """Process weapon special attacks following C src/fight.c:one_hit L600-680.

    Applies special weapon effects after a successful hit:
    - WEAPON_POISON: Apply poison affect if save fails
    - WEAPON_VAMPIRIC: Drain life and heal attacker
    - WEAPON_FLAMING: Fire damage
    - WEAPON_FROST: Cold damage
    - WEAPON_SHOCKING: Lightning damage

    Returns list of messages describing special attack effects.
    """
    messages = []

    wield = get_wielded_weapon(attacker)
    if wield is None:
        return messages

    current_target = getattr(attacker, "fighting", None)
    if current_target is not None and current_target is not victim:
        return messages

    # Get weapon flags - support both extra_flags (for ObjIndex) and weapon_flags attribute
    weapon_flags = 0
    if hasattr(wield, "weapon_flags"):
        weapon_flags = int(wield.weapon_flags)
    elif hasattr(wield, "extra_flags"):
        weapon_flags = int(wield.extra_flags)

    weapon_level = _weapon_level(wield) or 1
    weapon_name = getattr(wield, "name", None) or getattr(wield, "short_descr", None) or "the weapon"
    room = getattr(victim, "room", None)

    # WEAPON_POISON - ROM src/fight.c L600-636
    if weapon_flags & WEAPON_POISON:
        # FIGHT-017: ROM derives the poison level from a TEMPORARY envenom
        # affect on the weapon if present — `affect_find(wield->affected,
        # gsn_poison)` → `poison->level`, else `wield->level`
        # (src/fight.c:605-608). The envenom path (spell_poison on an object,
        # mud/skills/handlers.py:6388) stores such an affect with
        # `spell_name == "poison"` on `wield.affected`.
        poison_af = None
        affected = getattr(wield, "affected", None)
        for af in affected if isinstance(affected, list) else []:
            name = getattr(af, "spell_name", None) or getattr(af, "type", None)
            if name == "poison":
                poison_af = af
                break

        if poison_af is None:
            # ARITH-004 (⛔ N/A): ROM `src/fight.c:606` uses `wield->level` raw,
            # but the `max(1, ...)` floor here is behaviorally dead —
            # `weapon_level` is only ever consumed via `// 2` (and the other
            # procs via `// N (+const)`), and `0 // N == 1 // N == 0` for N >= 2,
            # so flooring a level-0 weapon to 1 never changes an observable
            # value. `weapon_level` is also already floored at line 1556
            # (`_weapon_level(wield) or 1`).
            level = max(1, weapon_level)
        else:
            # ROM src/fight.c:608 — `level = poison->level` raw (no floor; a
            # level-0 envenom must still pass saves_spell(0, ...) and weaken).
            level = max(0, int(getattr(poison_af, "level", 0) or 0))

        if not saves_spell(level // 2, victim, DamageType.POISON):
            _push_message(victim, "You feel poison coursing through your veins.")
            if room is not None:
                # mirroring ROM src/fight.c:614-615 — `act("$n is
                # poisoned by the venom on $p.", victim, wield, NULL,
                # TO_ROOM)`. PERS substitution on $n per-listener
                # (FIGHT-009). Weapon name passes verbatim ($p is not
                # can_see-gated).
                _broadcast_pos_change(
                    victim,
                    "{name} is poisoned by the venom on {weapon}.",
                    weapon=weapon_name,
                )
            # mirroring ROM src/fight.c:616-624 — affect_join a structured
            # AFF_POISON affect, not a bare flag: af.level = level*3/4,
            # af.duration = level/2, af.location = APPLY_STR, af.modifier = -1.
            # Character.apply_spell_effect is the Python affect_join port.
            if hasattr(victim, "apply_spell_effect"):
                victim.apply_spell_effect(
                    SpellEffect(
                        name="poison",
                        level=c_div(level * 3, 4),
                        duration=c_div(level, 2),
                        stat_modifiers={Stat.STR: -1},
                        affect_flag=AffectFlag.POISON,
                        wear_off_message="You feel less sick.",
                    )
                )
            elif hasattr(victim, "add_affect"):
                victim.add_affect(AffectFlag.POISON)
            messages.append("You feel poison coursing through your veins.")

        # FIGHT-017: weaken a temporary envenom per hit — ROM src/fight.c:627-636.
        # This sits OUTSIDE the save block: weakening happens whether or not the
        # victim saved. Permanent WEAPON_POISON weapons have no envenom affect
        # (poison_af is None) and are never weakened.
        if poison_af is not None:
            poison_af.level = max(0, int(getattr(poison_af, "level", 0) or 0) - 2)
            poison_af.duration = max(0, int(getattr(poison_af, "duration", 0) or 0) - 1)
            if poison_af.level == 0 or poison_af.duration == 0:
                # ROM act("The poison on $p has worn off.", ch, wield, NULL,
                # TO_CHAR) — to the wielder (attacker), not the victim.
                _push_message(attacker, f"The poison on {weapon_name} has worn off.")

    # WEAPON_VAMPIRIC - ROM src/fight.c L640-649
    if weapon_flags & WEAPON_VAMPIRIC:
        dam = rng_mm.number_range(1, weapon_level // 5 + 1)
        _push_message(victim, f"You feel {weapon_name} drawing your life away.")
        if room is not None:
            # mirroring ROM src/fight.c:643 — `act("$p draws life
            # from $n.", victim, wield, NULL, TO_ROOM)`. PERS on $n
            # per-listener (FIGHT-010).
            _broadcast_pos_change(
                victim,
                "{weapon} draws life from {name}.",
                weapon=weapon_name,
            )

        # Apply vampiric damage (additional negative damage) without extra messages
        apply_damage(attacker, victim, dam, DamageType.NEGATIVE, show=False)

        # Heal attacker by half the damage
        attacker.hit += dam // 2
        if hasattr(attacker, "max_hit") and getattr(attacker, "max_hit", 0):
            attacker.hit = min(attacker.hit, attacker.max_hit)

        # Shift alignment toward evil (ROM: ch->alignment = UMAX(-1000, ch->alignment - 1))
        if hasattr(attacker, "alignment"):
            attacker.alignment = max(-1000, attacker.alignment - 1)

        messages.append(f"You feel {weapon_name} drawing your life away.")

    # WEAPON_FLAMING - ROM src/fight.c L651-659
    if weapon_flags & WEAPON_FLAMING:
        dam = rng_mm.number_range(1, weapon_level // 4 + 1)
        # ROM src/fight.c:655 act("$p sears your flesh.", victim, wield, NULL,
        # TO_CHAR) — the weapon ($p) leads, so ROM act_new caps the first char
        # (src/comm.c:2376, FIGHT-031).
        _push_message(victim, capitalize_act_line(f"{weapon_name} sears your flesh."))
        if room is not None:
            # mirroring ROM src/fight.c:654 — `act("$n is burned by
            # $p.", victim, wield, NULL, TO_ROOM)`. PERS on $n
            # per-listener (FIGHT-011).
            _broadcast_pos_change(
                victim,
                "{name} is burned by {weapon}.",
                weapon=weapon_name,
            )
        fire_effect(victim, weapon_level // 2, dam, SpellTarget.CHAR)
        apply_damage(attacker, victim, dam, DamageType.FIRE, show=False)
        messages.append(capitalize_act_line(f"{weapon_name} sears your flesh."))

    # WEAPON_FROST - ROM src/fight.c L661-670
    if weapon_flags & WEAPON_FROST:
        dam = rng_mm.number_range(1, weapon_level // 6 + 2)
        # ROM src/fight.c:664 act("The cold touch of $p surrounds you with ice.",
        # victim, wield, NULL, TO_CHAR) — $p is the weapon name. FIGHT-033.
        _push_message(victim, capitalize_act_line(f"The cold touch of {weapon_name} surrounds you with ice."))
        if room is not None:
            # mirroring ROM src/fight.c:663 — `act("$p freezes $n.",
            # victim, wield, NULL, TO_ROOM)`. ROM places the weapon
            # ($p) first and the victim ($n) as the object of
            # "freezes" — Python previously emitted "X is frozen by Y"
            # which inverts the subject/object (FIGHT-012). Fix both
            # the PERS gap and the wording in one pass.
            _broadcast_pos_change(
                victim,
                "{weapon} freezes {name}.",
                weapon=weapon_name,
            )
        cold_effect(victim, weapon_level // 2, dam, SpellTarget.CHAR)
        apply_damage(attacker, victim, dam, DamageType.COLD, show=False)
        messages.append(capitalize_act_line(f"The cold touch of {weapon_name} surrounds you with ice."))

    # WEAPON_SHOCKING - ROM src/fight.c L672-681
    if weapon_flags & WEAPON_SHOCKING:
        dam = rng_mm.number_range(1, weapon_level // 5 + 2)
        # ROM src/fight.c:675 act("You are shocked by $p.", victim, wield, NULL,
        # TO_CHAR) — $p is the weapon name. FIGHT-033.
        _push_message(victim, capitalize_act_line(f"You are shocked by {weapon_name}."))
        if room is not None:
            # mirroring ROM src/fight.c:673-674 — `act("$n is struck
            # by lightning from $p.", victim, wield, NULL, TO_ROOM)`.
            # PERS on $n per-listener (FIGHT-013).
            _broadcast_pos_change(
                victim,
                "{name} is struck by lightning from {weapon}.",
                weapon=weapon_name,
            )
        shock_effect(victim, weapon_level // 2, dam, SpellTarget.CHAR)
        apply_damage(attacker, victim, dam, DamageType.LIGHTNING, show=False)
        messages.append(capitalize_act_line(f"You are shocked by {weapon_name}."))

    return messages
