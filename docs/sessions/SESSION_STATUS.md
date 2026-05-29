# Session Status — 2026-05-29 — SHOP-PET-002 + INV-001 (e) fixed (pet buy = create_mobile; INV-001 family ENFORCED)

## Current State

- **Active mode**: cross-file invariants (the per-file audit tracker is
  exhausted — no ⚠️ Partial / ❌ Not Audited rows). This session closed the named
  next task **`SHOP-PET-002`** and a fresh INV-001 SINGLE-DELIVERY member the
  advisor surfaced inside the same function. **INV-001 is again fully ✅ ENFORCED
  — no open violations.**
- **Last completed** (this session):
  - **`SHOP-PET-002`** ✅ FIXED (master 2.11.28, `d4df5356`) — `do_buy`'s pet
    branch now re-creates the pet via `spawn_mob(proto.vnum)` (the
    `create_mobile(pIndexData)` equivalent, `src/act_obj.c:2613`) instead of
    cloning the kennel template, so HP/mana/gold/dam_type are freshly rolled and
    the spawn RNG stream advances exactly as ROM's (gold→hp→mana→damtype→sex,
    `src/db.c:2047-2113`). ROM `do_buy` overrides reapplied on the fresh mob
    (`name`←`player_name` + `short_descr`, `ACT_PET`, `AFF_CHARM`, `comm`).
    Unifies the bought-pet type (`MobInstance`) with the already-`MobInstance`
    reload path. Dead `_clone_pet_character` removed; `deduct_cost` guarded behind
    the `spawn_mob` None-check (no charge for a pet that can't be made). Test
    `tests/integration/test_shop_pet_002_create_mobile_reroll.py`.
  - **`INV-001 (e)`** ✅ FIXED (master 2.11.29, `1ccf9b1e`) — `"Enjoy your pet."`
    was `char.messages.append(...)` AND returned by `do_buy`, double-delivering
    to a connected PC (the `do_kill`/`do_rescue`/INV-001 (d) shape). ROM
    `src/act_obj.c:2635` sends it once and returns void. Dropped the append, kept
    the return. The haggle/"now follows you" lines stay mailbox-only — a lesser
    wrong-channel cousin noted in the tracker, not folded in. Test
    `tests/integration/test_pet_buy_single_delivery.py`.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_SHOP_PET_002_AND_PET_BUY_SINGLE_DELIVERY.md](SESSION_SUMMARY_2026-05-29_SHOP_PET_002_AND_PET_BUY_SINGLE_DELIVERY.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.29 |
| Tests | 4980 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | Cross-file invariants (INV-001 SINGLE-DELIVERY fully ENFORCED again) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. INV-001 SINGLE-DELIVERY is
fully ✅ ENFORCED (members a–e all closed). Concrete next options:

1. **Fresh cross-file invariant probe** — pick a candidate area not yet covered
   by an INV row (affect ticks, position transitions, mob script triggers,
   group/follower chain), run the 5-minute probe-then-scope (read ROM C contract
   → read Python equivalent → one failing test), then close as a gap or file the
   next free INV-NNN. See AGENTS.md "Cross-File Invariants".
2. **Pet-shop wrong-channel cleanup** — the haggle (`"You haggle the price down
   to N coins."`) and `add_follower` "… now follows you." lines in
   `_handle_pet_shop_purchase` are mailbox-only (late for a connected PC). The
   haggle wrong-channel also spans `do_buy`/`do_sell` item branches — a
   shop-wide MAGIC-003-style channel pass, not an INV-001 double-delivery.

Other carried-open items (see the summary's Outstanding section): `Character.pet`
type annotation is stale (`Character | None` but stores `MobInstance` on both buy
and reload paths — cosmetic), `do_cast` object-targeting legs, converter
hardening, and two known xdist flakes (`test_backstab_uses_position_and_weapon`,
`test_combat_death.py`).
