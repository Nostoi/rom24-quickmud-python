from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from random import Random
from typing import Callable, Dict, Optional

from mud.advancement import gain_exp
from mud.math.c_compat import c_div
from mud.models import Skill, SkillJson
from mud.models.constants import AffectFlag
from mud.utils import rng_mm
from mud.models.json_io import dataclass_from_dict
from mud.skills.metadata import ROM_SKILL_METADATA


class SkillRegistry:
    """Load skill metadata from JSON and dispatch handlers."""

    def __init__(self, rng: Optional[Random] = None) -> None:
        self.skills: Dict[str, Skill] = {}
        self.handlers: Dict[str, Callable] = {}
        self.rng = rng or Random()

    def load(self, path: Path) -> None:
        """Load skill definitions from a JSON file."""
        with path.open() as fp:
            data = json.load(fp)
        module = import_module("mud.skills.handlers")
        for entry in data:
            skill_json = dataclass_from_dict(SkillJson, entry)
            skill = Skill.from_json(skill_json)
            metadata = ROM_SKILL_METADATA.get(skill.name, {})

            levels_source = entry.get("levels") or metadata.get("levels") or []
            if len(levels_source) == 4:
                skill.levels = tuple(int(v) for v in levels_source)

            ratings_source = entry.get("ratings") or metadata.get("ratings") or []
            if len(ratings_source) == 4:
                skill.ratings = tuple(int(v) for v in ratings_source)

            if "slot" in entry:
                skill.slot = int(entry["slot"])
            else:
                skill.slot = int(metadata.get("slot", skill.slot))

            if "min_mana" in entry:
                skill.min_mana = int(entry["min_mana"])
            else:
                skill.min_mana = int(metadata.get("min_mana", skill.mana_cost))

            if "beats" in entry:
                skill.beats = int(entry["beats"])
            else:
                skill.beats = int(metadata.get("beats", skill.lag))

            # Legacy callers still consult mana_cost/lag fields; mirror ROM values
            skill.mana_cost = skill.min_mana
            skill.lag = skill.beats
            handler = getattr(module, skill.function)
            self.skills[skill.name] = skill
            self.handlers[skill.name] = handler

    def get(self, name: str) -> Skill:
        return self.skills[name]

    def use(self, caster, name: str, target=None):
        """Execute a skill and handle ROM-style success, lag, and advancement."""

        skill = self.get(name)
        if int(getattr(caster, "wait", 0)) > 0:
            messages = getattr(caster, "messages", None)
            if isinstance(messages, list):
                messages.append("You are still recovering.")
            raise ValueError("still recovering")
        if caster.mana < skill.mana_cost:
            raise ValueError("not enough mana")

        cooldowns = getattr(caster, "cooldowns", {})
        if cooldowns.get(name, 0) > 0:
            raise ValueError("skill on cooldown")

        lag = self._compute_skill_lag(caster, skill)
        self._apply_wait_state(caster, lag)
        caster.mana -= skill.mana_cost

        learned: Optional[int]
        try:
            learned_val = caster.skills.get(name)
            learned = int(learned_val) if learned_val is not None else None
        except Exception:
            learned = None

        roll = rng_mm.number_percent()
        success: bool
        if learned is not None:
            success = roll <= learned
        else:
            failure_threshold = int(round(skill.failure_rate * 100))
            success = roll > failure_threshold

        result = False
        if success:
            result = self.handlers[name](caster, target)

        cooldowns[name] = skill.cooldown
        caster.cooldowns = cooldowns

        self._check_improve(caster, skill, name, success)
        return result

    def _compute_skill_lag(self, caster, skill: Skill) -> int:
        """Return the ROM wait-state (pulses) for a skill, adjusted by affects."""

        base_lag = int(getattr(skill, "lag", 0) or 0)
        if base_lag <= 0:
            return 0

        flags = int(getattr(caster, "affected_by", 0) or 0)
        lag = base_lag
        if flags & AffectFlag.HASTE:
            lag = max(1, c_div(lag, 2))
        if flags & AffectFlag.SLOW:
            lag = lag * 2
        return lag

    def _apply_wait_state(self, caster, lag: int) -> None:
        """Apply WAIT_STATE semantics mirroring ROM's UMAX logic."""

        if lag <= 0 or not hasattr(caster, "wait"):
            return
        current = int(getattr(caster, "wait", 0) or 0)
        caster.wait = max(current, lag)

    def _check_improve(self, caster, skill: Skill, name: str, success: bool) -> None:
        from mud.models.character import Character  # Local import to avoid cycle

        if not isinstance(caster, Character):
            return
        if caster.is_npc:
            return
        learned = caster.skills.get(name)
        if learned is None or learned <= 0:
            return
        adept = caster.skill_adept_cap()
        if learned >= adept:
            return
        rating = skill.rating.get(caster.ch_class, 1)
        if rating <= 0:
            return

        chance = 10 * caster.get_int_learn_rate()
        multiplier = 1
        chance //= max(1, multiplier * rating * 4)
        chance += caster.level
        if rng_mm.number_range(1, 1000) > chance:
            return

        if success:
            improve_chance = max(5, min(95, 100 - learned))
            if rng_mm.number_percent() < improve_chance:
                caster.skills[name] = min(adept, learned + 1)
                caster.messages.append(f"You have become better at {skill.name}!")
                gain_exp(caster, 2 * rating)
        else:
            improve_chance = max(5, min(30, learned // 2))
            if rng_mm.number_percent() < improve_chance:
                increment = rng_mm.number_range(1, 3)
                caster.skills[name] = min(adept, learned + increment)
                caster.messages.append(
                    f"You learn from your mistakes, and your {skill.name} skill improves."
                )
                gain_exp(caster, 2 * rating)

    def tick(self, character) -> None:
        """Reduce active cooldowns on a character by one tick."""
        cooldowns = getattr(character, "cooldowns", {})
        for key in list(cooldowns):
            cooldowns[key] -= 1
            if cooldowns[key] <= 0:
                del cooldowns[key]
        character.cooldowns = cooldowns


skill_registry = SkillRegistry()


def load_skills(path: Path) -> None:
    skill_registry.load(path)
