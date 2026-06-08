from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import settings
from hypothesis.stateful import run_state_machine_as_test

from tools.diff_harness.compare import diff_traces
from tools.diff_harness.generated import DeterministicNoRngDiffMachine
from tools.diff_harness.oracle import drive_c_oracle
from tools.diff_harness.pyreplay import drive_python_replay
from tools.diff_harness.scenario import Scenario

REPO = Path(__file__).resolve().parents[1]
DIFFSHIM = REPO / "src" / "diffshim"


def test_generated_no_rng_sequences_match_live_c():
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    run_state_machine_as_test(
        lambda: DeterministicNoRngDiffMachine(binary=DIFFSHIM),
        settings=settings(max_examples=4, stateful_step_count=5, deadline=None),
    )


def test_generated_object_lifecycle_sequence_matches_live_c():
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_oload",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__oload=3021", "get sword", "wield sword", "remove sword", "drop sword"],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_container_round_trip_matches_live_c():
    """put/get-from-container round trip against the live C oracle.

    Surfaced FINDING-017: ROM ``obj_to_char`` head-inserts, so after
    ``get bag; get sword`` the carry list is LIFO ([sword, bag]); the Python
    port appended, diverging at the ``get sword`` step. Fixed in
    ``Character.add_object``. This deterministic sequence also exercises the
    new ``do_put`` / get-from-container command paths.
    """
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_container",
        seed=777,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__oload=3032",  # a bag (open container, per-item cap 50)
            "__oload=3021",  # a small sword (weight 30 — fits the bag)
            "get bag",
            "get sword",
            "put sword bag",
            "get sword bag",
            "drop bag",
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_room_drop_order_matches_live_c():
    """Room contents list LIFO order (INV-039, FINDING-018).

    ROM ``obj_to_room`` head-inserts, so dropping sword then bag leaves the room
    contents [bag, sword] and ``look`` lists the bag first. The Python port
    appended to ``room.contents``, listing the sword first; fixed in
    ``Room.add_object``.
    """
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_room_drop_order",
        seed=5,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__oload=3032", "__oload=3021", "get bag", "get sword", "drop sword", "drop bag", "look"],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_container_contents_order_matches_live_c():
    """Container contents list LIFO order (INV-039, FINDING-019).

    ROM ``obj_to_obj`` head-inserts, so putting sword then ring into the bag
    stores [ring, sword]; ``get all bag`` then pulls them in that order. The
    Python port appended to ``contained_items``; fixed in
    ``obj_manipulation._obj_to_obj``. (The watch is the resulting inventory, not
    ``look in bag``, which independently trips the FINDING-021 header-cap bug.)
    """
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_container_contents_order",
        seed=5,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__oload=3032",  # bag
            "__oload=3021",  # small sword (weight 30)
            "__oload=3043",  # ring of protection (weight 10 — also fits)
            "get bag",
            "get sword",
            "get ring",
            "put sword bag",
            "put ring bag",
            "get all bag",
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_light_hold_cycle_matches_live_c():
    """``hold`` / ``remove`` a light source (torch 3030) against the live C oracle.

    Exercises the ``do_hold`` and ``remove`` command paths for a non-weapon,
    non-body-armor wear slot (HOLD), which has not been exercised by the
    generated state machine before (only wield/wear)."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_light_hold",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__oload=3030", "get torch", "hold torch", "remove torch", "drop torch"],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_eat_food_matches_live_c():
    """``eat`` a food object (bread 3011) against the live C oracle.

    Exercises the ``do_eat`` path, which consumes the object (destroys it).
    Bread is ITEM_FOOD (item_type=19), weight 10, cost 9."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_eat_food",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__oload=3011", "get bread", "eat bread"],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_mob_give_matches_live_c():
    """``__mload`` a mob + ``give`` objects/gold/silver against the live C oracle.

    Exercises the ``do_give`` path: object transfer (sword → mob inventory),
    gold transfer, and silver transfer. Watch includes the mob to verify its
    gold/silver purse changes. ``__seed`` is re-applied before ``__mload`` so
    both sides get identical mob hp/silver from the Mitchell-Moore RNG
    (world-init RNG draws differ between C and Python, so the seed must be
    re-normalized before the mob spawn)."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_mob_give",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester", "drunk"],
        watch_rooms=[3001],
        steps=[
            "__oload=3021",
            "get sword",
            "__silver=200",
            "__gold=10",
            "inventory",
            "__seed=1234",
            "__mload=3064",
            "__seed=1234",
            "inventory",
            "give sword drunk",
            "inventory",
            "give 2 gold drunk",
            "inventory",
            "give 25 silver drunk",
            "inventory",
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_drink_container_matches_live_c():
    """``drink`` a drink container (bottle beer 3001) against the live C oracle.

    Exercises the ``do_drink`` path for ITEM_DRINK_CON objects. The bottle beer
    has 16 sips of beer (ssize=12 per sip). The test character starts at
    condition[FULL]=48 (>45), so do_drink blocks with a fullness guard message —
    both C and Python should agree on the blocked output. Exercising the actual
    drinking logic (sip decrement, condition gains) would require lowering FULL
    in both drivers (C shim's make_test_char and Python's pyreplay)."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_drink",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["__oload=3001", "get bottle", "drink bottle"],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_position_transitions_matches_live_c():
    """``rest`` → ``sleep`` → ``wake`` position transitions against the
    live C oracle.

    Exercises the deterministic position commands (STANDING → RESTING →
    SLEEPING → STANDING) with no RNG involvement. The ``wake`` command with no
    arguments calls ``do_stand``, so the final transition is SLEEPING →
    STANDING."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_position",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=["rest", "sleep", "wake"],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_pour_out_matches_live_c():
    """``pour <container> out`` empties a drink container against the live C oracle.

    Exercises the ``do_pour`` / ``do_empty`` path for the bottle beer (vnum 3001,
    16 sips of beer). Pouring out sets value[1]=0 (emptied) and value[3]=0
    (cleared poison flag). Both operations are deterministic."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_pour_out",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001, 3005],
        steps=["__oload=3001", "get bottle", "pour bottle out"],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_fill_from_fountain_matches_live_c():
    """``fill <container>`` from a fountain against the live C oracle.

    Exercises the ``do_fill`` path: pour out the beer → move south to room 3005
    (The Sanctuary, which has a fountain reset; exit D2 from 3001) → load
    fountain vnum 3135 explicitly → fill the bottle with water. ROM fill always
    fills to max (16 sips). The container must be empty first because ROM fill
    refuses to mix different liquids."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_fill",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001, 3005],
        steps=[
            "__oload=3001",
            "get bottle",
            "pour bottle out",
            "south",
            "__oload=3135",
            "fill bottle",
            "north",
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_pour_between_containers_matches_live_c():
    """``pour <source> <target>`` between two drink containers against the live C oracle.

    Exercises the ``do_pour`` transfer path: pour beer from a bottle (vnum 3001,
    16 sips of beer) into an empty coffee cup (vnum 3101, capacity 6, keywords
    ``coffee cup``). The cup is poured out first (emptied), so the liquid-type
    guard (ROM ``do_pour`` line 1113 ``in->value[2] != out->value[2]``) is
    skipped (target is empty → ``in->value[1] == 0``). ROM transfers
    min(source sips, target capacity - target current) = min(16, 6) = 6 sips
    and copies the liquid type from source to target."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_pour_between",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__oload=3001",
            "get bottle",
            "__oload=3101",
            "get cup",
            "pour cup out",
            "pour bottle cup",
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_shop_sell_matches_live_c():
    """``sell`` a weapon to a shopkeeper against the live C oracle.

    Exercises the ``do_sell`` path: load weaponsmith (vnum 3003, profit_sell=40),
    load sword (vnum 3021, cost=250), sell sword for 100 silver (250*40/100=100).
    Verifies the player's silver increases by 100 and the sword leaves inventory.
    ``__seed`` brackets isolate mob-creation RNG (hp dice + wealth rolls) and
    sell RNG (number_percent unconditional per ROM act_obj.c:2925, plus
    number_range(50,100) for item timer per act_obj.c:2956) so both sides enter
    the sell from an identical stream."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_shop_sell",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester", "weaponsmith"],
        watch_rooms=[3001],
        steps=[
            "__silver=200",
            "__gold=10",
            "__hour=12",
            "__oload=3021",
            "get sword",
            "__seed=4321",
            "__mload=3003",
            "__seed=4321",
            "__seed=5678",
            "sell sword",
            "__seed=5678",
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_shop_buy_matches_live_c():
    """``buy`` a weapon from a shopkeeper against the live C oracle.

    Exercises the ``do_buy`` path: load weaponsmith (vnum 3003, profit_buy=120),
    stock keeper with sword (vnum 3021, cost=250) via ``__mob_carry=3021``,
    buy sword for 300 silver (c_div(250*120,100)=300).  Verifies the player's
    silver decreases by 300, the sword enters player inventory, the keeper's
    gold increases by 3 (incremental credit: 300//100=3 gold, 300%100=0 silver).
    ``__seed`` brackets isolate mob-creation RNG and do_buy's unconditional
    number_percent() call (ROM src/act_obj.c:2724) so both sides enter from an
    identical stream."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_shop_buy",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester", "weaponsmith"],
        watch_rooms=[3001],
        steps=[
            "__silver=300",
            "__gold=10",
            "__hour=12",
            "__seed=4321",
            "__mload=3003",
            "__seed=4321",
            "__mob_carry=3021",
            "__seed=5678",
            "buy sword",
            "__seed=5678",
            "inventory",
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_pour_into_held_container_matches_live_c():
    """``pour <source> <character>`` into a mob's held drink container.

    Exercises the vch branch of ROM ``do_pour`` (src/act_obj.c:1146-1157):
    player pours beer from their bottle into a coffee cup the drunk mob holds.
    ``__mob_hold=3101`` spawns an empty cup and equips it to the first NPC's
    HOLD slot, so the do_pour liquid-type guard passes."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_pour_into_held",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester", "drunk"],
        watch_rooms=[3001],
        steps=[
            "__oload=3001",
            "get bottle",
            "__seed=1234",
            "__mload=3064",
            "__seed=1234",
            "__mob_hold=3101",
            "pour bottle drunk",
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_shop_sell_keeper_broke_matches_live_c():
    """``sell`` to a keeper with zero treasury — exercises the wealth-check early exit.

    ROM ``do_sell`` (src/act_obj.c:2916-2921) returns early with keeper voice
    ``"I'm afraid I don't have enough wealth to buy $p."`` when
    ``price > (keeper->silver + 100 * keeper->gold)``.  ``__mob_gold=0`` and
    ``__mob_silver=0`` zero the first NPC's treasury after spawning so the guard
    fires regardless of the mob's rolled wealth.  No haggle ``number_percent()``
    call occurs on this path, so no ``__seed`` bracket is needed around the sell
    command itself."""
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_shop_sell_keeper_broke",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester", "weaponsmith"],
        watch_rooms=[3001],
        steps=[
            "__silver=200",
            "__gold=10",
            "__hour=12",
            "__oload=3021",
            "get sword",
            "__seed=4321",
            "__mload=3003",
            "__seed=4321",
            "__mob_gold=0",
            "__mob_silver=0",
            "sell sword",
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None
