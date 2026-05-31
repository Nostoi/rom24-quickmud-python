# Session Status — 2026-05-31 — affect-tick parity (GL-026–GL-030) + VISIBLE-001 + EMOTE-003

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
- **GL-027 + GL-029 (2.12.8) — CLOSED** (commit `94fc9226`). Chose fix
  direction (b): gave `MobInstance` a real `affected` list and extracted
  `Character._sync_spell_effect_to_affected` into a shared
  `mud.models.character.sync_spell_effect_to_affected` helper, so mobs route
  through the main `affected`-list tick path (one `number_range(0,4)` roll per
  `duration>0` affect — the GL-026 contract — and decrement-and-stay). The
  re-cast merge now mirrors Character's remove-then-apply (fixes a latent
  hitroll/damroll double-apply). **GL-029** (caught by advisor review before
  push): the helper emitted a shadow only for numeric modifiers, so a flag-only
  effect (sanctuary/sleep/…) produced none — and a regression GL-027 itself
  introduced: a flag-only effect FROZE on the main path behind a
  modifier-bearing affect (never decremented). Fixed by emitting one base
  `AffectData` (`APPLY_NONE`, `bitvector=flag`) when no modifier shadow was
  created; every active `spell_effect` now mirrors ≥1 `AffectData`, so the
  dict-only fallback is no longer reachable via the normal apply path. Full
  suite green (5126 passed, 4 skipped). Tests:
  `tests/integration/test_gl027_mob_affect_tick_parity.py` (3:
  RNG-stream, decrement-and-stay, flag-only-orphan guard).
- **VISIBLE-001 (2.12.9) — CLOSED** (commit `0cbdb013`). `do_visible` stripped
  `"invisibility"`/`"mass invisibility"` but the spells register `"invis"`/
  `"mass invis"`, so cast invis lingered in `spell_effects` after going visible
  (spurious later wear-off). Now routes through `remove_spell_effect("invis")`/
  `("mass invis")`. Test: `tests/integration/test_visible001_strip_cast_invis.py`.
- **GL-030 (2.12.9) — CLOSED** (commit `535e10c3`). The pet round-trip check
  surfaced a crash GL-027 introduced: `_serialize_pet` did `if affect.type < 0`
  on the new string-keyed shadow `AffectData` → `"bless" < 0` `TypeError`, so
  saving a buffed/debuffed charmed pet crashed the character save. Guarded with
  `isinstance(affect_type, int)`. Test: `tests/test_pet_save_affect_roundtrip.py`.
- **GL-031 (OPEN, pre-existing)** — a charmed pet's spell-cast buffs aren't
  persisted across save/reload (`MobInstance.spell_effects` was never
  serialized; GL-030 correctly skips the string-named shadows). ROM `fwrite_pet`
  saves pet affects by SN. Fix: serialize `pet.spell_effects` + restore via
  `apply_spell_effect`. See `UPDATE_C_AUDIT` GL-031.
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
  [SESSION_SUMMARY_2026-05-31_GL027_MOB_AFFECT_TICK_PATH.md](SESSION_SUMMARY_2026-05-31_GL027_MOB_AFFECT_TICK_PATH.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.9 |
| Tests | 5130 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 24 enforced — INV-025 now records the MOBtrigger *suppression* leg (EMOTE-003 correction); producer leg anchored at `do_stand` |
| Open correctness gaps | GL-027 + GL-029 + GL-030 + VISIBLE-001 all closed (2.12.8/2.12.9). One open gap filed (pre-existing, deferred): **GL-031** (`UPDATE_C_AUDIT` — a charmed pet's spell-cast buffs don't persist across save/reload; `MobInstance.spell_effects` was never serialized) |
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
3. ~~GL-027~~ **closed 2.12.8 (commit `94fc9226`)** — chose fix direction (b):
   `MobInstance` got a real `affected` list + shared
   `sync_spell_effect_to_affected`, so mobs route through the main GL-026 path.
   Adversarial review caught **GL-029** (flag-only effects froze on the main
   path / hit the fallback) — also closed in the same commit via a base
   `AffectData`. The dict-only fallback is now unreachable via the normal apply
   path. See `UPDATE_C_AUDIT` GL-027/GL-029.
4. ~~Affect ticks~~ **probed/closed 2.12.6–2.12.8** — GL-026 (RNG order), GL-028
   (mob expiry crash), GL-027 + GL-029 (mob/flag-only affect-tick path) all
   closed. Affect-tick candidate is now exhausted.
5. Broader INV-025 sweep: remaining non-combat `_push_message`/`broadcast_room`
   narration surfaces where the matching ROM site uses `act()`.
6. Other probe candidates: position transitions, group/follower chain.

Method: probe-then-scope (read ROM C contract → read Python equivalent →
one failing test for the contract → close as a gap or file as next INV-NNN).
