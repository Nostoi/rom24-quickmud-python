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
| 6 | **Pointer identity** | C pointer `==` vs Python object `==`/`is` | `is` for character identity compares | ❌ | partial | INV-031 (`is_same_group` uses `is`), INV-006; specific sites tested, no bypass-grep across `mud/` |

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
| 4 | **Async message delivery / act-cap** | C synchronous `write_to_buffer` in tick vs Python async dispatch (double-deliver, miss, mis-cap) | behavioral — single-delivery (XOR), per-recipient masking, first-letter cap, verified by integration tests, not a lexical bypass | enforced | INV-001 (×5 `test_inv001_*.py`) / 027 / 029; ACT-CAP-001..004. **Reclassified A→C 2026-06-02:** a clean static bypass-guard is INFEASIBLE — legitimate hand-rolled XOR loops (`do_yell`) correctly use `create_task(send_to_char)`, and `.messages.append` has many legitimate sites (`Character.send_to_char`, broadcast primitives, actor-self lines), so any blanket grep false-positives. The contract is contextual → Layer C, with a Layer-B "review new delivery sites" element. |

## What "done" means, per layer

- **Layer A:** every class has a committed bypass-guard and it's green. Today:
  4 of 5 guarded (RNG, equipment-key, attribute-naming, **flag-hex** —
  `test_flag_hex_convention.py`, added 2026-06-02). **To-do:** class
  6 (pointer-identity scanner) — may prove infeasible as Layer A and reclassify,
  exactly as async-delivery (old class 4) did on 2026-06-02 when a clean
  bypass-grep turned out to false-positive. Flag-hex came back the *other* way:
  a tight prefix-anchored grep had exactly one legitimate hit (the `WiznetFlag`
  enum body), so it was allowlist-able → feasible, cleaner than async got.
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
4. **Class 6 (pointer-identity) scanner.** Scope a pattern for `==`/`!=`
   between two `Character` references; high false-positive risk → may be
   Layer-B.
5. **Class 11 dynamic widening (optional).** Hypothesis `RuleBasedStateMachine`
   driving `diff_harness` to attack the scenario-enumeration limit.

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
