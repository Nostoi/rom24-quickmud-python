# act_obj.c Consumables & Special-Object Commands — Parity Audit

**Subsystem scope (P1-7 follow-up)**: consumable and special-object commands sourced from
`src/act_obj.c`. This audit covers eight commands and their Python counterparts.

**ROM C reference**: `src/act_obj.c`

> **Reconciliation note (2026-05-13):**
> This file began as an April 24 snapshot. Its original `do_recite` / `do_brandish` /
> `do_zap` findings are now stale. The authoritative per-command closure notes live in
> `docs/parity/ACT_OBJ_C_AUDIT.md`, and the integration surface is verified by
> `tests/integration/test_consumables.py`.

| Command     | ROM C lines | Python module                                | Status |
|-------------|-------------|----------------------------------------------|--------|
| `do_eat`    | 1284–1365   | `mud/commands/consumption.py`                | ✅ Audited complete — see `docs/parity/ACT_OBJ_C_AUDIT.md` |
| `do_drink`  | 1161–1280   | `mud/commands/consumption.py`                | ✅ Audited complete — see `docs/parity/ACT_OBJ_C_AUDIT.md` |
| `do_quaff`  | 1865–1906   | `mud/commands/obj_manipulation.py`           | ✅ Audited complete — see `docs/parity/ACT_OBJ_C_AUDIT.md` |
| `do_recite` | 1910–1974   | `mud/commands/magic_items.py`                | ✅ Audited complete — see `docs/parity/ACT_OBJ_C_AUDIT.md` |
| `do_brandish` | 1978–2064 | `mud/commands/magic_items.py`                | ✅ Audited complete — see `docs/parity/ACT_OBJ_C_AUDIT.md` |
| `do_zap`    | 2068–2157   | `mud/commands/magic_items.py`                | ✅ Audited complete — see `docs/parity/ACT_OBJ_C_AUDIT.md` |
| `do_pour`   | 1033–1159   | `mud/commands/liquids.py`                    | ✅ Audited complete — see `docs/parity/ACT_OBJ_C_AUDIT.md` |
| `do_fill`   | 965–1032    | `mud/commands/liquids.py`                    | ✅ Audited complete — see `docs/parity/ACT_OBJ_C_AUDIT.md` |

All eight commands are wired into `mud/commands/dispatcher.py`.

---

## Current authoritative state

- `do_recite`, `do_brandish`, and `do_zap` are no longer runtime-broken.
- `do_eat`, `do_drink`, `do_quaff`, `do_pour`, and `do_fill` were subsequently closed
  against ROM and recorded in `docs/parity/ACT_OBJ_C_AUDIT.md`.
- The integration surface is now exercised directly by
  `tests/integration/test_consumables.py`.

---

## Verification

- `tests/integration/test_consumables.py` passes in full.
- `tests/integration/test_spell_casting.py` passes for the command-dispatch spell-item
  surface.
- `tests/test_command_parity.py` continues to confirm dispatcher registration.

For command-level closure details, use `docs/parity/ACT_OBJ_C_AUDIT.md` as the canonical
record.
