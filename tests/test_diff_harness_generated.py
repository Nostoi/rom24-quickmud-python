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


def test_generated_keyed_door_cycle_matches_live_c():
    """``close`` / ``lock`` / ``unlock`` / ``pick`` / ``open`` / traverse a keyed door.

    Exercises the deterministic door command widening added to
    ``DeterministicNoRngDiffMachine``.  The stock Cityguard HQ west door starts
    open and uses the iron key (3120), so the sequence closes it, locks and
    unlocks it with the key, then locks it again, picks it with a learned 100%
    skill, opens it, and walks through/back across the door.
    """
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_keyed_door",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001, 3110, 3142],
        steps=[
            "__goto=3110",
            "__oload=3120",
            "get key",
            "close west",
            "lock west",
            "unlock west",
            "lock west",
            "__level=30",
            "__learn=pick lock",
            "__seed=1234",
            "pick west",
            "__seed=5678",
            "open west",
            "west",
            "east",
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


def test_generated_examine_object_branches_matches_live_c():
    """``examine`` across its item-type branches against the live C oracle.

    ROM ``do_examine`` (src/act_info.c) runs ``do_look <obj>`` then, for
    ITEM_CONTAINER / ITEM_DRINK_CON / ITEM_MONEY / ITEM_CORPSE_*, peeks inside
    (a ``look in <obj>``).  This pins three branches:

    - container (bag 3032)  → object description + ``A bag holds:`` / ``Nothing.``
    - drink-con (bottle 3001) → object description + fill-level line
    - weapon (sword 3021)   → default branch, object description only

    The drink-con line reproduces ROM's verbatim ``"with  a amber liquid"``
    double-space/"a amber" wording (src/act_info.c:1143 + liq_table), so it also
    locks the act-rendering for the DRINK_CON peek path.  The state-machine
    ``examine_*`` rules exercise these opportunistically; this scenario
    guarantees coverage every run (the rule preconditions fire rarely).
    """
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_examine_branches",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__oload=3032",  # bag (container)
            "__oload=3001",  # bottle beer (drink-con)
            "__oload=3021",  # small sword (weapon)
            "get bag",
            "get bottle",
            "get sword",
            "examine bag",
            "examine bottle",
            "examine sword",
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_compare_objects_matches_live_c():
    """``compare`` across its branches against the live C oracle.

    ROM ``do_compare`` (src/act_info.c) is fully deterministic.  This pins:

    - item-type mismatch (weapon vs armor) → ``You can't compare $p and $P.``
    - value comparison (small sword value (1+5)*1=6 > dagger (1+4)*1=5) →
      ``$p looks better than $P.``
    - same object (``compare sword sword`` matches obj1==obj2) →
      ``You compare $p to itself.  It looks about the same.``

    Exercises the ``$p``/``$P`` act-substitution + first-letter cap (the
    FINDING-021/022/033 output-rendering class).  The dagger (3020) and small
    sword (3021) have distinct keywords (``dagger`` / ``sword``) so the
    selectors are unambiguous.
    """
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_compare_objects",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__oload=3021",  # small sword (weapon, value 6)
            "__oload=3020",  # dagger (weapon, value 5)
            "__oload=3045",  # scale mail jacket (armor)
            "get sword",
            "get dagger",
            "get jacket",
            "compare sword jacket",  # mismatch: weapon vs armor
            "compare sword dagger",  # value: sword > dagger
            "compare sword sword",  # itself
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_wear_all_matches_live_c():
    """``wear all`` bulk-loop form against the live C oracle.

    This scenario SURFACED FINDING-034 and now LOCKS its fix (WEAR-012): ROM
    ``wear all`` (`src/act_obj.c:1712-1723`) calls ``wear_obj(ch, obj, FALSE)``
    unconditionally, lighting+holding the torch (and wielding weapons / holding
    HOLD items). Python's ``_wear_all`` previously skipped all three classes; it
    now routes every carried item through the shared ``_wear_obj(ch, obj,
    fReplace=False)`` dispatch, so it converges against C.

    ROM ``do_wear`` (src/act_obj.c:1712-1723) loops ``ch->carrying`` and calls
    ``wear_obj(ch, obj, FALSE)`` for every item with ``wear_loc == WEAR_NONE``.
    This pins that loop with two items that land in *distinct* slots — a scale
    mail jacket (3045, WEAR_BODY) and a torch (3030, WEAR_LIGHT) — so there is no
    slot contention and ``fReplace == FALSE`` never has to skip an occupied slot.
    (``wear all`` over two weapons is the dual-wield arm — a separate probe.)

    Carry list is head-insert LIFO: ``get jacket`` then ``get torch`` ⇒ carry
    ``[torch, jacket]``, so ``wear all`` holds the torch first, then wears the
    jacket; ``look`` confirms both moved to equipment.  No RNG on the wear path,
    so no ``__seed`` bracket.
    """
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_wear_all",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__oload=3045",  # scale mail jacket (WEAR_BODY)
            "__oload=3030",  # torch (WEAR_LIGHT)
            "get jacket",
            "get torch",  # carry [torch, jacket]
            "wear all",  # hold torch, wear jacket
            "look",  # equipment populated, carry empty
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_sacrifice_lifecycle_matches_live_c():
    """``sacrifice`` an object to Mota — ``do_sacrifice`` (Class-10 lifecycle).

    ROM ``do_sacrifice`` (src/act_obj.c:1765-1862) is fully deterministic — the
    reward is ``silver = UMAX(1, obj->level * 3)`` capped at ``obj->cost`` for
    non-corpses, with **no** ``number_*`` call on any branch — so no ``__seed``
    bracket is needed (verified against the C source before writing this).  The
    target must be in the room, not carried (``get_obj_list(ch, arg,
    ch->in_room->contents)``), and a successful sacrifice ``extract_obj``s it —
    the object-extraction lifecycle (divergence class 10).  This pins:

    - bare ``sacrifice`` (self / no arg) → ``Mota appreciates your offer and may
      accept it later.`` (TO_CHAR; the TO_ROOM act needs another watcher)
    - ``sacrifice <missing>``           → ``You can't find it.``
    - ``sacrifice sword`` (small sword 3021 in room) → ``Mota gives you N silver
      coins for your sacrifice.`` + ``ch->silver += N`` + object extracted
    - ``look`` confirms the room no longer holds the sword (extraction observed)
    - ``sacrifice sword`` again         → ``You can't find it.`` (already gone)

    The C oracle computes the silver reward; the test asserts only that C and
    Python agree (a divergence here would be a finding, not a golden to edit).
    """
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_sacrifice",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "sacrifice",  # self / no arg → Mota declines
            "sacrifice nothinghere",  # not found
            "__oload=3021",  # small sword into the room (sacrifice targets room)
            "sacrifice sword",  # reward + extract_obj
            "look",  # sword gone from room
            "sacrifice sword",  # not found (extracted)
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_get_all_drop_all_matches_live_c():
    """``get all`` / ``drop all`` bulk-loop forms against the live C oracle.

    ROM ``do_get`` (src/act_obj.c:233-253) and ``do_drop`` iterate the
    room-contents / inventory list and call ``get_obj`` / ``obj_from_char`` per
    item, so the bulk verbs are observable LIFO loops (the INV-039 / class-13
    head-insert contract, here exercised at the bulk-loop level rather than the
    per-item ``get <obj>`` level the existing scenarios cover):

    - ``__oload`` head-inserts into the room: load sword (3021) then dagger
      (3020) ⇒ room contents ``[dagger, sword]``.
    - ``get all`` walks that order, each ``get_obj`` head-inserting into carry ⇒
      output ``You get a dagger.`` then ``You get a sword.``; carry ``[sword,
      dagger]``.
    - ``drop all`` walks carry ``[sword, dagger]`` ⇒ ``You drop a sword.`` then
      ``You drop a dagger.``; room back to ``[dagger, sword]``.

    The interleaved ``look`` snapshots pin both list orders.  Two weapons (not
    worn) keep this the clean carry/room case — ``wear all``'s dual-wield arm is
    a separate probe.  No RNG on any get/drop path, so no ``__seed`` bracket.
    """
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_get_all_drop_all",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__oload=3021",  # small sword → room head ⇒ [sword]
            "__oload=3020",  # dagger → room head ⇒ [dagger, sword]
            "get all",  # You get a dagger. / You get a sword.
            "look",  # carry order [sword, dagger]
            "drop all",  # You drop a sword. / You drop a dagger.
            "look",  # room order [dagger, sword]
        ],
    )

    assert diff_traces(drive_c_oracle(sc, DIFFSHIM), drive_python_replay(sc)) is None


def test_generated_container_lock_cycle_matches_live_c():
    """``unlock`` / ``open`` / ``close`` / ``lock`` a keyed container — the
    ``do_open``/``do_close``/``do_lock``/``do_unlock`` OBJECT branch.

    Distinct from ``test_generated_keyed_door_cycle`` (the EXIT branch): this
    pins the ITEM_CONTAINER arm of all four handlers (src/act_move.c:388-413,
    496-516, 626-656, 761-791), which keys off ``value[1]`` CONT_* flags and
    ``value[2]`` (key vnum), where the door arm uses ``exit_info`` + ``key``.

    The desk drawer (vnum 3130) protos as ``ABCD`` = CLOSEABLE | PICKPROOF |
    CLOSED | LOCKED, so a freshly loaded one starts closed-and-locked; its key
    is the wooden key (vnum 3122).  The drawer has no ITEM_TAKE wear flag
    (``container 0 0``) so it cannot be picked up — it is referenced in the room
    via ``get_obj_here``'s room fallback.  The sequence walks the full
    deterministic branch set, every line of which act-renders the drawer's short
    desc ``the desk`` via ``$p``:

    - ``unlock`` before ``get key``      → ``You lack the key.`` (no key in carry)
    - ``open`` while still locked        → ``It's locked.``
    - ``unlock`` with key                → ``You unlock the desk.``
    - ``open``                           → ``You open the desk.``
    - ``lock`` while open                → ``It's not closed.``
    - ``close``                          → ``You close the desk.``
    - ``lock`` with key                  → ``You lock the desk.``

    No RNG is drawn on any container open/close/lock/unlock path (pick lock is
    the only door verb that rolls), so no ``__seed`` bracket is needed.
    """
    if not DIFFSHIM.exists():
        pytest.skip("src/diffshim is required for live generated differential tests")

    sc = Scenario(
        name="generated_container_lock_cycle",
        seed=1234,
        start_room=3001,
        char_name="Tester",
        char_level=5,
        watch_chars=["Tester"],
        watch_rooms=[3001],
        steps=[
            "__oload=3130",  # desk drawer (container, starts CLOSED+LOCKED)
            "__oload=3122",  # wooden key (key vnum the drawer wants)
            "unlock drawer",  # no key carried yet → "You lack the key."
            "open drawer",  # still locked → "It's locked."
            "get key",
            "unlock drawer",  # "You unlock the desk."
            "open drawer",  # "You open the desk."
            "lock drawer",  # open, not closed → "It's not closed."
            "close drawer",  # "You close the desk."
            "lock drawer",  # "You lock the desk."
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
