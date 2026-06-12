# Session Status — 2026-06-12 — INV-046 PHANTOM-REGISTRY families 1+2+Layer-A+3a closed

## Current State

- **Active focus**: INV-046 (PHANTOM-REGISTRY) — ⚠️ PARTIAL (families 1, 2, Layer-A, 3a closed; family 3b remains)
- **Last completed**: INV-046 family 3a — `mfind`/`ofind` crash + `memory`/`dump` zero prototype counts (v2.14.20, commit `ac118d1d`)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_INV046_FAMILIES_1_2_LAYER_A_3A.md](SESSION_SUMMARY_2026-06-12_INV046_FAMILIES_1_2_LAYER_A_3A.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.20 |
| Tests collected | 5648 |
| INV-046 integration tests | 15 / 15 passing |
| INV-046 status | ⚠️ PARTIAL — families 1+2+Layer-A+3a ✅; family 3b open |
| Active focus | INV-046 PHANTOM-REGISTRY (family 3b — phantom stat-table aliases) |

## Next Intended Task

Close **INV-046 family 3b**: the remaining phantom stat-table alias reads. Most are
`getattr`-with-default (not crash-severity, but silently print zero/empty in production).
Key sites:
- `imm_search.py:157,201,357-362` — `areas`, `rooms`, `helps`, `socials`, `skill_table`,
  `object_list`, `social_registry`
- `info_extended.py:127,131,252` — `player_registry`, `max_on_today`
- `misc_player.py:236,272`, `imm_set.py:354,363` — `note_boards`, `skill_table`
- `remaining_rom.py:303,323` — `group_table`; `misc_info.py:75` — `social_table`

Approach: extend the Layer-A guard (`tests/test_phantom_registry_convention.py`) to cover the
family-3b alias set, then fix each call site to use the real registry attribute or return a
`"Not yet implemented.\n\r"` stub. Then flip INV-046 to ✅ ENFORCED once all phantom reads are
gone. Also: file WIZ-051 in `ACT_WIZ_C_AUDIT.md` (find_location missing get_obj_world fallback)
and diagnose the two xdist flakes (`test_ac_clamping_for_negative_values`,
`test_hpcnt_fires_exactly_once_per_violence_tick`).
