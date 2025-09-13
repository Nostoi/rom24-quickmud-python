from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from random import Random
from typing import Callable, Dict, Optional

from mud.models import Skill, SkillJson
from mud.utils import rng_mm
from mud.models.json_io import dataclass_from_dict


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
            handler = getattr(module, skill.function)
            self.skills[skill.name] = skill
            self.handlers[skill.name] = handler

    def get(self, name: str) -> Skill:
        return self.skills[name]

    def use(self, caster, name: str, target=None):
        """Execute a skill and handle resource costs and failure.

        Parity: If the caster has a learned percentage for this skill in
        `caster.skills[name]` (0..100), success is determined by a ROM-style
        percent roll (number_percent) against that learned value. If no
        learned value is present, fall back to `failure_rate` as before.
        """
        skill = self.get(name)
        if caster.mana < skill.mana_cost:
            raise ValueError("not enough mana")

        cooldowns = getattr(caster, "cooldowns", {})
        if cooldowns.get(name, 0) > 0:
            raise ValueError("skill on cooldown")

        caster.mana -= skill.mana_cost
        # ROM parity: prefer per-character learned% when available
        learned = None
        try:
            learned = caster.skills.get(name)  # 0..100
        except Exception:
            # Characters without a `skills` mapping should not error
            learned = None

        if learned is not None:
            # Success when roll <= learned (ROM practice mechanics)
            if rng_mm.number_percent() > int(learned):
                cooldowns[name] = skill.cooldown
                caster.cooldowns = cooldowns
                return False
        else:
            # Fallback: use failure_rate gate (legacy behavior)
            # Convert float failure_rate (0.0..1.0) to percentage threshold 0..100
            failure_threshold = int(round(skill.failure_rate * 100))
            if rng_mm.number_percent() <= failure_threshold:
                cooldowns[name] = skill.cooldown
                caster.cooldowns = cooldowns
                return False
            # Success path (roll > threshold): execute handler

        result = self.handlers[name](caster, target)
        cooldowns[name] = skill.cooldown
        caster.cooldowns = cooldowns
        return result

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
