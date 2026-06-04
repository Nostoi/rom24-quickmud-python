# Session Status — 2026-06-04 — XP-DELIVERY-001 + FINDING-027 money/coin parity (2.13.11)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **XP-DELIVERY-001 — tick-time kill messages reached players a command late**
    ✅ FIXED (2.13.10). A kill resolves during a combat tick, when nothing drains
    the `char.messages` mailbox, so the death-chain lines using the mailbox-only
    `Character.send_to_char` (XP award, level-up, "you gain N hit points",
    alignment zap) surfaced only at the player's next command — the reported
    "experience points after I left the room" bug. All four routed through the
    async-aware `send_to_char_buffered`. Filed as an INV-001 wrong-channel cousin.
  - **FINDING-027 — money/coin object vnum + `create_money` wording/cost** ✅
    RESOLVED (2.13.11). The new `money_drop_get_give` diff scenario found (a)
    `OBJ_VNUM_SILVER_SOME`/`GOLD_SOME` swapped vs ROM `merc.h`, and (b)
    `create_money` hand-rolling proto wording/economics instead of mirroring
    limbo.are #1-#5 ("one silver coin"→"a silver coin", "N silver and N gold
    coins"→"N silver coins and N gold coins", gold cost `100*gold`→`gold`).
    `create_money` now fabricates a per-call proto matching limbo.are exactly.
  - **Diff-harness widening**: `silver` added to the snapshot pipeline + `__gold=`/
    `__silver=` meta-commands; `pyreplay.__mload` now snapshots a spawned mob only
    when declared in `watch.chars` (matches the C shim). New `money_drop_get_give`
    scenario + golden; all 7 goldens regenerated.
  - **FINDING-026 — shop sell/value duplicate-stock pricing + wording** ✅
    RESOLVED (2.13.9).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-04_XP_DELIVERY_AND_FINDING_027_MONEY.md](SESSION_SUMMARY_2026-06-04_XP_DELIVERY_AND_FINDING_027_MONEY.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.11 |
| Tests | Full suite `pytest` → **5425 passed, 4 skipped** (~289s); `ruff check .` clean |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Divergence class 13 | object-list ordering + equipment representation legs closed; money/coin object class (vnum + create_money wording/cost) now covered by FINDING-027 + deterministic `money_drop_get_give` diff scenario |
| Open engine findings | FINDING-024/025 historical; FINDING-027 leaves one non-blocking follow-up (create_money invalid-input return-None vs ROM clamp) |

## Next Intended Task

1. Continue Phase C deterministic diff-harness widening on adjacent no-RNG paths
   (the money class — drop/get/give coins — is now covered).
2. Optional FINDING-027 follow-up: ROM `create_money` clamps invalid input
   (`gold = UMAX(1, gold)`) and never returns NULL; the Python port still returns
   `None` and callers guard on it. Not exercised by any scenario; changing it
   touches the `make_corpse`/`do_drop` caller contract.
3. Add RNG-locked combat scenarios only after seed alignment is proven.

## Other open / deferred items

- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.
