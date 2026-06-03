# Session Status — 2026-06-03 — INV-038 + live-report fixes + ruff/tooling cleanup (2.12.91)

## Current State

This session (continued across several threads) landed, in order:

1. **INV-038 IDLE-TIMER-RESET-ON-INPUT** (✅ ENFORCED, 2.12.86) — ROM resets a
   PC's idle `ch->timer` only on descriptor input, not every tick; the Python
   port reset it every tick for connected players, killing idle→void. Fix spans
   `char_update` + `_read_player_command`. Autoquit gated to link-dead chars
   (connected-player autoquit-with-teardown filed as **GL-035**, OPEN; the
   single-quit-per-tick quirk as **GL-034**, OPEN).
2. **GL-036** (✅ FIXED, 2.12.87) — live player report: a berserker mob crashed
   the game tick every round (`MobInstance` lacked `has_spell_effect`). Added it.
3. **`do_practice` double-delivery** (✅ FIXED, 2.12.88, INV-001) — live report:
   practice lines printed twice (mailbox append + return). Dropped the append.
   Practice learning speed verified ROM-correct (no change).
4. **Repo-wide ruff cleanup** (2.12.89–90) — `ruff check .` and
   `ruff format --check .` are now **fully clean repo-wide** (was ~1750 findings,
   851 files). The `mud/` F841 review surfaced **MAGIC-009** (below).
5. **pre-commit activated + aligned to ruff** (2.12.91) — installed in-clone;
   5 commit-stage hooks (ruff, ruff-format, validate-area-parity,
   equipment-key-convention, attribute-convention). `test-fixtures-lint` left
   `stages: [manual]` (~617 legacy sites).
6. **`validate_area_parity` fixed** (2.12.91) — was comparing two loaders with
   different runtime normalizations (D-reset boot-consumption + M-arg4 0→1),
   reporting 34 false positives; now compares raw conversion → perfect parity on
   all 50 shipped areas; re-enabled as a commit hook.

- **Pointer to prior summary**:
  [SESSION_SUMMARY_2026-06-03_INV038_IDLE_TIMER_INPUT_RESET.md](SESSION_SUMMARY_2026-06-03_INV038_IDLE_TIMER_INPUT_RESET.md)

## Next Intended Task — MAGIC-009 (the one open engine bug)

**Fix `spell_cancellation`'s missing per-effect `check_dispel`/`saves_dispel`
roll.** Full instructions, ROM refs, the exact fix, and the RNG-controlled test
rewrites are in the dedicated handoff:

➡️ **[HANDOFF_2026-06-03_MAGIC009_CANCELLATION.md](HANDOFF_2026-06-03_MAGIC009_CANCELLATION.md)**

Use the `rom-gap-closer` skill with gap ID `MAGIC-009`
(`docs/parity/MAGIC_C_AUDIT.md`).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.91 |
| Tests | Full suite `pytest` → 5373 passed, 4 skipped |
| Lint | `ruff check .` + `ruff format --check .` clean repo-wide; pre-commit active (5 commit-stage hooks) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 31 active rows (INV-038 ✅ ENFORCED) |
| Open engine bugs | MAGIC-009 (cancellation — see handoff). Lower priority: GL-034, GL-035. |

## Other open / deferred items

- **GL-034** (`UPDATE_C_AUDIT.md`) — idle autoquit fan-out (ROM one-per-tick vs Python all). Low impact.
- **GL-035** (`UPDATE_C_AUDIT.md`) — connected-player idle autoquit needs async descriptor teardown.
- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate or it's reworked to changed-files-only.
