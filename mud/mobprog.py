"""Basic mob program trigger handling and interpreter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
from typing import Iterable

from .models.mob import MobIndex


class Trigger(IntFlag):
    """Bit flags describing mob program trigger types."""

    ACT = 1 << 0
    BRIBE = 1 << 1
    DEATH = 1 << 2
    ENTRY = 1 << 3
    FIGHT = 1 << 4
    GIVE = 1 << 5
    GREET = 1 << 6
    GRALL = 1 << 7
    KILL = 1 << 8
    HPCNT = 1 << 9
    RANDOM = 1 << 10
    SPEECH = 1 << 11
    EXIT = 1 << 12
    EXALL = 1 << 13
    DELAY = 1 << 14
    SURR = 1 << 15


@dataclass
class ExecutionResult:
    """Represents a single action performed by the interpreter."""

    command: str
    argument: str


def run_prog(
    mob: MobIndex, trig: Trigger, *, phrase: str | None = None
) -> list[ExecutionResult]:
    """Run mob programs matching *trig* and *phrase*.

    This very small interpreter only understands ``say`` and ``emote``
    commands and returns the actions performed for testing.
    """

    results: list[ExecutionResult] = []
    for prog in mob.mprogs:
        if prog.code is None:
            continue
        if not prog.trig_type & int(trig):
            continue
        if prog.trig_phrase and phrase is not None:
            if prog.trig_phrase.lower() not in phrase.lower():
                continue
        results.extend(_execute(prog.code))
    return results


def _execute(code: str) -> Iterable[ExecutionResult]:
    for raw_line in code.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("say "):
            yield ExecutionResult("say", line[4:].strip())
        elif line.startswith("emote "):
            yield ExecutionResult("emote", line[6:].strip())
        # other mob commands ignored for now
