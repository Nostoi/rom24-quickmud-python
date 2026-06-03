"""Hypothesis state machines for generated differential harness scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hypothesis.stateful import RuleBasedStateMachine, precondition, rule

from tools.diff_harness.compare import diff_traces
from tools.diff_harness.oracle import drive_c_oracle
from tools.diff_harness.pyreplay import drive_python_replay
from tools.diff_harness.scenario import Scenario


@dataclass
class _ObjectState:
    vnum: int
    keyword: str
    load_command: str
    wear_command: str
    room: int | None = None
    inventory: bool = False
    equipped: bool = False


class DeterministicNoRngDiffMachine(RuleBasedStateMachine):
    """Generate legal no-RNG command sequences and diff C against Python."""

    def __init__(self, *, binary: Path):
        super().__init__()
        self.binary = binary
        self.steps: list[str] = []
        self.current_room = 3001
        self.small_sword = _ObjectState(
            vnum=3021,
            keyword="sword",
            load_command="__oload=3021",
            wear_command="wield sword",
        )
        self.scale_jacket = _ObjectState(
            vnum=3045,
            keyword="jacket",
            load_command="__oload=3045",
            wear_command="wear jacket",
        )

    @rule()
    def look(self) -> None:
        self.steps.append("look")

    @rule()
    def inventory(self) -> None:
        self.steps.append("inventory")

    @precondition(lambda self: self.current_room == 3001)
    @rule()
    def north(self) -> None:
        self.steps.append("north")
        self.current_room = 3054

    @precondition(lambda self: self.current_room == 3054)
    @rule()
    def south(self) -> None:
        self.steps.append("south")
        self.current_room = 3001

    @precondition(lambda self: not self._object_exists(self.small_sword))
    @rule()
    def load_small_sword(self) -> None:
        self._load_object(self.small_sword)

    @precondition(lambda self: not self._object_exists(self.scale_jacket))
    @rule()
    def load_scale_jacket(self) -> None:
        self._load_object(self.scale_jacket)

    @precondition(lambda self: self.small_sword.room == self.current_room)
    @rule()
    def get_small_sword(self) -> None:
        self._get_object(self.small_sword)

    @precondition(lambda self: self.scale_jacket.room == self.current_room)
    @rule()
    def get_scale_jacket(self) -> None:
        self._get_object(self.scale_jacket)

    @precondition(lambda self: self.small_sword.inventory and not self.small_sword.equipped)
    @rule()
    def wield_small_sword(self) -> None:
        self._wear_object(self.small_sword)

    @precondition(lambda self: self.scale_jacket.inventory and not self.scale_jacket.equipped)
    @rule()
    def wear_scale_jacket(self) -> None:
        self._wear_object(self.scale_jacket)

    @precondition(lambda self: self.small_sword.equipped)
    @rule()
    def remove_small_sword(self) -> None:
        self._remove_object(self.small_sword)

    @precondition(lambda self: self.scale_jacket.equipped)
    @rule()
    def remove_scale_jacket(self) -> None:
        self._remove_object(self.scale_jacket)

    @precondition(lambda self: self.small_sword.inventory and not self.small_sword.equipped)
    @rule()
    def drop_small_sword(self) -> None:
        self._drop_object(self.small_sword)

    @precondition(lambda self: self.scale_jacket.inventory and not self.scale_jacket.equipped)
    @rule()
    def drop_scale_jacket(self) -> None:
        self._drop_object(self.scale_jacket)

    @staticmethod
    def _object_exists(obj: _ObjectState) -> bool:
        return obj.room is not None or obj.inventory or obj.equipped

    def _load_object(self, obj: _ObjectState) -> None:
        self.steps.append(obj.load_command)
        obj.room = self.current_room

    def _get_object(self, obj: _ObjectState) -> None:
        self.steps.append(f"get {obj.keyword}")
        obj.room = None
        obj.inventory = True

    def _wear_object(self, obj: _ObjectState) -> None:
        self.steps.append(obj.wear_command)
        obj.inventory = False
        obj.equipped = True

    def _remove_object(self, obj: _ObjectState) -> None:
        self.steps.append(f"remove {obj.keyword}")
        obj.inventory = True
        obj.equipped = False

    def _drop_object(self, obj: _ObjectState) -> None:
        self.steps.append(f"drop {obj.keyword}")
        obj.inventory = False
        obj.room = self.current_room

    def teardown(self) -> None:
        if not self.steps:
            return
        sc = Scenario(
            name="generated_no_rng",
            seed=1234,
            start_room=3001,
            char_name="Tester",
            char_level=5,
            watch_chars=["Tester"],
            watch_rooms=[3001, 3054],
            steps=list(self.steps),
        )
        report = diff_traces(drive_c_oracle(sc, self.binary), drive_python_replay(sc))
        assert report is None, f"generated sequence diverged: {self.steps!r}\n{report}"
