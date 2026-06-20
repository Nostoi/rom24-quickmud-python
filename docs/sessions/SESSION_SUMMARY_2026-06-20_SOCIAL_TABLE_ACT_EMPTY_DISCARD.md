# Session Summary — 2026-06-20 — social_table diff + INV-052 (act_new empty-discard)

## Scope

Continuation of the prior `/loop` table-diff session (per-file audit tracker is
drained; the active pass is systematic ROM↔Python static-table diffs + cross-file
invariants). Picked up the **#1 next-intended task** from `SESSION_STATUS.md`: the
`social_table` diff (`area/social.are` ⇄ `data/socials.json`), which the prior
session left INCONCLUSIVE because a naive line-parser of `social.are` is wrong
(variable-length records, `$` NULL sentinels, `#` early-terminators).

Built a **faithful parser** replicating ROM `src/db2.c:load_socials` +
`src/db.c:fread_word`/`fread_to_eol`/`fread_string_eol` (leading-whitespace strip,
trailing-whitespace preserve, `$`→NULL, `#`→early-terminate) and did a full
244-social × 8-field join. Result: the table is **byte-clean** except one
systematic pattern — **384 fields are ROM-NULL (`$`) vs JSON `""`**, with ZERO
content differences. That pattern turned out to be a real (if subtle) behavioral
divergence in the act-delivery layer, closed as **INV-052**.

## Outcomes

### `INV-052` — ✅ ENFORCED (ACT-EMPTY-DISCARD) — new cross-file invariant

- **ROM C**: `src/comm.c:2240-2244 act_new` — `if (format == NULL || format[0]
  == '\0') return;` is the function's *first* statement, BEFORE the per-recipient
  loop, so it suppresses both delivery AND the per-NPC `mp_act_trigger`/`TRIG_ACT`
  dispatch (`src/comm.c:2384-2385`). Sibling `act_new` sub-contract to INV-025
  (trigger dispatch), INV-027 (PERS masking), INV-029 (first-letter cap).
- **Divergence**: ROM-NULL social slots (the `$` sentinel) load as `""` in
  `data/socials.json`. Python's `act_to_room`/`socials._act_to_char` rendered
  `act_format("")` → `""` and `push_message(recipient, "")` delivered a **spurious
  blank line**; `act_to_room` additionally fired `TRIG_ACT` on the empty message.
  Empirically reproduced: a no-arg `kiss` (`others_no_arg` is ROM-NULL) sent every
  room bystander an empty line; ROM sends nothing.
- **Fix**: `act_new`-faithful empty-guard at the TOP (before loop/push/trigger) of
  the two delivery boundaries the socials path uses —
  `mud/utils/act.py:act_to_room` (closes the room side for ALL ~101 callers) and
  `mud/commands/socials.py:_act_to_char` (social TO_CHAR/TO_VICT). A
  `push_message`-level guard was rejected (advisor): it would fix the blank line
  but leave the spurious `TRIG_ACT` (downstream of the trigger dispatch).
- **Scope honesty**: covers all room broadcasts + the socials directed-line class.
  A general sweep of direct single-recipient `push_message`/`send_to_char_buffered`
  empty-variable sites *outside* socials is an un-done, low-yield follow-up (most
  pass literals/guaranteed-non-empty buffers) — spelled out in the INV status cell
  so "ENFORCED" isn't misread as "every act() empty everywhere is guarded."
- **Blast radius**: `act_to_room` is CRITICAL by caller-count (101), but the change
  is a pure additive guard mirroring ROM exactly — it can only suppress empties
  ROM also suppresses. Full suite green confirms the behavioral delta is narrow.
- **Tests**: `tests/integration/test_inv052_act_empty_discard.py` (4 — act_to_room
  empty→no delivery, act_to_room empty→no TRIG_ACT, socials._act_to_char empty→no
  delivery, end-to-end `kiss` no-arg → no blank line to bystander).

## Clean negative (verified, no further gap)

- **`social_table` is byte-clean.** 244 socials, all 8 fields, full faithful join:
  no missing/extra socials, no name dups, zero content differences. The only
  divergence was the NULL-vs-`""` representation, neutralized by INV-052. This
  resolves the prior session's INCONCLUSIVE `social_table` item — it is now a
  CLEAN NEGATIVE save for the one act-layer fix.

## Files Modified

- `mud/utils/act.py` — INV-052 empty-guard at top of `act_to_room`.
- `mud/commands/socials.py` — INV-052 empty-guard at top of `_act_to_char`.
- `tests/integration/test_inv052_act_empty_discard.py` — new (4 tests).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — new INV-052 row + scope-honest status.
- `CHANGELOG.md` — Fixed entry (INV-052).
- `pyproject.toml` — 2.14.197 → **2.14.198**.

## Test Status

- `tests/integration/test_inv052_act_empty_discard.py` — 4/4 passing.
- Full suite: **5988 passed, 4 skipped** (was 5984/4 at session start; +4 = the
  new test file). `ruff check` clean on all touched `.py` files.
- GitNexus reindexed exit-0 after the code commit (only the 2 documented harmless
  C-header scope failures `recycle.h`/`olc.h`; zero Python failures).

## Next Steps / Outstanding

The low-risk data/registration veins remain drained. Remaining candidates, in
priority order:

1. **INTERP-028** (🔄 OPEN, MINOR) — duplicate `bs` registration (alias on
   `backstab` + standalone `Command("bs", …)`). Cosmetic, no observable
   divergence.
2. **Per-spell `min_position` enforcement** (behavioral, verify-then-decide) — ROM
   `skill_table` carries a POS per spell; `do_cast` gates on a flat
   `POS_FIGHTING`, and `skills.json` carries no per-spell POS. Whether Python
   should enforce each spell's own min position is unverified. **HIGH-blast-radius
   core path (do_cast/dispatch) → FILE, do not fix autonomously** per the risk
   posture; needs human-reviewed work.
3. **INV-052 follow-up (low-yield)** — general sweep of direct single-recipient
   `push_message`/`send_to_char_buffered` empty-variable sites outside socials.
   Re-open with a per-site gap only if a scenario/golden surfaces a blank-line
   leak; do not grind a full audit speculatively.
4. **Risk posture (advisor)**: when a behavioral divergence needs logic changes in
   a HIGH-blast-radius core path (combat/movement/dispatch), file it, don't fix
   autonomously. Pure additive guards that mirror a single ROM function exactly
   (like INV-052 / INTERP-034) are the exception — they are strictly
   parity-correcting and safe despite wide caller counts.
