# Session Summary — 2026-06-10 — affect shadow LIFO order, DEX/INT/WIS APPLY_ mapping

## Scope

Continuation from v2.13.62. The active pass is cross-file invariants / diff-harness coverage.
The previous session authored the `affect_expiry_lifecycle` diff-harness scenario but left it
skipping because no C golden had been captured. This session built the diffshim binary and
captured the golden — which immediately revealed three parity bugs in the Python affect system.
All three were diagnosed, fixed with failing-test-first discipline, and committed as v2.13.63.

## Outcomes

### `affect_expiry_lifecycle` C-golden captured — ✅ LIVE

- **Scenario**: `tools/diff_harness/scenarios/affect_expiry_lifecycle.json`
- **Golden**: `tests/data/golden/diff/affect_expiry_lifecycle.golden.json` (10 steps)
- **Build**: `cd src && make -f Makefile.diffshim diffshim` succeeded on Apple clang 17
- **Result**: capturing the golden revealed three divergences; all three fixed (see below).
  The scenario is now a live C-oracle guard — no longer skipped.

### Bug 1: Affect shadow LIFO ordering — ✅ FIXED

- **Root cause**: `sync_spell_effect_to_affected` and `Character.affect_to_char` both used
  `list.append()` (FIFO), but ROM `src/handler.c:1271 affect_to_char` head-inserts:
  `paf_new->next = ch->affected; ch->affected = paf_new;` (LIFO — newest first).
- **Observable divergence**: C output shows `['haste', 'sanctuary']` (haste cast last →
  appears first). Python showed `['sanctuary', 'haste']`.
- **Fix**: Changed all six `affected.append(...)` calls in `sync_spell_effect_to_affected`
  to `affected.insert(0, ...)`, and the one in `Character.affect_to_char` likewise.
- **ROM C reference**: `src/handler.c:1271`
- **Test**: `test_affected_list_lifo_order` in `tests/test_handler_affects_rom_parity.py`

### Bug 2: DEX/INT/WIS → wrong APPLY_ location in shadow AffectData — ✅ FIXED

- **Root cause**: `sync_spell_effect_to_affected` computed `location = stat_int + 1` where
  `stat_int = int(stat)`. Python's `Stat` enum order (STR=0, INT=1, WIS=2, DEX=3, CON=4)
  differs from ROM C's APPLY_ order (STR=1, DEX=2, INT=3, WIS=4, CON=5). Result:
  - `Stat.DEX (3) + 1 = 4` → stored as `APPLY_WIS` instead of `APPLY_DEX=2`
  - Spells affected: `haste` and `slow` (both use `Stat.DEX`)
- **Observable divergence**: C shows `modifies dexterity by 4`, Python showed `modifies wisdom by 4`.
- **Note**: The actual stat application was correct (applied via `_apply_stat_modifier` using
  Stat.DEX as array index) — only the shadow location (used by display + reset_char) was wrong.
- **Fix**: Replaced `stat_int + 1` with an explicit `_STAT_TO_APPLY` dict: `{STR:1, DEX:2,
  INT:3, WIS:4, CON:5}`. Same fix applied in `handler.py:reset_char` secondary stat-matching
  blocks (which used `int(Stat.DEX) + 1 = 4` to match equipment APPLY_ locations from .are
  files — those store ROM C constants directly).
- **ROM C reference**: `src/merc.h:1205-1210`
- **Test**: `test_dex_stat_modifier_shadow_uses_apply_dex` in `tests/test_handler_affects_rom_parity.py`

### Bug 3: Sanctuary missing wear-off message — ✅ FIXED

- **Root cause**: Python `sanctuary` created a `SpellEffect` with no `wear_off_message`.
  ROM C `src/const.c:1438` defines `msg_off = "The white aura around your body fades."` in
  the sanctuary skill_table entry.
- **Observable divergence**: After `__char_update` at step 9, C emitted both haste
  (`"You feel yourself slow down."`) and sanctuary wear-off messages. Python emitted only haste.
- **Fix**: Added `wear_off_message="The white aura around your body fades."` to the sanctuary
  SpellEffect in `mud/skills/handlers.py`.
- **ROM C reference**: `src/const.c:1438`

## Files Modified

- `mud/models/character.py` — `sync_spell_effect_to_affected`: `append` → `insert(0)`;
  added `_STAT_TO_APPLY` dict; `Character.affect_to_char`: `append` → `insert(0)`
- `mud/handler.py` — `reset_char`: added `APPLY_STR/DEX/INT/WIS/CON` locals; replaced
  `int(Stat.X) + 1` formula with correct constants in two stat-matching blocks
- `mud/skills/handlers.py` — `sanctuary`: added `wear_off_message`
- `tests/test_handler_affects_rom_parity.py` — two new enforcement tests
- `tests/data/golden/diff/affect_expiry_lifecycle.golden.json` — new golden (10 steps)
- `CHANGELOG.md` — added [2.13.63] Fixed entries
- `pyproject.toml` — 2.13.62 → 2.13.63

## Test Status

- New enforcement tests: `test_dex_stat_modifier_shadow_uses_apply_dex`,
  `test_affected_list_lifo_order` — both passing
- Diff harness: 40 passed, 1 skipped (`shop_sell_keeper_broke` pre-existing) — `affect_expiry_lifecycle` now passes
- Full suite: **5504 passed, 5 skipped** (no regressions from 27-caller blast radius)

## Next Steps

Cross-file invariants remains the active pass. The diff-harness now has 25 scenarios with
40 C-oracle tests. Remaining open work:

1. **`shop_sell_keeper_broke`** — the one remaining skipped scenario (no golden); authoring
   a new buy/sell round-trip scenario may be worth more than fixing the edge case in the
   broken-keeper path.

2. **Charm/follower wear-off lifecycle** — an unexercised surface called out in prior
   sessions: `AFF_CHARM` expiry, follower detach, `pet` pointer cleanup. Would exercise
   `stop_follower` / `INV-037` through the diff harness.

3. **`drink`/`eat`/`food` consumption** — condition decay + THIRST/FULL/HUNGER bitvectors;
   another untested surface.

4. **MATH-002/003/004** — documented ⚠️ OPEN hygiene items (LOW severity) in
   `docs/parity/audits/MATH_AND_RNG.md`. Held for a future lint rule; no observable gap.
