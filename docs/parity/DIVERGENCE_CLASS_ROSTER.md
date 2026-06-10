# Divergence-Class Roster — ROM 2.4b6 → Python Completeness Lens

> **Status:** DRAFT (2026-06-02). Measurement artifact, not a status tracker to
> rot. Does **not** replace `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` (per-file) or
> `CROSS_FILE_INVARIANTS_TRACKER.md` (per-contract). It is the *completeness
> lens that sits above both*: it answers "how do we know when we're done, and
> by what method per class," which neither per-file nor per-INV granularity can.

## Why this document exists

"How many cross-file invariants are left?" has no answer — bug discovery is
open-ended, with no denominator. But the question has a *tractable
reformulation*: ROM↔Python parity risk only exists where the two engines
**diverge structurally** (sync vs async, pointers vs GC identity, array vs
dict, C-int vs Python-int, …). That set of **divergence classes** is small
(~11), rooted in concrete runtime facts, and — crucially — **each class has a
single correct verification method.** Completeness is then legible per class,
and the denominator is "number of classes," not "number of unknown bugs."

## The unifying technique (and its limits)

> For a class whose contract is *"every site must route through one canonical
> chokepoint,"* enumerate every site, flag bypasses (offenders), commit the
> scan as a test. Zero offenders = closed; committed test = **stays** closed
> (self-maintaining — a regression re-opens the guard automatically).

This is exactly what `test_rng_determinism.py`, `test_equipment_key_convention.py`,
and `test_attribute_convention.py` already do (`rglob("*.py")` → regex for the
forbidden bypass → `assert not offenders`). They are three instances of one
pattern.

**But the technique does not fit every class.** A contract that is *temporal*
(ordering, "X must render before Y clamps Z") or *domain-conditional* (signed
math: `c_div` only where an operand can be negative) has no single chokepoint to
route through. Those need a different method. So completeness is **two-layered**:

| Layer | Method | Self-maintaining? |
|-------|--------|-------------------|
| **A. Static bypass-guard** | `rglob` + forbid-pattern + `assert`, committed to CI | ✅ yes — regression re-opens it |
| **B. Human domain-read** | enumerate candidate sites, a human reads each operand domain | ❌ no — point-in-time |
| **C. Dynamic differential** | `tools/diff_harness` (C⇄Python replay) ± Hypothesis state machine | partial — re-runs in CI, but scenario-bounded |

A single tool cannot give 100%. The roster's job is to point **each class at its
correct layer** and record whether that layer has actually been run.

## The roster

Legend — **Guard**: ✅ committed CI scan · ⚠️ verified by hand, not committed ·
❌ none. **Status**: clean / open / doc-rot / unverified.

### Layer A — static bypass-guard (committable, self-maintaining)

| # | Divergence class | C↔Python divergence | Canonical chokepoint | Guard | Status | Evidence |
|---|------------------|---------------------|----------------------|-------|--------|----------|
| 1 | **RNG** | C Mitchell-Moore `number_mm` vs Python `random` | `mud.math.rng_mm.number_*` | ✅ | clean | `tests/test_rng_determinism.py` (bans `random.*` in combat/skills/spells) |
| 2 | **Equipment key** | C `obj->wear_loc == iWear` (int) vs Python dict | `int(WearLocation.X)` via `canonical_wear_slot` | ✅ | clean | `tests/test_equipment_key_convention.py` (bans string-keyed access) |
| 3 | **Attribute naming** | port-specific field names | `char.inventory` / `room.people` / `char.equipment` | ✅ | clean | `tests/test_attribute_convention.py` (bans `.carrying`/`.characters`/`.equipped`) |
| 5 | **Flag values** | C bit-shift macros vs guessable hex | `IntEnum` flag classes | ✅ | clean | `tests/test_flag_hex_convention.py` (bans `FLAGPREFIX_X = 0x…` outside the enum modules; `mud/wiznet.py`'s `WiznetFlag` body allowlisted as the canonical chokepoint). Added 2026-06-02. Locks "no flag-prefixed hex constant redefined outside the enum modules" — does **not** catch a decimal-literal bypass (`if act & 32768:`), which is indistinguishable from arithmetic. |
| 6 | **Pointer identity** | C pointer `==` vs Python object `==`/`is` | every entity runtime type is `@dataclass(eq=False)` → identity `==`/`__hash__` (ROM pointer semantics); `is` still used to document intent | ❌→C→**✅ FIXED** | **resolved (2.12.78–80)** | **Reclassified A→C 2026-06-02 (see Layer C row 12), root-fixed 2.12.78–80 — now fully closed.** A static bypass-guard is infeasible — `==`/`!=` cannot be type-discriminated by line-grep. Root cause was entity runtime dataclasses being value-eq + `instance_id`/`id` unset on spawn → distinct same-proto entities compared `==`. Fixed by `@dataclass(eq=False)` on **all five** runtime types — `Character` (PCs), `MobInstance` (mobs, highest-risk twin case), `Object`, `Room` (2.12.80), and legacy `ObjectInstance` (suite green 5361, no test relied on value-eq). `MobInstance`/`ObjectInstance` were caught by adversarial review after the first commit (sibling non-subclass dataclasses don't inherit a single class's `eq=False`). INV-031(c)/INV-006 fixed/tested specific sites; the root cause is **INV-034 (✅ ENFORCED)**. |

### Layer B — human domain-read (enumerable, not auto-verifiable)

| # | Divergence class | C↔Python divergence | Why no static guard | Status | Evidence |
|---|------------------|---------------------|---------------------|--------|----------|
| 7 | **Signed integer math** | C truncates toward 0 / `%` takes dividend sign; Python floors / `%` takes divisor sign | `c_div`/`c_mod` are needed **only where an operand can be negative** — a blanket `//` ban flags ~30 correct non-negative uses (AGENTS.md). Requires reading each operand's domain. | ongoing | `mud.math.c_compat`; cited per-site in comments. No global scan possible. |

### Layer C — dynamic differential (ordering/temporal/lifecycle — no chokepoint)

| # | Divergence class | C↔Python divergence | Method | Status | Evidence |
|---|------------------|---------------------|--------|--------|----------|
| 8 | **Membership coherence** | C linked-list `char_from/to_room` vs Python `room.people` + `character_registry` | mutators keep both sides coherent — behavioral, not bypass | enforced | INV-009/010/023 tests |
| 9 | **Ordering / temporal** | C single-threaded tick vs Python async (e.g. prompt rendering `<-15hp>` between `update_pos` and `raw_kill` clamp) | no single chokepoint — sequencing | enforced (point) | INV-002 (PROMPT-CLAMP); `tools/diff_harness` |
| 10 | **Object / affect lifecycle** | C `extract_obj`/affect expiry vs Python registry add/remove | behavioral lifecycle on `object_registry` / expiry loop | enforced | INV-014/015 tests |
| 11 | **Data-load round-trip** | C `fread_flag` letter-decode vs Python `.are`→JSON→runtime | boot world, assert flags survive end-to-end | enforced | INV-032/033; `test_inv032_room_flags_survive_load.py` |
| 12 | **Pointer identity** (reclassified from Layer A 2026-06-02) | C pointer `==` vs Python value-eq dataclass `__eq__` | behavioral — entity identity; root-fixed by making every entity runtime type an identity-eq dataclass, so `==`/`in`/`remove`/`index` now mean pointer-identity | **enforced (2.12.78–80)** | **INV-034 ✅** (`tests/test_inv034_pointer_identity_divergence.py`, now plain asserts passing under identity equality). Root cause (value-eq dataclasses + `instance_id`/`id` unset on spawn) **fixed** via `@dataclass(eq=False)` on all five runtime types (`Character`, `MobInstance`, `Object`, `Room`, legacy `ObjectInstance`), after the value-eq test-reliance sweep came up empty; suite green 5361. `MobInstance`/`ObjectInstance` caught by adversarial review after the first commit; `Room` flipped 2.12.80. INV-031(c) had fixed one site (`is_same_group`). Class 6 fully closed. |
| 4 | **Async message delivery / act-cap** | C synchronous `write_to_buffer` in tick vs Python async dispatch (double-deliver, miss, mis-cap) | behavioral — single-delivery (XOR), per-recipient masking, first-letter cap, verified by integration tests, not a lexical bypass | enforced | INV-001 (×5 `test_inv001_*.py`) / 027 / 029; ACT-CAP-001..004. **Reclassified A→C 2026-06-02:** a clean static bypass-guard is INFEASIBLE — legitimate hand-rolled XOR loops (`do_yell`) correctly use `create_task(send_to_char)`, and `.messages.append` has many legitimate sites (`Character.send_to_char`, broadcast primitives, actor-self lines), so any blanket grep false-positives. The contract is contextual → Layer C, with a Layer-B "review new delivery sites" element. |

| 13 | **Object-list head-insert (placement order)** | C `obj_to_{char,room,obj}` head-insert (LIFO list) vs Python `append` (FIFO) | behavioral — list ordering, observable via `do_inventory`/`do_look`/`look in`, numbered selectors, `get/drop all` | **chokepoints enforced (2.13.1); bypass sweep COMPLETED (2.13.3); FINDING-022 RESOLVED (2.13.4)** | **INV-039** (`test_inv013_..._head_inserts_lifo` + 3 diff-harness order tests). 15 bypass sites fixed: `game_loop._obj_to_obj` → `insert(0)`, `game_loop._obj_to_char` → routes through chokepoint, `game_loop._obj_to_room` → always `room.add_object`, `MobInstance.add_to_inventory` → `insert(0)`, `ObjectInstance.move_to_room` → `room.add_object`, `equipment._perform_remove` → `add_object`, `death._handle_corpse_item` / `make_corpse` money → `insert(0)`, scavenger (spec_funs + ai) → `add_object`/`add_to_inventory`, `mob_cmds.mpoload`/`mptransfer_obj` fallback → `insert(0)`, `imm_load`/`imm_search` → chokepoint, `shop` sell-to-keeper → chokepoint, `reset_handler` container-put → `insert(0)`, `build.cmd_redit` → `insert(0)`. **4 correct append sites left as-is** (DB reload, clone, conversion, mpjunk-rebuild are order-preserving). **FINDING-022** (`look in` contents indent) resolved by porting `show_list_to_char` to `mud/utils/act.py`; `_look_in` now uses it for correct no-indent (non-COMBINE PC) or 5-space/(N) (COMBINE/NPC) formatting. **FINDING-023** (fire_effect `room.objects` dead code, items dropped by fire never reached room) fixed in same sweep. **FINDING-020 RESOLVED (2.13.6)**: equip→remove now preserves ROM's carry-list position via an acquisition-sequence shim (`Object._carry_seq` stamped at every `add_object`; `_remove_obj` re-inserts by descending seq). C-oracle-confirmed that the position is RELATIVE to acquisition order (not a fixed index) — verified across findings/interleave/roundtrip + two-equip/re-equip/drop-mix; generated-machine remove rules un-gated. **FINDING-024 RESOLVED (2.13.7)**: DB save/load persists `Object._carry_seq` through `ObjectSave.carry_seq` and advances the runtime counter after `from_orm`, so reloaded equipped objects return to their ROM-preserved carry-list position when removed. **FINDING-025 RESOLVED (2.13.8)**: mob equipment now treats the `MobInstance.equip` inventory+`wear_loc` model as ROM-faithful; shared wield lookup scans carried objects by `wear_loc`, `MobInstance.remove_object` clears carrier/`wear_loc`, and disarm mirrors ROM's NODROP/INVENTORY carry-list branch plus NPC immediate visible-weapon reclaim branch. |

## What "done" means, per layer

- **Layer A:** every class has a committed bypass-guard and it's green. Today:
  4 of 4 *feasible* classes guarded (RNG, equipment-key, attribute-naming,
  **flag-hex** — `test_flag_hex_convention.py`, added 2026-06-02). The two other
  nominal Layer-A candidates **both reclassified to Layer C** when probed (a clean
  bypass-grep proved infeasible): async-delivery (old class 4) and
  **pointer-identity (class 6, 2026-06-02 — now INV-034)**. Flag-hex was the one
  that came back feasible: a tight prefix-anchored grep had exactly one
  legitimate hit (the `WiznetFlag` enum body), so it was allowlist-able. **Net:
  Layer A is at its feasible ceiling — every class that admits a static
  chokepoint-guard now has one; the remainder are behavioral (Layer C).**
- **Layer B:** every signed-math site has been domain-read once. Ongoing,
  inherently point-in-time; the closest to a guard is flagging *new* `//`/`%`
  in PRs for human review.
- **Layer C:** every ordering/lifecycle/load invariant has a diff_harness
  scenario or behavioral test. Mostly enforced via the INV tests; the open
  lever is **Hypothesis state-machine coverage** feeding `diff_harness` to
  widen the scenario space (the current dynamic-coverage limit).

## To-do list (falls directly out of the roster)

1. ~~Promote class 4 to a committed Layer-A guard.~~ **Resolved differently
   (2026-06-02):** the attempt found a clean static guard **infeasible** —
   `do_yell` correctly hand-rolls the `create_task(send_to_char)` XOR, and
   `.messages.append` has many legitimate sites, so any blanket grep
   false-positives. Class 4 **reclassified A→C**: enforced behaviorally by the
   INV-001/027/029 + ACT-CAP-001..004 integration tests, not a lexical guard.
   (This is the skill's Phase-1 "if it false-positives, it's not Layer A" rule
   firing as designed.)
2. ~~Fix the class-4 doc-rot.~~ **Done (2026-06-02):** INV-029's row cell
   falsely listed `do_say`/`do_tell` cousins as OPEN/uncapped; they were closed
   via ACT-CAP-003/004 (2.11.42–43, committed tests). Corrected the stale status
   and enforcement clauses to match the (already-correct) watch-list. Note the
   precise finding was an *internal contradiction* (stale row cell vs. current
   watch-list), found by re-verifying the source — not the looser "doc-rot" I
   first reported.
3. ~~**Class 5 (flag-hex) scanner.**~~ **Done (2026-06-02):** Layer-A
   feasible. A tight `FLAGPREFIX_X = 0x…` grep had exactly one legitimate hit —
   `mud/wiznet.py`'s `WiznetFlag` enum body (the canonical chokepoint, not a
   bypass) — so it was allowlist-able. Committed `tests/test_flag_hex_convention.py`.
   Resolving the four offenders to make it green: migrated live `PLR_*`
   (`player_config.py`) and `COMM_DEAF` (`remaining_rom.py`) to derive from the
   enums (correct values, no behavior change), and **deleted two dead-code
   landmine functions** (`handler.is_friend`, `handler.check_immune`,
   HANDLER-DEAD-001/002) that hardcoded *wrong* bit positions
   (`ASSIST_PLAYERS = 0x1` bit 0 vs canonical `1<<18`; `IMM_WEAPON = 0x1` bit 0
   vs `DefenseBit.WEAPON = 1<<3`). Recall validated against the past
   PARALLEL-005 (`0x0010`→ExtraFlag.EVIL) and ACT_TRAIN (`0x200`) instances.
   Limit recorded in the row: the guard does not catch decimal-literal bypasses.
4. ~~**Class 6 (pointer-identity) scanner.**~~ **Resolved A→C + filed OPEN
   (2026-06-02):** a static guard is infeasible (`==`/`!=` can't be
   type-discriminated by grep — most `==` is int/str/enum). The probe instead
   *discovered* the root cause is live: `Character`/`Object` are value-eq
   dataclasses and the spawn path leaves `instance_id`/`id` unset, so distinct
   same-proto entities compare `==` (empirically verified). Filed as **INV-034**
   (Layer C, OPEN) with a strict-xfail demonstration test; INV-031(c) was the
   recall oracle (it had already fixed one site, `is_same_group`→`is`). Root fix
   (`@dataclass(eq=False)`) deferred to a scoped session — has ~91-site blast
   radius + needs a value-eq test-reliance sweep first. An AGENTS.md ROM Parity
   Rule ("use `is`, not `==`, for entity identity") was added so new code doesn't
   re-introduce the pattern.
5. ~~**Root-fix INV-034 (scoped session).**~~ **DONE (2.12.78).** Converted all
   four entity runtime types — `Character`, `MobInstance` (mobs, highest-risk
   twin case), `Object`, legacy `ObjectInstance` — to `@dataclass(eq=False)`
   (identity `==`/`__hash__` = ROM pointer semantics). `MobInstance`/
   `ObjectInstance` were caught by adversarial review after the first
   `Character`/`Object` commit (a single class's `eq=False` doesn't propagate to
   sibling non-subclass entity dataclasses). The gating sweep
   (`grep -rn "assert .*(obj|char|victim|item).*==" tests/`) found **no** test
   relying on distinct-twin value-equality — every entity-vs-entity comparison
   was an `.attr` compare or two references to the *same* object. Full suite
   green (5361 passed; the inv034 demos flipped xfail→pass + Character/Room
   behavioral tests + a runtime-type regression guard); class 6 → ✅,
   INV-034 → ✅ ENFORCED, demo tests converted to plain assertions.
   **`Room` flipped 2.12.80** (its own RED test + gating sweep), so **class 6 is
   now fully closed** across every entity runtime type — no follow-up remains.
6. **Class 11 dynamic widening (optional).** Hypothesis `RuleBasedStateMachine`
   driving `diff_harness` to attack the scenario-enumeration limit. **Phases A/B
   complete (2026-06-03):** `tools/diff_harness/oracle.py` provides the live C
   oracle for arbitrary in-memory scenarios, `tools/diff_harness/pyreplay.py`
   provides the shared Python replay driver, and
   `tests/test_diff_harness_generated.py` runs a bounded no-RNG state machine
   over deterministic commands. **Phase C started (2026-06-03):** generated
   coverage now includes `__oload` object injection plus legal get/wield/wear/
   remove/drop lifecycle rules for a small sword and scale mail jacket. This
   immediately surfaced and closed FINDING-016 (`remove` left stale `worn_by`).
   **Phase C continued (2026-06-03):** added an open container (bag) with
   put/get-from-container rules. This surfaced **class 13** (object-list
   head-insert): FINDING-017/018/019 (`obj_to_{char,room,obj}` appended instead
   of head-inserting → INV-039, three chokepoints fixed), plus the open siblings
   FINDING-020 (`remove` re-append position) and FINDING-021 (`look in` header
   cap). **Phase C continued (2026-06-09):** added keyed-door command widening:
   harness meta-commands `__goto=<vnum>` / `__level=<n>` plus generated rules for
   Midgaard Cityguard HQ's stock west door (`close`, `lock`, `unlock`, `pick`)
   using iron key 3120 and a learned `pick lock` skill. **Phase C continued
   (2026-06-09 follow-up):** added `open west` to the same generated keyed-door
   cycle. A traversal probe (`west` into room 3142) surfaced **FINDING-031**
   (room occupant look-order drift: ROM cityguards before captain; Python captain
   before cityguards). **FINDING-031 resolved in 2.13.39:** `Room.add_mob` now
   head-inserts like ROM `char_to_room`, and the generated keyed-door cycle now
   lands `west` into Captain's Office and `east` back to Cityguard HQ against the
   live C oracle. **Portal follower probe (2.13.40):** re-reading `act_enter.c`
   versus `act_move.c` exposed ENTER-019: portal followers must not be
   pre-skipped by destination visibility, even though directional followers are;
   `_move_followers` now separates those two ROM contracts. **Mob-entry trigger
   precondition probe (2.13.41):** re-reading the same post-move trigger block
   exposed MOVE-007 / ENTER-020: NPC `TRIG_ENTRY` dispatch must be gated by
   `HAS_TRIGGER(ch, TRIG_ENTRY)` (`mprog_flags & Trigger.ENTRY`) for both
   directional and portal movement; NPCs without the bit now stay silent instead
   of calling `mp_percent_trigger`. **MEdit mobprog runtime probe (2.13.43):**
   an OLC-created `entry` mobprog now has end-to-end coverage through
   `_interpret_medit` → `spawn_mob` → directional `move_character`, proving the
   builder-set ROM trigger bit and `MobProgram` row survive into runtime
   `mp_percent_trigger` selection. **MEdit greet mobprog runtime probe
   (2.13.44):** an OLC-created `greet` mobprog now has end-to-end coverage
   through `_interpret_medit` → `spawn_mob` → PC directional `move_character`,
   proving the builder-set `TRIG_GREET` bit and `MobProgram` row survive into
   runtime `mp_greet_trigger` selection. **MEdit speech mobprog runtime probe
   (2.13.45):** an OLC-created `speech` mobprog now has end-to-end coverage
   through `_interpret_medit` → `spawn_mob` → player-facing `do_say`, proving
   the builder-set `TRIG_SPEECH` bit and `MobProgram` row survive into runtime
   speech-trigger selection with the raw spoken phrase. **MEdit act mobprog
   runtime probe (2.13.46):** an OLC-created `act` mobprog now has end-to-end
   coverage through `_interpret_medit` → `spawn_mob` → player-facing
   `do_stand`, proving the builder-set `TRIG_ACT` bit and `MobProgram` row
   survive into the ROM `act()` / `mp_act_trigger` dispatch path. **MEdit bribe
   mobprog runtime probe (2.13.47):** an OLC-created `bribe` mobprog now has
   end-to-end coverage through `_interpret_medit` → `spawn_mob` → player-facing
   money `do_give`, proving the builder-set `TRIG_BRIBE` bit and `MobProgram`
   row survive into ROM's `mp_bribe_trigger` threshold path. **MEdit give
   mobprog runtime probe (2.13.48):** an OLC-created `give` mobprog now has
   end-to-end coverage through `_interpret_medit` → `spawn_mob` → player-facing
   object `do_give`, proving the builder-set `TRIG_GIVE` bit and `MobProgram`
   row survive into ROM's `mp_give_trigger` object-dispatch path. **MEdit combat
   mobprog runtime probe (2.13.49):** OLC-created `fight` and `hpcnt` mobprogs
   now have end-to-end coverage through `_interpret_medit` → `spawn_mob` →
   `violence_tick`, with `multi_hit` / `check_assist` stubbed so the probe pins
   ROM's deterministic post-round `TRIG_FIGHT` then `TRIG_HPCNT` dispatch site
   without depending on combat RNG. **MEdit surrender mobprog runtime probe
   (2.13.50):** an OLC-created `surr` mobprog now has end-to-end coverage
   through `_interpret_medit` → `spawn_mob` → player-facing `do_surrender`,
   proving the builder-set `TRIG_SURR` bit and `MobProgram` row survive into
   ROM's surrender-trigger dispatch path before the NPC ignore/retaliation
   fallback. **MEdit kill/death mobprog runtime probe (2.13.51):**
   OLC-created `kill` and `death` mobprogs now have end-to-end coverage through
   `_interpret_medit` → `spawn_mob` → `apply_damage`, proving the builder-set
   `TRIG_KILL` and `TRIG_DEATH` bits and `MobProgram` rows survive into ROM's
   `damage()` trigger dispatch path when an NPC victim first enters combat and
   then dies. **MEdit exit/exall/grall mobprog runtime probe (2.13.52):**
   OLC-created `exit`, `exall`, and `grall` mobprogs now have end-to-end
   coverage through `_interpret_medit` → `spawn_mob` → `move_character`,
   confirming the builder-set trigger bits and `MobProgram` rows reach the
   correct ROM dispatch branches — EXIT gated on mob position + visibility
   (`src/mob_prog.c:1262-1269`), EXALL unconditional
   (`src/mob_prog.c:1271-1276`), GRALL as the fallback branch in
   `mp_greet_trigger` when the mob is not at `default_pos`
   (`src/mob_prog.c:1333-1345`). All deterministic MEdit trigger types now
   covered. **Diff-harness C-oracle for ACT/BRIBE/GIVE (2.13.55):**
   `mob_act_trigger.json`, `mob_bribe_trigger.json`, and `mob_give_trigger.json`
   scenarios capture C-oracle ground truth for the three remaining deterministic
   dispatch paths. ACT fires via `act("$n stands up.",...)→mp_act_trigger`
   (`src/comm.c:2385`); BRIBE fires when `amount >= atoi(trig_phrase)` in silver
   (`src/act_obj.c:735`); GIVE fires on object-give by vnum match
   (`src/mob_prog.c:1195-1242`). Python and C agree on all three (5,484 tests
   pass). All deterministic Class 11 mobprog trigger dispatch paths now have
   C-oracle ground truth. RNG-locked paths (TRIG_RANDOM, TRIG_DELAY) deferred
   until a reproducible seed sequence is proven. **Diff-harness C-oracle for
   SURR/FIGHT/HPCNT (2.13.56):** `mob_surr_trigger.json`,
   `mob_fight_trigger.json`, and `mob_hpcnt_trigger.json` extend C-oracle coverage
   to combat-path triggers. SURR fires when the PC surrenders to an NPC that has
   `TRIG_SURR` and `mp_percent_trigger` succeeds (`src/fight.c:3235-3241`). FIGHT
   fires once per `violence_update` round via `mp_fight_trigger` after the NPC's
   `multi_hit` completes (`src/fight.c:92-98`). HPCNT fires when mob HP percent
   falls below the threshold (`100*mob->hit/mob->max_hit < atoi(trig_phrase)`,
   `src/mob_prog.c:1357`). New `__mob_hp=<n>` meta-command stages the mob below
   threshold without combat-RNG dependency (added to both diffmain.c and
   pyreplay.py). **Parity fix (2.13.56):** `_room_occupant_line` `FIGHTING`
   branch in `mud/world/look.py` now correctly outputs `"YOU!"` when the mob's
   target is the observer and appends `"."` for same-room non-observer targets,
   matching `src/act_info.c:404-416`. Python and C agree on all three new
   scenarios (5,487 tests pass). **Diff-harness C-oracle for KILL/DEATH
   (2.13.58):** `mob_kill_trigger.json` and `mob_death_trigger.json` added.
   `__instant_kill` meta-command exercises the full `damage()` → `raw_kill` →
   `mp_death_trigger` death path deterministically. Four parity bugs fixed:
   TRIG_DEATH ordering (must fire after `group_gain`), `death_cry` default
   message, `xp_compute` logon=0 elapsed, snapshot dead-char filter. `TRIG_KILL`
   fires on the first hit when victim not yet fighting
   (`src/mob_prog.c:mp_kill_trigger`); `TRIG_DEATH` fires after XP with mob
   temporarily at STANDING (`src/mob_prog.c:mp_death_trigger`). Python and C agree
   (5,493 tests pass). **Diff-harness C-oracle for RANDOM/DELAY (2.13.59):**
   `mob_random_trigger.json` and `mob_delay_trigger.json` added. `__mobile_update`
   meta-command runs one `mobile_update()` tick; `__mob_delay=N` primes
   `mprog_delay`. `TRIG_RANDOM` fires unconditionally each tick when
   `position == default_pos` and `trig_phrase=101` (`src/mob_prog.c:mp_random_trigger`);
   `TRIG_DELAY` fires when `mprog_delay` reaches 0
   (`src/mob_prog.c:mp_delay_trigger`). Python and C agree on first try.
   **Class 11 is now COMPLETE** — all 15 mobprog dispatch paths have
   diff-harness C-oracle ground truth (2.13.59).
7. ~~**Class 13 bypass-site sweep (`/rom-divergence-sweep`).**~~ **DONE (2.13.3).**
    15 runtime-placement bypass sites fixed to route through the INV-039 chokepoints
    or use `insert(0)`. 4 order-preserving sites left as `append` (DB reload, clone,
    conversion, mpjunk-rebuild). FINDING-023 (fire_effect dead-code `room.objects`)
    fixed in same sweep. FINDING-022 (`look in` contents indent) resolved (2.13.4)
    by porting `show_list_to_char` to `mud/utils/act.py`. **FINDING-020 resolved
    (2.13.6)** via the `Object._carry_seq` acquisition-sequence shim — C-oracle
    confirmed equip→remove position is RELATIVE to acquisition order.
    **FINDING-024 resolved (2.13.7)** by persisting `Object._carry_seq` through
    DB object snapshots and advancing the runtime counter on load. **FINDING-025
    resolved (2.13.8)** by making shared wield lookup scan mob inventory
    `wear_loc` and by mirroring ROM's NODROP/INVENTORY + NPC auto-reclaim disarm
    branches.

## Honest caveats

- **The class list itself is argued-complete, not proven-complete** (~11 rows,
  rooted in finite runtime-divergence facts). New classes can surface; add a row
  when one does.
- **Layer A "clean" ≠ "no parity bug in this class"** — it means "no *bypass* of
  the chokepoint." A bug *inside* the chokepoint is a per-function audit concern,
  not a bypass-guard concern.
- **This roster does not find bugs** — it records, per class, which method does
  and whether it has been run. Its value is making the denominator legible, not
  replacing the verification work.
