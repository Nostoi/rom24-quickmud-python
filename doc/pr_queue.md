# PR Queue — Subsystem‑Scoped Parity Tasks

This file enumerates ready‑to‑raise PRs, one per subsystem, sourced from P0 tasks in `PYTHON_PORT_PLAN.md`. Each PR targets a minimal, reviewable diff and includes tests derived from ROM 2.4 C behavior.

## 1) Enter/Portal Flows (act_enter)
- Branch: `parity/act_enter`
- Subsystem: movement_encumbrance
- Scope:
  - Add `do_enter` command and wire into dispatcher.
  - Implement portal/door traversal and checks in `mud/world/movement.py`.
  - Model basic PORTAL flags/values in `mud/models/object.py` if missing.
- Tests: `tests/test_world.py::test_enter_portal_traversal`, denial cases (closed/invalid/key).
- Acceptance: `enter <portal>` moves when allowed; denial messages match ROM semantics.
- Evidence: C src/act_enter.c:do_enter; C src/act_move.c door/exit checks.

## 2) User‑Defined Aliases (alias.c)
- Branch: `parity/alias`
- Subsystem: command_interpreter
- Scope:
  - Pre‑dispatch alias expansion in `mud/commands/dispatcher.py`.
  - Add create/list/remove alias commands; persist per‑player aliases.
- Tests: `tests/test_commands.py::test_alias_create_expand_persist`.
- Acceptance: `alias k kill`; `k orc` expands to `kill orc`; survives save/load.
- Evidence: C src/alias.c:do_alias/do_unalias; C src/interp.c alias preprocess.

## 3) Healer NPC Services (healer.c)
- Branch: `parity/healer`
- Subsystem: shops_economy
- Scope:
  - Implement healer spell service command(s) and pricing.
  - Invoke spell handlers; charge gold; output messages.
- Tests: `tests/test_shops.py::test_healer_services_pricing_and_effects`.
- Acceptance: Prices/effects for sample spells (e.g., heal/refresh) match C behavior; denial on insufficient funds.
- Evidence: C src/healer.c:do_heal.

## 4) Scan Command (scan.c)
- Branch: `parity/scan`
- Subsystem: command_interpreter
- Scope:
  - Implement `scan` with range‑limited, visibility‑aware output.
  - Use world/look helpers for formatting.
- Tests: `tests/test_world.py::test_scan_simple_corridor_ordering`.
- Acceptance: Output ordering and visibility rules match ROM for canonical corridor topology.
- Evidence: C src/scan.c:do_scan; DOC command reference (if present).

