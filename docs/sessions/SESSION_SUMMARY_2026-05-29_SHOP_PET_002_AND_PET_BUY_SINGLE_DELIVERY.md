# Session Summary — 2026-05-29 — SHOP-PET-002 + INV-001 (e) (pet-buy create_mobile + SINGLE-DELIVERY)

## Scope

Continued from the FIGHT-030 / INV-001 (d) handoff. `SESSION_STATUS.md` named
**`SHOP-PET-002`** as the top concrete next task (a local single-function
divergence in the pet-shop buy path). Closed it via the standard gap-closer TDD
flow. While closing it, the advisor surfaced a fresh **INV-001 SINGLE-DELIVERY**
violation living in the same function (`_handle_pet_shop_purchase`) — the
`"Enjoy your pet."` line double-delivered to a connected PC — which was filed as
**INV-001 (e)** and then closed as a second commit. Both landed as separate
`fix(parity)` commits (one gap = one test = one commit).

## Outcomes

### `SHOP-PET-002` — ✅ FIXED (2.11.28, `d4df5356`)

- **Python**: `mud/commands/shop.py:_handle_pet_shop_purchase`
- **ROM C**: `src/act_obj.c:2613` (`pet = create_mobile(pet->pIndexData)`),
  `src/db.c:2047-2113` (`create_mobile` RNG draw order)
- **Gap**: `do_buy`'s pet branch cloned the kennel template instead of
  re-creating the pet from the prototype. ROM does a **fresh** `create_mobile`,
  which draws the spawn RNG stream (gold → hp → mana → damtype-when-unset →
  sex-when-random) and re-rolls each value. The old `_clone_pet_character`
  copied the template `MobInstance`'s already-rolled HP/mana/gold/dam_type, so a
  bought pet (a) inherited the template's *cloned* random-default dam_type rather
  than re-rolling `number_range(1,3)`; (b) advanced the spawn RNG stream by
  **zero** draws, desyncing any RNG consumer ordered after the purchase vs ROM;
  (c) inherited HP/mana/gold rather than freshly rolling them.
- **Fix**: `_handle_pet_shop_purchase` now creates the pet via
  `spawn_mob(proto.vnum)` — the `create_mobile` equivalent and **single source of
  truth** for the ROM draw order (it also registers the mob in
  `character_registry`, so the prior explicit append was removed). The ROM
  `do_buy` overrides are reapplied to the fresh mob: `name` ← `player_name` and
  `short_descr` from the index (`src/db.c:2038-2039`, compensating for
  `from_prototype` setting `name` ← `short_descr`), `ACT_PET`, `AFF_CHARM`, and
  `comm` assigned outright (`src/act_obj.c:2614-2616`). This also **unifies the
  bought-pet type (`MobInstance`) with the already-`MobInstance` reload path**
  (`mud/db/serializers.py:_deserialize_pet` → `spawn_mob`), removing a pre-existing
  bought-vs-reloaded type inconsistency. The now-dead `_clone_pet_character` was
  removed. `deduct_cost` is guarded **behind** the `spawn_mob` None-check
  (advisor catch): `spawn_mob` fails soft where ROM's `create_mobile` `exit(1)`s,
  so charging-before-guard would let a player pay for a pet that couldn't be made.
- **Tests**: `tests/integration/test_shop_pet_002_create_mobile_reroll.py` (1) —
  the bought pet's random fields (`max_hit`/`gold`/`silver`/`dam_type`) match a
  fresh `create_mobile` from the same seed, AND the purchase advances the RNG
  stream identically (the **deterministic discriminator**: a clone draws nothing,
  so the post-purchase draw desyncs). Fail-first verified: `bought_next (731965)
  != control_next (44722)`. Existing `test_pet_shop_purchase_creates_charmed_pet`
  `has_comm_flag` assertions reconciled to `comm`-bit checks (the pet is now a
  `MobInstance`, which keys `comm` as a raw int).

### `INV-001 (e)` — ✅ FIXED (2.11.29, `1ccf9b1e`)

- **Python**: `mud/commands/shop.py:_handle_pet_shop_purchase`
- **ROM C**: `src/act_obj.c:2635` (`send_to_char("Enjoy your pet.\n\r", ch)` —
  once, void return)
- **Gap**: the success line `"Enjoy your pet."` was
  `char.messages.append(...)` **and** returned by `do_buy`. The connection loop
  (`mud/net/connection.py:1980-2000`) sends a command's return value AND drains
  `char.messages`, so a connected PC buying a pet saw the line **twice** — the
  same INV-001 shape as `do_kill` (FIGHT-020), `do_surrender`, `do_rescue`
  (FIGHT-029), and the "still recovering" sweep (INV-001 (d)). Surfaced by the
  advisor while closing SHOP-PET-002 (which rewrote this function).
- **Fix**: dropped the mailbox append, kept the return (the single canonical
  delivery — the INV-001 (d) recipe). The haggle (`"You haggle the price down to
  N coins."`) and follow (`"… now follows you."`) lines remain mailbox-only — a
  lesser **wrong-channel cousin** noted in the tracker but NOT folded in (the
  haggle wrong-channel also spans the item-buy/sell branches; broader, separate).
- **Tests**: `tests/integration/test_pet_buy_single_delivery.py` (1) — behavioral
  connected-PC single-delivery through `do_buy`. Fail-first showed
  `['Enjoy your pet.', 'companion pet now follows you.', 'Enjoy your pet.']` (2×).
  `test_pet_shop_purchase_creates_charmed_pet` realigned (the line is return-only
  now; the mailbox ends with the haggle + follow lines).

## Files Modified

- `mud/commands/shop.py` — pet buy re-creates via `spawn_mob` (SHOP-PET-002);
  `"Enjoy your pet."` mailbox append dropped (INV-001 (e)); dead
  `_clone_pet_character` removed; unused `character_registry` import dropped.
- `tests/integration/test_shop_pet_002_create_mobile_reroll.py` — new (1 test).
- `tests/integration/test_pet_buy_single_delivery.py` — new (1 test).
- `tests/test_shops.py` — `test_pet_shop_purchase_creates_charmed_pet` reconciled
  (`has_comm_flag` → `comm`-bit; mailbox no longer carries "Enjoy your pet.").
- `docs/parity/FIGHT_C_AUDIT.md` — SHOP-PET-002 row → ✅ FIXED.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 (e) filed then → ✅
  FIXED; INV-001 status cell back to fully ✅ ENFORCED.
- `CHANGELOG.md` — `[2.11.28]` (SHOP-PET-002) + `[2.11.29]` (INV-001 (e)) Fixed.
- `pyproject.toml` — 2.11.27 → 2.11.29 (two patch bumps).

Commits: `d4df5356` (SHOP-PET-002), `1ccf9b1e` (INV-001 (e)).

## Test Status

- `tests/integration/test_shop_pet_002_create_mobile_reroll.py` — 1/1.
- `tests/integration/test_pet_buy_single_delivery.py` — 1/1.
- Shops + pet + still-recovering area suite — 41 passed.
- **Full suite**: **4980 passed, 4 skipped** (+2 vs prior 4978 = one new test per
  gap). No regressions across both fixes (full suite run green after each).
- `ruff check` on touched files: shop.py (`I001` import-block + `F541` `$p`
  literal) and test_shops.py (`I001`) errors are all **pre-existing** — verified
  byte-identical to HEAD before each commit; new test files are clean; **0 new**.
- `gitnexus_detect_changes`: both commits LOW risk, 0 affected processes; scope =
  exactly `_handle_pet_shop_purchase` + its locals + the reconciled test + the
  doc sections. (shop.py is in the documented 32KB GitNexus-failing list, so the
  full-suite pass is the authoritative regression check.) Reindexed after each
  commit (exit 0).

## Outstanding

(Carried; both this session's gaps now closed.)

- **Lesser wrong-channel cousins in `_handle_pet_shop_purchase`** (noted in
  INV-001 (e)'s tracker row, not yet fixed): the haggle line and the
  `add_follower` "… now follows you." line are mailbox-only (late for a connected
  PC). The haggle wrong-channel spans the item-buy/sell branches too — a broader,
  separate cleanup, not an INV-001 double-delivery.
- **`Character.pet` type annotation** is `Character | None`, but both the reload
  path and (now) the buy path store a `MobInstance`. The runtime is correct
  (duck-typed throughout); the annotation is stale. Cosmetic pyright-only.
- **Object targeting in `do_cast`** — `TAR_OBJ_CHAR_*` object-target legs
  (`src/magic.c:502-506`, `:525-529`); named-not-found wording (MAGIC_C_AUDIT).
- **Converter hardening** — `convert_skills_to_json.py` is lossy (drops
  hand-added `cancellation`/`harm`); make it merge-not-replace.
- **`test_backstab_uses_position_and_weapon` / `test_combat_death.py` xdist
  flakes** (carried) — seed RNG; root-cause leaking sibling if they recur.
- Stray uncommitted 1-line doc tweak to
  `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` (present across sessions;
  unrelated to parity — left uncommitted).

## Next Steps

Per-file audit tracker remains exhausted (no ⚠️ Partial / ❌ Not Audited rows);
**cross-file invariants is the standing pass**. INV-001 SINGLE-DELIVERY is again
fully ✅ ENFORCED with member (e) closed. Concrete next candidates:

1. Probe a fresh cross-file invariant area not yet covered by an INV row (affect
   ticks, position transitions, mob script triggers, group/follower chain) —
   probe-then-scope per AGENTS.md "Cross-File Invariants".
2. The haggle/follow wrong-channel cleanup above, if a shop-wide MAGIC-003-style
   pass is desired (would touch `do_buy`/`do_sell`/`do_value` and pet buy).
