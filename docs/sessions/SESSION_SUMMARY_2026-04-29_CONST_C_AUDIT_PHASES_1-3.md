# Session Summary — 2026-04-29 — `const.c` Audit Phases 1–3

## Scope

Picked up after the `bit.c` audit-only session closed (`docs/parity/BIT_C_AUDIT.md` ✅ Audited 90%, version 2.6.46). Started the next ⚠️ Partial row in `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`: `const.c` (P3, 80%, 1936 lines, 16 top-level data tables). Goal: per-table inventory, per-consumer Phase 2 verification of the load-bearing stat-bonus tables, and stable gap IDs for any divergence.

The audit surfaced **CRITICAL behavioral gaps** in combat (`GET_HITROLL`/`GET_DAMROLL`/`GET_AC` macros) and advancement (`advance_level` HP + practice gain) — Python reads raw `hitroll`/`damroll`/`armor` without the ROM `str_app[STR]` / `dex_app[DEX]` augmentation, and `advance_level` is missing both `con_app[CON].hitp` and `wis_app[WIS].practice`. Per advisor guidance and `AGENTS.md` "no deferring" rule for behavioral parity, the tracker is **not** flipped to ✅ AUDITED — it stays ⚠️ Partial 80% pending closures via `/rom-gap-closer`.

## Outcomes

### `const.c` — ⚠️ Phase 1–3 complete, Phase 4 deferred to per-gap closures

- **Audit doc**: `docs/parity/CONST_C_AUDIT.md` (new)
- **Tables inventoried**: 16 (`item_table`, `weapon_table`, `wiznet_table`, `attack_table`, `race_table`, `pc_race_table`, `class_table`, `title_table`, `str_app`, `int_app`, `wis_app`, `dex_app`, `con_app`, `liq_table`, `skill_table`, `group_table`)
- **Tables ✅ AUDITED**: 13 (item, wiznet, attack, race, pc_race, class, int_app, liq, skill, group + `str_app.carry` / `str_app.wield` columns)
- **Gaps filed**: 7 stable IDs (`CONST-001`..`CONST-007`)

### Gap inventory

| Gap ID | Severity | Description |
|--------|----------|-------------|
| `CONST-001` | IMPORTANT | `title_table[MAX_CLASS][MAX_LEVEL+1][2]` (480 entries) not ported; `set_title`/`advance_level` cannot reproduce ROM defaults. **Defer to NANNY-009 dedicated session.** |
| `CONST-002` | CRITICAL | `GET_HITROLL` macro: `mud/combat/engine.py:411,420` reads raw `attacker.hitroll`; missing `str_app[STR].tohit`. STR-3: −5 to-hit; STR-25: +6. |
| `CONST-003` | CRITICAL | `GET_DAMROLL` macro: `mud/combat/engine.py:1184` reads raw `attacker.damroll`; missing `str_app[STR].todam`. STR-3: −4 dam; STR-25: +9. |
| `CONST-004` | CRITICAL | `GET_AC` macro: `mud/combat/engine.py:391` + score/look display read raw `victim.armor[ac_idx]`; missing `dex_app[DEX].defensive` when awake. DEX-3: +40 AC penalty; DEX-25: −120 AC bonus. |
| `CONST-005` | CRITICAL | `advance_level`: `mud/advancement.py:91` uses static `LEVEL_BONUS[ch_class]`; ROM rolls `number_range(class.hp_min, class.hp_max) + con_app[CON].hitp`. Both the RNG roll and the CON modifier are absent. |
| `CONST-006` | IMPORTANT | `advance_level`: `mud/advancement.py:94` is constant `+= PRACTICES_PER_LEVEL` (== 1); ROM uses `+ wis_app[WIS].practice`. WIS-25 misses +5 practices/level. |
| `CONST-007` | MINOR | `weapon_table` (8 rows, name/vnum/WEAPON_X/gsn) not ported as data; `get_weapon_sn` derives ad-hoc. **Defer to OLC audit** (BIT-style). |

### Verification highlights

- **Phase 2 cross-checked all 4 macro consumers in ROM (`GET_HITROLL`/`GET_DAMROLL`/`GET_AC`/`advance_level`)** against Python combat (`mud/combat/engine.py`), score display, and `mud/advancement.py`. The drift is consistent: ROM bakes the stat-app modifier into a read-time macro; Python ports the field but skips the macro layer.
- `con_app[CON].shock` column has zero ROM consumers (verified by `grep -rn con_app src/` — only `update.c:78` references the struct, and it reads `.hitp`). Marked dead data — non-gap.
- `int_app[INT].learn` (1 col × 26 rows) ported as `INT_APP_LEARN` (`mud/models/constants.py:232`); 26-entry diff against ROM `const.c:759-786` matches.
- `liq_table` 16 rows verified end-to-end via `LIQUID_TABLE` (`mud/models/constants.py:374`) — same row order, same proof/full/thirst/food/ssize values; DRINK-005 closure already exercises this.

## Files Modified

- `docs/parity/CONST_C_AUDIT.md` — new audit doc, Phase 1–3 complete, Phase 4 closures handed off to per-gap `/rom-gap-closer` cycles.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `const.c` row updated with audit doc reference + 7 gap IDs; remains ⚠️ Partial 80%.
- `docs/sessions/SESSION_SUMMARY_2026-04-29_CONST_C_AUDIT_PHASES_1-3.md` — this file.
- `docs/sessions/SESSION_STATUS.md` — overwritten, points at this summary.
- `CHANGELOG.md` — `[Unreleased]` `### Changed` entry for the audit doc.
- `pyproject.toml` — 2.6.46 → 2.6.47 (patch: docs-only, audit-doc + tracker text).

No production code, no test files, no fixtures touched. Pure audit-doc session.

## Test Status

This session is audit-doc only — no code changes — so no test runs were strictly required. Last suite-of-record (music.c handoff): 1383 passed / 10 skipped / 1 pre-existing intermittent flake.

## Next Steps

The seven gaps are **not** equally deferrable. Per `AGENTS.md` ROM-Parity Rules ("no deferring P2/optional"), the four CRITICAL combat-math gaps must close before the tracker can flip:

1. **`CONST-002` / `CONST-003` / `CONST-004` triplet** — port `str_app` (full 4-column table) and `dex_app` (1 column) into a new module (suggested `mud/models/stat_apps.py`), add `get_hitroll(ch)` / `get_damroll(ch)` / `get_ac(ch, type)` accessors, switch combat read-sites to use them. One `/rom-gap-closer` cycle per gap; closures share the table-import infrastructure.
2. **`CONST-005`** — port `con_app` (2 cols, but only `.hitp` has consumers), rewrite `advance_level` to roll `number_range(class.hp_min, class.hp_max) + con_app[CON].hitp`. Verify `class_table.hp_min/hp_max` are ported on `mud/models/classes.py:ClassType`; if not, port them as part of this closure.
3. **`CONST-006`** — port `wis_app` (1 col), apply in `advance_level` after `CONST-005` lands.
4. **`CONST-001`** — `title_table` 480-entry port. Per `SESSION_STATUS.md` plan, this gets a dedicated `NANNY-009` session.
5. **`CONST-007`** — defer to OLC audit (same pattern as `BIT-001/002/003`).

Suggested next session: invoke `/rom-gap-closer CONST-002` to start the combat-math triplet.
