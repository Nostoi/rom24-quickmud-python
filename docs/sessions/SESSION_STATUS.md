# Session Status — 2026-06-12 — INV-045 ✅ ENFORCED; INV-046 PHANTOM-REGISTRY filed

## Current State

- **Active audit**: Cross-file invariants pass (per-file tracker exhausted — all P0/P1/P2 at 100%)
- **Last completed**: GL-043 (`aggr_update` reversed walk, 2.14.15) + HANDLER-006 (`get_char_world` newest-match, 2.14.16) → **INV-045 (CHAR-LIST-WALK-ORDER) flipped ✅ ENFORCED**. New **INV-046 (PHANTOM-REGISTRY)** filed ❌ OPEN: 17 production sites read `getattr(registry, "char_list"/"players", ...)` — attributes that exist only when tests inject them, so production immortal world lookups silently scan nothing.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_INV045_ENFORCED_INV046_PHANTOM_REGISTRY.md](SESSION_SUMMARY_2026-06-12_INV045_ENFORCED_INV046_PHANTOM_REGISTRY.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.16 |
| Tests | 5628 passed, 4 skipped (full suite, 2026-06-12) |
| ROM C files audited | All P0/P1/P2 at 100% |
| Active focus | Cross-file invariants — INV-046 PHANTOM-REGISTRY (❌ OPEN; next free ID: INV-047) |

## Next Intended Task

Close **INV-046 (PHANTOM-REGISTRY)** family-by-family, one gap-closer commit each:

1. **First family**: the duplicate `get_char_world`/`get_char_room` pair in
   `mud/commands/imm_commands.py:56-101` (substring match, no `can_see`, scans phantom
   `registry.char_list`/`registry.players`). Replace with delegation to the ROM-correct
   `mud.world.char_find` pair; update importers (`imm_punish.py`, `imm_load.py`,
   `remaining_rom.py`); rewrite the injecting tests (~15 sites in
   `tests/integration/test_act_wiz_command_parity.py`, 2 in
   `test_inv029_act_first_letter_cap.py`) to populate `character_registry` instead.
   ROM behavior — not the injected-fake behavior — is the oracle.
2. **Then**: the `players`-map readers (`imm_server.py:44,48,75,82,237,238`,
   `imm_search.py:258,277,363`, `imm_load.py:349`, `imm_emote.py:216`,
   `player_config.py:189`) — likely `descriptor_list`/`character_registry` walks in ROM.
3. **Finish**: Layer-A grep-guard test forbidding `getattr(registry, "char_list"|"players", ...)`
   so the pattern cannot return.

After INV-046: fresh probe candidates — mob memory (`src/fight.c` ATTACK_BACK / hunt),
`update_handler` pulse cadence vs Python tick scheduler, `weather_update` fan-out order.
