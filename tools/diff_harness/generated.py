"""Hypothesis state machines for generated differential harness scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hypothesis.stateful import RuleBasedStateMachine, precondition, rule

from mud.models.constants import Position
from tools.diff_harness.compare import diff_traces
from tools.diff_harness.oracle import drive_c_oracle
from tools.diff_harness.pyreplay import drive_python_replay
from tools.diff_harness.scenario import Scenario


@dataclass
class _ObjectState:
    vnum: int
    keyword: str
    load_command: str
    wear_command: str | None = None
    hold_command: str | None = None
    eat_command: str | None = None
    drink_command: str | None = None
    room: int | None = None
    inventory: bool = False
    equipped: bool = False
    in_container: bool = False
    consumed: bool = False
    drank: bool = False
    poured_out: bool = False


@dataclass
class _MobState:
    vnum: int
    keyword: str
    room: int | None = None
    gold: int = 0
    silver: int = 0


class DeterministicNoRngDiffMachine(RuleBasedStateMachine):
    """Generate legal no-RNG command sequences and diff C against Python."""

    def __init__(self, *, binary: Path):
        super().__init__()
        self.binary = binary
        self.steps: list[str] = []
        self.current_room = 3001
        self.current_position = Position.STANDING
        self.player_gold = 10
        self.player_silver = 200
        self._fountain_room: int | None = None
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
        self.torch = _ObjectState(
            vnum=3030,
            keyword="torch",
            load_command="__oload=3030",
            hold_command="hold torch",
        )
        self.bread = _ObjectState(
            vnum=3011,
            keyword="bread",
            load_command="__oload=3011",
            eat_command="eat bread",
        )
        self.bag = _ObjectState(
            vnum=3032,
            keyword="bag",
            load_command="__oload=3032",
        )
        self.drunk = _MobState(vnum=3064, keyword="drunk")
        self._drunk_has_empty_cup: bool = False
        self.weaponsmith = _MobState(vnum=3003, keyword="weaponsmith")
        self.bottle_beer = _ObjectState(
            vnum=3001,
            keyword="bottle",
            load_command="__oload=3001",
            drink_command="drink bottle",
        )
        self.coffee_cup = _ObjectState(
            vnum=3101,
            keyword="cup",
            load_command="__oload=3101",
        )
        # affect-expiration state: track whether armor has been cast so the
        # rule fires at most once per run (armor is not re-castable while active).
        self.learned_armor: bool = False
        # cap __char_update calls well below ROM's idle-to-limbo threshold (12)
        # so the test char is never teleported out of the watch room.
        self.char_update_count: int = 0

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

    # FINDING-020 (CLOSED, 2.13.6): ROM keeps equipped objects in `ch->carrying`
    # (only `wear_loc` changes), so a removed item keeps its original carry-list
    # position. The Python port now stamps a monotonic acquisition seq at every
    # `add_object` and re-inserts a removed object at the position descending-
    # acquisition order dictates (mud/commands/obj_manipulation.py:_remove_obj),
    # reproducing ROM's preserved order even with other objects carried. The
    # earlier `_no_other_carried()` gate is therefore removed so the machine
    # exercises the formerly-divergent remove-with-other-carried path against the
    # C oracle.
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

    @precondition(lambda self: not self._object_exists(self.bag))
    @rule()
    def load_bag(self) -> None:
        self._load_object(self.bag)

    @precondition(lambda self: self.bag.room == self.current_room)
    @rule()
    def get_bag(self) -> None:
        self._get_object(self.bag)

    # The bag is only dropped while empty, keeping the generated model's view of
    # the sword's location unambiguous (a dropped bag with the sword inside would
    # hide the sword from both the room.contents and inventory snapshot fields).
    @precondition(lambda self: self.bag.inventory and not self.small_sword.in_container)
    @rule()
    def drop_bag(self) -> None:
        self._drop_object(self.bag)

    @precondition(lambda self: self.bag.inventory and self.small_sword.inventory and not self.small_sword.equipped)
    @rule()
    def put_small_sword_in_bag(self) -> None:
        self.steps.append(f"put {self.small_sword.keyword} {self.bag.keyword}")
        self.small_sword.inventory = False
        self.small_sword.in_container = True

    @precondition(lambda self: self.bag.inventory and self.small_sword.in_container)
    @rule()
    def get_small_sword_from_bag(self) -> None:
        self.steps.append(f"get {self.small_sword.keyword} {self.bag.keyword}")
        self.small_sword.in_container = False
        self.small_sword.inventory = True

    @precondition(lambda self: not self._object_exists(self.torch))
    @rule()
    def load_torch(self) -> None:
        self._load_object(self.torch)

    @precondition(lambda self: self.torch.room == self.current_room)
    @rule()
    def get_torch(self) -> None:
        self._get_object(self.torch)

    @precondition(lambda self: self.torch.inventory and not self.torch.equipped)
    @rule()
    def hold_torch(self) -> None:
        self.steps.append("hold torch")
        self.torch.inventory = False
        self.torch.equipped = True

    @precondition(lambda self: self.torch.equipped)
    @rule()
    def remove_torch(self) -> None:
        self.steps.append("remove torch")
        self.torch.inventory = True
        self.torch.equipped = False

    @precondition(lambda self: self.torch.inventory and not self.torch.equipped)
    @rule()
    def drop_torch(self) -> None:
        self._drop_object(self.torch)

    @precondition(lambda self: not self._object_exists(self.bread))
    @rule()
    def load_bread(self) -> None:
        self._load_object(self.bread)

    @precondition(lambda self: self.bread.room == self.current_room)
    @rule()
    def get_bread(self) -> None:
        self._get_object(self.bread)

    @precondition(lambda self: self.bread.inventory and not self.bread.equipped and not self.bread.consumed)
    @rule()
    def eat_bread(self) -> None:
        self.steps.append("eat bread")
        self.bread.inventory = False
        self.bread.consumed = True

    # ── drink rules ────────────────────────────────────────────────

    @precondition(lambda self: not self._object_exists(self.bottle_beer))
    @rule()
    def load_bottle_beer(self) -> None:
        self._load_object(self.bottle_beer)

    @precondition(lambda self: self.bottle_beer.room == self.current_room)
    @rule()
    def get_bottle_beer(self) -> None:
        self._get_object(self.bottle_beer)

    # do_drink blocks mortals if condition[FULL] > 45. Lower FULL to 0 before
    # the drink so the actual drinking logic is exercised (sip decrement,
    # condition gains, liquid effects). Both C and Python drivers handle the
    # __cond_full= meta-command.
    @precondition(lambda self: self.bottle_beer.inventory and not self.bottle_beer.drank)
    @rule()
    def drink_bottle_beer(self) -> None:
        self.steps.append("__cond_full=0")
        self.steps.append("drink bottle")
        self.bottle_beer.drank = True

    # ── position transition rules ──────────────────────────────────
    # Source: src/act_move.c do_sit/do_stand/do_rest/do_sleep/do_wake.
    # do_sit:   SLEEPING→error; RESTING/STANDING→SITTING; SITTING→no-op
    # do_rest:  SLEEPING→error; SITTING/STANDING→RESTING; RESTING→no-op
    # do_sleep: SLEEPING→no-op; RESTING/SITTING/STANDING→SLEEPING
    # do_stand: SLEEPING/RESTING/SITTING→STANDING
    # do_wake:  calls do_stand → STANDING

    @precondition(lambda self: self.current_position in (Position.STANDING, Position.RESTING))
    @rule()
    def sit(self) -> None:
        self.steps.append("sit")
        self.current_position = Position.SITTING

    @precondition(lambda self: self.current_position in (Position.STANDING, Position.SITTING))
    @rule()
    def rest(self) -> None:
        self.steps.append("rest")
        self.current_position = Position.RESTING

    @precondition(lambda self: self.current_position in (Position.RESTING, Position.SITTING, Position.STANDING))
    @rule()
    def sleep(self) -> None:
        self.steps.append("sleep")
        self.current_position = Position.SLEEPING

    @precondition(lambda self: self.current_position == Position.SLEEPING)
    @rule()
    def wake(self) -> None:
        self.steps.append("wake")
        self.current_position = Position.STANDING

    @precondition(lambda self: self.current_position in (Position.RESTING, Position.SITTING))
    @rule()
    def stand(self) -> None:
        self.steps.append("stand")
        self.current_position = Position.STANDING

    # ── fill / pour rules ─────────────────────────────────────────

    # Movement between temple (3001) and sanctuary (3005) — room 3005 has a
    # fountain (vnum 3135) for fill/pour scenarios. The exit from 3001 to 3005
    # is south (D2 in the area file), not down.
    @precondition(lambda self: self.current_room == 3001 and self.current_position == Position.STANDING)
    @rule()
    def south_to_sanctuary(self) -> None:
        self.steps.append("south")
        self.current_room = 3005

    @precondition(lambda self: self.current_room == 3005 and self.current_position == Position.STANDING)
    @rule()
    def north_to_temple(self) -> None:
        self.steps.append("north")
        self.current_room = 3001

    # Pour out the bottle beer (empties container + clears poison flag).
    @precondition(
        lambda self: self.bottle_beer.inventory and not self.bottle_beer.poured_out and not self.bottle_beer.drank
    )
    @rule()
    def pour_out_bottle(self) -> None:
        self.steps.append("pour bottle out")
        self.bottle_beer.poured_out = True

    # Spawn a fountain (vnum 3135) in the current room so do_fill can find it.
    @precondition(lambda self: self._fountain_room is None and self.current_room == 3005)
    @rule()
    def spawn_fountain(self) -> None:
        self.steps.append("__oload=3135")
        self._fountain_room = self.current_room

    # Fill the bottle from the fountain. Container must be empty (poured out)
    # because ROM fill refuses to mix different liquids.
    @precondition(
        lambda self: self.current_room == 3005
        and self.bottle_beer.poured_out
        and self.bottle_beer.inventory
        and self._fountain_room == self.current_room
    )
    @rule()
    def fill_bottle(self) -> None:
        self.steps.append("fill bottle")
        self.bottle_beer.poured_out = False
        self.bottle_beer.drank = False

    # ── pour-between-containers rules ──────────────────────────────

    @precondition(lambda self: not self._object_exists(self.coffee_cup))
    @rule()
    def load_coffee_cup(self) -> None:
        self._load_object(self.coffee_cup)

    @precondition(lambda self: self.coffee_cup.room == self.current_room)
    @rule()
    def get_coffee_cup(self) -> None:
        self._get_object(self.coffee_cup)

    @precondition(lambda self: self.coffee_cup.inventory and not self.coffee_cup.poured_out)
    @rule()
    def pour_out_coffee_cup(self) -> None:
        self.steps.append("pour cup out")
        self.coffee_cup.poured_out = True

    @precondition(
        lambda self: self.bottle_beer.inventory
        and not self.bottle_beer.poured_out
        and not self.bottle_beer.drank
        and self.coffee_cup.inventory
        and self.coffee_cup.poured_out
    )
    @rule()
    def pour_bottle_into_cup(self) -> None:
        self.steps.append("pour bottle cup")
        self.coffee_cup.poured_out = False

    # ── mob rules ────────────────────────────────────────────────

    @precondition(lambda self: self.drunk.room is None)
    @rule()
    def load_drunk(self) -> None:
        self.steps.append("__seed=1234")
        self.steps.append("__mload=3064")
        self.steps.append("__seed=1234")
        self.drunk.room = self.current_room

    # ── shop rules ────────────────────────────────────────────────
    # Midgaard weaponsmith (vnum 3003) accepts weapons; profit_sell=40.
    # Sword 3021 (cost=250) → sell price = 250*40/100 = 100 silver.
    # __seed= brackets isolate mob-creation and sell RNG from the rest of
    # the stream (create_mobile rolls hp dice + wealth; do_sell calls
    # number_percent unconditionally + number_range(50,100) for item timer).
    # Source: src/act_obj.c:2531 do_buy, src/act_obj.c:2875 do_sell.

    @precondition(lambda self: self.weaponsmith.room is None)
    @rule()
    def load_weaponsmith(self) -> None:
        # __hour=12 is required — the diffshim never sets current_time, so
        # time_info.hour = ((0 - 650336715) / 60) % 24 which is negative in C
        # (≈ -17), tripping ROM's open_hour guard (time_info.hour < pShop->open_hour)
        # even for shops with open_hour=0.  Any valid hour 0-23 fixes it.
        self.steps.append("__hour=12")
        self.steps.append("__seed=4321")
        self.steps.append("__mload=3003")
        self.steps.append("__seed=4321")
        self.weaponsmith.room = self.current_room

    @precondition(
        lambda self: self.small_sword.inventory
        and not self.small_sword.equipped
        and self.weaponsmith.room == self.current_room
    )
    @rule()
    def sell_sword_to_weaponsmith(self) -> None:
        self.steps.append("__seed=5678")
        self.steps.append("sell sword")
        self.steps.append("__seed=5678")
        self.small_sword.inventory = False
        self.player_silver += 100

    @precondition(lambda self: self.drunk.room == self.current_room and not self._drunk_has_empty_cup)
    @rule()
    def give_drunk_empty_cup(self) -> None:
        self.steps.append("__mob_hold=3101")
        self._drunk_has_empty_cup = True

    @precondition(
        lambda self: self.bottle_beer.inventory
        and not self.bottle_beer.poured_out
        and not self.bottle_beer.drank
        and self._drunk_has_empty_cup
    )
    @rule()
    def pour_bottle_into_drunk_held_cup(self) -> None:
        self.steps.append("pour bottle drunk")
        self._drunk_has_empty_cup = False

    @precondition(
        lambda self: self.small_sword.inventory
        and not self.small_sword.equipped
        and self.drunk.room == self.current_room
    )
    @rule()
    def give_sword_to_drunk(self) -> None:
        self.steps.append("give sword drunk")
        self.small_sword.inventory = False

    @precondition(lambda self: self.player_gold >= 2 and self.drunk.room == self.current_room)
    @rule()
    def give_gold_to_drunk(self) -> None:
        self.steps.append("give 2 gold drunk")
        self.player_gold -= 2
        self.drunk.gold += 2

    @precondition(lambda self: self.player_silver >= 25 and self.drunk.room == self.current_room)
    @rule()
    def give_silver_to_drunk(self) -> None:
        self.steps.append("give 25 silver drunk")
        self.player_silver -= 25
        self.drunk.silver += 25

    # ── affect-expiration rules ───────────────────────────────────
    # Cast armor (duration set to 2 via __set_affect_duration=2 after cast so
    # the affect expires in 3 __char_update calls, keeping timer < 12 / limbo
    # threshold).  __seed= brackets isolate the cast's RNG consumption so the
    # char_update ticks start from a deterministic stream.
    # Source: src/magic.c:spell_armor, src/update.c:char_update affect loop.

    @precondition(lambda self: not self.learned_armor)
    @rule()
    def learn_and_cast_armor(self) -> None:
        self.steps.append("__learn=armor")
        self.steps.append("__seed=1234")
        self.steps.append("cast 'armor'")
        self.steps.append("__seed=5678")
        self.steps.append("__set_affect_duration=2")
        self.learned_armor = True

    @precondition(lambda self: self.char_update_count < 8)
    @rule()
    def char_update_tick(self) -> None:
        self.steps.append("__char_update")
        self.char_update_count += 1

    @staticmethod
    def _object_exists(obj: _ObjectState) -> bool:
        return obj.room is not None or obj.inventory or obj.equipped or obj.in_container or obj.consumed

    def _load_object(self, obj: _ObjectState) -> None:
        self.steps.append(obj.load_command)
        obj.room = self.current_room

    def _get_object(self, obj: _ObjectState) -> None:
        self.steps.append(f"get {obj.keyword}")
        obj.room = None
        obj.inventory = True

    def _wear_object(self, obj: _ObjectState) -> None:
        wear_command = obj.wear_command
        assert wear_command is not None, f"{obj.keyword} is not wearable"
        self.steps.append(wear_command)
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
        all_steps = ["__silver=200", "__gold=10", *self.steps]
        watch_chars = ["Tester"]
        if self.drunk.room is not None:
            watch_chars.append("drunk")
        if self.weaponsmith.room is not None:
            watch_chars.append("weaponsmith")
        sc = Scenario(
            name="generated_no_rng",
            seed=1234,
            start_room=3001,
            char_name="Tester",
            char_level=5,
            watch_chars=watch_chars,
            watch_rooms=[3001, 3005, 3054],
            steps=all_steps,
        )
        report = diff_traces(drive_c_oracle(sc, self.binary), drive_python_replay(sc))
        assert report is None, f"generated sequence diverged: {self.steps!r}\n{report}"
