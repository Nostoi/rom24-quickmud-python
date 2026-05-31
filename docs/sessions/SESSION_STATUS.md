# Session Status — 2026-05-31 — affect-tick parity (GL-026/GL-028) + EMOTE-003

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, affect-ticks probe → 2.12.6/2.12.7)**:
  - **GL-026 (2.12.6)** — affect-tick level-fade RNG-consumption order.
    ROM `if (number_range(0,4)==0 && paf->level>0)` (`src/update.c:768`)
    consumes the roll **unconditionally** for every `duration>0` affect (C
    `&&` left-operand-first); Python had the operands swapped
    (`level>0 and number_range(...)`), skipping the roll at `level==0` — and
    level reaches 0 via the fade mechanic on long-lived affects, desyncing
    the global RNG stream for the same tick's plague/poison damage and
    beyond. Reordered to roll first. Test:
    `tests/integration/test_gl026_affect_tick_rng_consumption.py`.
  - **GL-028 (2.12.7)** — an expiring spell effect on a mob crashed the
    whole game tick. `MobInstance.apply_spell_effect` stores into
    `spell_effects` without an `affected` mirror, so mobs tick through
    `tick_spell_effects`' dict-only fallback, which calls
    `remove_spell_effect` on expiry — a method `MobInstance` lacked →
    `AttributeError` propagated out of the unguarded `char_update`/`game_tick`,
    aborting the tick (all later characters + obj/idle/aggr updates skipped).
    Added symmetric `MobInstance.remove_spell_effect`. Test:
    `tests/integration/test_gl028_mob_spell_effect_tick.py` (real char_update
    path).
- **Open follow-up filed**: **GL-027** (⚠️ OPEN, `UPDATE_C_AUDIT`) — the same
  dict-only fallback still (1) rolls zero RNG per mob affect and (2) expires
  `duration==1` one tick early. Fix-direction decision pending: patch the
  fallback to mirror ROM's loop, **or** give `MobInstance` a real `affected`
  list + sync so mobs collapse onto the main GL-026 path and the fallback
  retires. GL-028 unblocked exercising this.
- **Prior this session (2.12.5)**:
  - **EMOTE-003 / INV-025 correction** — `do_emote` no longer fires NPC
    act-triggers. ROM `do_emote` (`src/act_comm.c:1090-1093`) wraps its
    `act()` in `MOBtrigger = FALSE`, and `src/comm.c:2384` dispatches
    `mp_act_trigger` only `else if (MOBtrigger)` — so an emote NEVER fires
    a `TRIG_ACT` (deliberate: free-form text must not let a player forge a
    trigger phrase, e.g. `emote bows` tripping an NPC scripted on "bows").
    The 2.9.40 INV-025 enforcement mis-identified `do_emote` as the
    *canonical producer* and made it call `mp_act_trigger_room` at runtime —
    a shipped behavioral bug. Removed the dispatch; retargeted the INV-025
    suite onto `do_stand` (a genuine `act()` producer, no MOBtrigger wrap)
    so the producer/gate/self-exclusion legs each still exercise their
    mechanism. MOBtrigger-suppression sweep confirmed `do_pmote`/`do_give`/
    `do_mpasound` were already correct; only `do_emote` over-dispatched.
    Commit d435e4ad. Also verified (clean, no change): TRIG_KILL fires at
    first-combat-entry (engine.py:680-687 ↔ fight.c:735-745) and TRIG_DEATH
    fires before death with position→STANDING (engine.py:752-759 ↔
    fight.c:918-922).
- **Prior session (2.12.2–2.12.4)**:
  - **TRAIN-004 / WIZ-050 (2.12.2)** — stat training (`do_train`) and the
    `set char <stat>` ranges (`do_mset`) now use ROM's race/class-specific
    `get_max_train` instead of a hardcoded cap. Root cause was a shared broken
    helper: `mud.handler.get_max_train` compared the int `ch.race` index
    against PC-race *name* strings and read a non-existent `class_num`, so it
    fell through `return 18` for every real PC — `do_train` shadowed that with
    its own literal 22, and `do_mset` inherited the broken 18 cap. Fixed at the
    root (int-race→name bridge, `ch_class`, +3 human / +2 other prime bonus,
    fallback 25); both call sites route through the one helper. Corrected the
    false-✅ `get_max_train` row in HANDLER_C_AUDIT.
  - **INV-025 door family (2.12.3)** — `do_close`/`do_lock`/`do_unlock`/
    `do_pick` now dispatch `TRIG_ACT` to listening NPCs (was only `do_open`),
    via the existing `_broadcast_act_to_room` helper. The reverse-side
    linked-room broadcasts are left plain (uniform open follow-up; see summary).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-31_TRAIN004_AND_INV025_DOOR_COMMANDS.md](SESSION_SUMMARY_2026-05-31_TRAIN004_AND_INV025_DOOR_COMMANDS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.7 |
| Tests | 5123 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 24 enforced — INV-025 now records the MOBtrigger *suppression* leg (EMOTE-003 correction); producer leg anchored at `do_stand` |
| Open correctness gaps | **GL-027** (mob affect-tick fallback: 0 RNG rolls + off-by-one expiry — fix-direction pending; see `UPDATE_C_AUDIT`) |
| Active focus | cross-file invariants probe pass (affect-ticks) |

## Next Intended Task

No open correctness gaps. Resume the **cross-file invariants probe pass**:

1. ~~INV-025 reverse-side door broadcasts~~ **closed 2.12.4** — `do_open` /
   `do_close` reverse-side linked-room loops now dispatch TRIG_ACT via the new
   `mud/mobprog.py:mp_reverse_act_trigger_room` (actor == recipient, mirroring
   ROM's `act("The $d opens.", rch, NULL, ..., TO_CHAR)` self-dispatch at
   `src/act_move.c:447-448`/`:545-547`). Test:
   `tests/integration/test_inv025_reverse_door_act_trigger_dispatch.py`.
   The INV-025 door family is now fully wired (lock/unlock/pick have no
   reverse-side broadcast — ROM flips the bit silently).
2. ~~Mob-trigger dispatch audit~~ **probed 2.12.5** — all 15 `mp_*_trigger`
   functions are wired at the correct ROM sites; TRIG_KILL/TRIG_DEATH semantics
   verified clean; the only divergence was the EMOTE-003 over-dispatch (closed).
   The MOBtrigger-suppression sweep is now complete (emote/pmote/give/mpasound
   all verified).
3. **GL-027 (highest-value open gap)** — close the mob affect-tick fallback
   divergence (0 RNG rolls + off-by-one). Decide fix direction first:
   patch the dict-only fallback to mirror ROM's loop, **or** give
   `MobInstance` a real `affected` list + sync (the ROM-correct end-state —
   one affect list, one loop — but higher blast radius; not a tail-of-session
   change). See `UPDATE_C_AUDIT` GL-027.
4. ~~Affect ticks~~ **probed 2.12.6/2.12.7** — GL-026 (RNG order) + GL-028
   (mob expiry crash) closed; GL-027 remains (see #3).
5. Broader INV-025 sweep: remaining non-combat `_push_message`/`broadcast_room`
   narration surfaces where the matching ROM site uses `act()`.
6. Other probe candidates: position transitions, group/follower chain.

Method: probe-then-scope (read ROM C contract → read Python equivalent →
one failing test for the contract → close as a gap or file as next INV-NNN).
