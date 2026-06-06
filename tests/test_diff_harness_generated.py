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
