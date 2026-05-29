"""Normalization + trace diffing. Both capture and replay call normalize_step()
so canonicalization never drifts between the C and Python sides."""

from __future__ import annotations

import re
from dataclasses import replace

from mud.net.ansi import strip_ansi
from tools.diff_harness.schema import CharSnap, RoomSnap, StepSnap

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _normalize_output(lines: list[str]) -> list[str]:
    """Canonicalize a step's output for cross-engine comparison.

    ROM emits ``\\n\\r`` line endings (CR *after* LF), while Python uses ``\\n``;
    the two also differ in how blank/padding lines are batched. We also strip
    colour: the Python engine emits raw ROM colour tokens (``{2``…``{x``) while
    the C shim's descriptor runs with colour off (``src/comm.c`` ``colour()``
    non-ANSI branch eats every ``{X`` pair), so its golden has none. ``strip_ansi``
    mirrors that ROM non-colour branch, making the comparison fair over plain text
    — it is a no-op on the already-stripped C side (FINDING-008 sub-issue 2, the
    colour-normalization analog of FINDING-002/005). Then strip real ANSI escapes
    and all CR, re-split on LF, trim, and drop empty lines so the comparison is
    over the sequence of non-empty text lines — the behaviorally meaningful
    content, independent of colour, newline convention, and blank spacing.
    """
    text = strip_ansi(_ANSI.sub("", "\n".join(lines))).replace("\r", "")
    return [stripped for raw in text.split("\n") if (stripped := raw.strip())]


def _normalize_char(c: CharSnap) -> CharSnap:
    return replace(
        c,
        affects=sorted(c.affects),
        affect_flags=sorted(c.affect_flags),
        inventory=list(c.inventory),  # order preserved
    )


def _normalize_room(r: RoomSnap) -> RoomSnap:
    return replace(r, people=sorted(r.people), contents=sorted(r.contents))


def normalize_step(step: StepSnap) -> StepSnap:
    return replace(
        step,
        chars=[_normalize_char(c) for c in step.chars],
        rooms=[_normalize_room(r) for r in step.rooms],
        output=_normalize_output(step.output),
    )


def diff_traces(c_trace: list[StepSnap], py_trace: list[StepSnap]) -> str | None:
    """Return a human-readable report of the FIRST divergence, or None if equal."""
    if len(c_trace) != len(py_trace):
        return f"trace length differs: C={len(c_trace)} py={len(py_trace)}"
    for c_step_raw, py_step_raw in zip(c_trace, py_trace, strict=True):
        c_step = normalize_step(c_step_raw)
        py_step = normalize_step(py_step_raw)
        if c_step == py_step:
            continue
        return _render_step_diff(c_step, py_step)
    return None


def _render_step_diff(c: StepSnap, py: StepSnap) -> str:
    prefix = f"step {c.step} (command={c.command!r})"
    if c.output != py.output:
        return f"{prefix} · output · C={c.output} py={py.output}"
    c_by_key = {ch.key: ch for ch in c.chars}
    py_by_key = {ch.key: ch for ch in py.chars}
    if set(c_by_key) != set(py_by_key):
        return f"{prefix} · chars · C keys={sorted(c_by_key)} py keys={sorted(py_by_key)}"
    for key in c_by_key:
        cc, pc = c_by_key[key], py_by_key[key]
        if cc != pc:
            for f in ("room", "position", "hp", "max_hp", "mana", "move", "level",
                      "align", "gold", "fighting", "eff_hitroll", "eff_damroll", "eff_ac",
                      "affects", "affect_flags",
                      "inventory", "equipment"):
                if getattr(cc, f) != getattr(pc, f):
                    return f"{prefix} · chars[{key}].{f} · C={getattr(cc, f)} py={getattr(pc, f)}"
    c_rooms = {r.vnum: r for r in c.rooms}
    py_rooms = {r.vnum: r for r in py.rooms}
    for vnum in c_rooms:
        if c_rooms[vnum] != py_rooms.get(vnum):
            return f"{prefix} · rooms[{vnum}] · C={c_rooms[vnum]} py={py_rooms.get(vnum)}"
    return f"{prefix} · steps differ (no field localized — inspect manually)"
