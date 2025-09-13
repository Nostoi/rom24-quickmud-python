from __future__ import annotations
from typing import Any, Callable
from mud.utils import rng_mm

spec_fun_registry: dict[str, Callable[..., Any]] = {}

def register_spec_fun(name: str, func: Callable[..., Any]) -> None:
    """Register *func* under *name*, storing key in lowercase."""
    spec_fun_registry[name.lower()] = func

def get_spec_fun(name: str) -> Callable[..., Any] | None:
    """Return a spec_fun for *name* using case-insensitive lookup."""
    return spec_fun_registry.get(name.lower())


def run_npc_specs() -> None:
    """Invoke registered spec_funs for NPCs in all rooms.

    For each NPC (MobInstance) present in any room, if its prototype has a
    non-empty ``spec_fun`` name and a function is registered under that name,
    call it with the mob instance.
    """
    from mud.registry import room_registry

    for room in list(room_registry.values()):
        for entity in list(getattr(room, "people", [])):
            proto = getattr(entity, "prototype", None)
            name = getattr(proto, "spec_fun", None)
            if not name:
                continue
            func = get_spec_fun(name)
            if func is None:
                continue
            try:
                func(entity)
            except Exception:
                # Spec fun failures must not break the tick loop
                continue


# --- Minimal ROM-like spec functions (rng_mm parity) ---

def spec_cast_adept(mob: Any) -> bool:
    """Simplified Adept spec that uses ROM RNG.

    ROM's `spec_cast_adept` periodically casts helpful spells on players.
    For parity of RNG usage, we roll `number_percent()` and return True when
    the roll is small. This function exists primarily to validate that the
    Mitchell–Moore RNG wiring matches ROM semantics.
    """
    roll = rng_mm.number_percent()
    # Return True on low roll to signal an action occurred (simplified).
    return roll <= 25


# Convenience registration name matching ROM conventions
register_spec_fun("spec_cast_adept", spec_cast_adept)
