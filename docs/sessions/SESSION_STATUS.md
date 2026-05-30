# Session Status — 2026-05-30 — INV-001 Shop Haggle Channel

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **`INV-001` shop haggle wrong-channel cousin ✅ FIXED (2.11.49)**
    — `mud/commands/shop.py` now delivers pet-buy, item-buy, and sell haggle
    success lines via `push_message`, so connected players receive them
    immediately through the descriptor, with mailbox fallback preserved for
    disconnected characters/tests.
- **Earlier today**: FIGHT-032 (2.11.44), FIGHT-033 (2.11.45), FIGHT-034
  (2.11.46), VISION-002 (2.11.47), ACT-CAP-001/002/003/004, FIGHT-031,
  INV-029.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-30_INV001_SHOP_HAGGLE_CHANNEL.md](SESSION_SUMMARY_2026-05-30_INV001_SHOP_HAGGLE_CHANNEL.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.49 |
| Tests | Focused shop slice: 39 passed (`test_shop_haggle_delivery_channel.py`, `test_pet_buy_single_delivery.py`, `tests/test_shops.py`) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants — continue probe/close cycle |

## Next Intended Task

Continue cross-file invariants as the primary pass. The shop haggle
wrong-channel cousin is closed; pick the next candidate area not yet covered by
an INV row, or address one of the carried-open maintenance items below.

Other carried-open items: known xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); `Character.pet` stale type
annotation; `do_cast` object-targeting legs; unused imports in
`group_commands.py`.

## Commit / push state

- Local working tree has uncommitted 2.11.49 changes.
- Existing `master` branch is still ahead of `origin/master`; do not push
  without the user's say-so.
