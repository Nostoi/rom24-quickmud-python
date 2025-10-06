from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from random import Random
from typing import TYPE_CHECKING, Any

from mud.advancement import gain_exp
from mud.math.c_compat import c_div
from mud.models import Skill, SkillJson
from mud.models.constants import AffectFlag
from mud.models.json_io import dataclass_from_dict
from mud.skills.metadata import ROM_SKILL_METADATA
from mud.utils import rng_mm

if TYPE_CHECKING:
    from mud.models.character import Character


@dataclass
class SkillUseResult:
    """Outcome container for `SkillRegistry.use` invocations."""

    success: bool
    message: str = ""
    payload: Any | None = None
    cooldown: int = 0
    lag: int = 0

    def __bool__(self) -> bool:  # pragma: no cover - convenience shim
        return self.success


class SkillRegistry:
    """Load skill metadata from JSON and dispatch handlers."""

    def __init__(self, rng: Random | None = None) -> None:
        self.skills: dict[str, Skill] = {}
        self.handlers: dict[str, Callable] = {}
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

    def find_spell(self, character: Character | None, name: str) -> Skill | None:
        """Return the first skill matching the prefix, preferring known skills."""

        query = (name or "").strip().lower()
        if not query:
            return None

        first_match: Skill | None = None

        prefer_known = False
        class_index = 0
        level = 0
        learned_map: dict[str, object] = {}

        if character is not None and not getattr(character, "is_npc", False):
            prefer_known = True
            try:
                class_index = int(getattr(character, "ch_class", 0) or 0)
            except Exception:
                class_index = 0
            try:
                level = int(getattr(character, "level", 0) or 0)
            except Exception:
                level = 0
            raw_skills = getattr(character, "skills", {}) or {}
            if isinstance(raw_skills, dict):
                learned_map = dict(raw_skills)

        for skill in self.skills.values():
            skill_name = getattr(skill, "name", "")
            if not skill_name:
                continue
            lower_name = skill_name.lower()
            if lower_name[0:1] != query[0:1]:
                continue
            if not lower_name.startswith(query):
                continue

            if first_match is None:
                first_match = skill

            if not prefer_known:
                continue

            known_key = skill_name
            learned_value = learned_map.get(known_key)
            if learned_value is None and lower_name != known_key:
                learned_value = learned_map.get(lower_name)
            try:
                learned = int(learned_value) if learned_value is not None else None
            except (TypeError, ValueError):
                learned = None
            if learned is None or learned <= 0:
                continue

            required_level: int | None = None
            levels = getattr(skill, "levels", None)
            if isinstance(levels, (list, tuple)) and len(levels) > 0:
                try:
                    required_level = int(levels[class_index])
                except (ValueError, TypeError, IndexError):
                    required_level = None
            if required_level is not None and level < required_level:
                continue

            return skill

        return first_match

    def use(self, caster, name: str, target=None) -> SkillUseResult:
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

        learned: int | None
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

        if success:
            handler_result = self.handlers[name](caster, target)
            result = self._normalize_success_result(skill, handler_result, lag)
        else:
            failure_message = self._failure_message(skill)
            if hasattr(caster, "messages") and isinstance(caster.messages, list):
                caster.messages.append(failure_message)
            result = SkillUseResult(
                success=False,
                message=failure_message,
                payload=None,
                cooldown=skill.cooldown,
                lag=lag,
            )

        cooldowns[name] = skill.cooldown
        caster.cooldowns = cooldowns

        self._check_improve(caster, skill, name, success)
        return result

    def _normalize_success_result(
        self,
        skill: Skill,
        handler_result: object,
        lag: int,
    ) -> SkillUseResult:
        """Wrap handler returns into a `SkillUseResult` with sensible defaults."""

        if isinstance(handler_result, SkillUseResult):
            cooldown = handler_result.cooldown or skill.cooldown
            wait_state = handler_result.lag or lag
            return SkillUseResult(
                success=handler_result.success,
                message=handler_result.message,
                payload=handler_result.payload,
                cooldown=cooldown,
                lag=wait_state,
            )

        message = ""
        payload = handler_result

        if isinstance(handler_result, tuple) and len(handler_result) == 2:
            payload, possible_message = handler_result
            if isinstance(possible_message, str):
                message = possible_message
        elif isinstance(handler_result, str):
            message = handler_result

        if not message:
            message = self._default_success_message(skill)

        return SkillUseResult(
            success=True,
            message=message,
            payload=payload,
            cooldown=skill.cooldown,
            lag=lag,
        )

    def _failure_message(self, skill: Skill) -> str:
        """Return the ROM-aligned failure message for a skill or spell."""

        messages = getattr(skill, "messages", {}) or {}
        if isinstance(messages, dict):
            failure = messages.get("failure")
            if isinstance(failure, str) and failure:
                return failure

        if getattr(skill, "type", "").lower() == "spell":
            return "You lost your concentration."
        return f"You fail to {skill.name}."

    def _default_success_message(self, skill: Skill) -> str:
        """Provide a fallback success string when handlers don't emit one."""

        messages = getattr(skill, "messages", {}) or {}
        if isinstance(messages, dict):
            success = messages.get("success")
            if isinstance(success, str) and success:
                return success

        skill_type = getattr(skill, "type", "").lower()
        if skill_type == "spell":
            return f"You cast {skill.name}."
        if skill_type == "skill":
            return f"You use {skill.name}."
        return skill.name

    def _compute_skill_lag(self, caster, skill: Skill) -> int:
        """Return the ROM wait-state (pulses) for a skill, adjusted by affects."""

        base_lag = int(getattr(skill, "lag", 0) or 0)
        if base_lag <= 0:
            return 0

        flags = int(getattr(caster, "affected_by", 0) or 0)
        lag_pulses = base_lag
        if flags & AffectFlag.HASTE:
            lag_pulses = max(1, c_div(lag_pulses, 2))
        if flags & AffectFlag.SLOW:
            lag_pulses = lag_pulses * 2

        return max(1, int(lag_pulses))

    def _apply_wait_state(self, caster, lag: int) -> None:
        """Apply WAIT_STATE semantics mirroring ROM's UMAX logic."""

        if lag <= 0 or not hasattr(caster, "wait"):
            return
        current = int(getattr(caster, "wait", 0) or 0)
        caster.wait = max(current, lag)

    def _check_improve(
        self,
        caster,
        skill: Skill,
        name: str,
        success: bool,
        multiplier: int = 1,
    ) -> None:
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
                caster.messages.append(f"You learn from your mistakes, and your {skill.name} skill improves.")
                gain_exp(caster, 2 * rating)

    def tick(self, character) -> None:
        """Reduce active cooldowns on a character by one tick."""
        cooldowns = getattr(character, "cooldowns", {})
        for key in list(cooldowns):
            cooldowns[key] -= 1
            if cooldowns[key] <= 0:
                del cooldowns[key]
        character.cooldowns = cooldowns

        # Wait-state recovery occurs in the violence pulse cadence. Skill ticks
        # only manage cooldown bookkeeping so they mirror ROM's update loop.

    def check_improve(self, caster, name: str, success: bool, multiplier: int = 1) -> None:
        """Public entry mirroring ROM check_improve helper."""

        skill = self.skills.get(name)
        if skill is None:
            return
        self._check_improve(caster, skill, name, success, multiplier)


skill_registry = SkillRegistry()


def load_skills(path: Path) -> None:
    skill_registry.load(path)


def check_improve(caster, name: str, success: bool, multiplier: int = 1) -> None:
    """Convenience wrapper delegating to the global skill registry."""

    skill_registry.check_improve(caster, name, success, multiplier)
