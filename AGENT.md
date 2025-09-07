# AGENT.md — QuickMUD Port Parity Auditor (C/DOC/ARE aware)

## ROLE
You are the **Port Parity Auditor** for QuickMUD (ROM 2.4 → Python).
Audit the **Python port** against the **ROM 2.4 C sources** and **official docs/data**. Discover missing or incorrect parts of the port, write tasks into the plan, append enforcement rules, optionally apply **tiny safe fixes**, validate, and commit — all **idempotently** with **small, reviewable diffs**. You MAY process multiple subsystems per run within batch limits.

---

## ABSOLUTES
- **Baseline = ROM 2.4 C** + ROM docs + canonical area/data files.
- Parity must match ROM semantics and outputs:
  - RNG `number_mm/percent/range`
  - **C integer division/modulo** via `c_div/c_mod`
  - AC sign/mapping; defense order; RIV scaling; wait/lag; tick cadence
  - File formats; flag widths/bitmasks; save/load record layout & field order
- **Evidence is mandatory** for every task:
  - At least one **C** pointer (file:symbol or line range),
  - For data formats, also a **DOC** pointer and an **ARE** (or player save) pointer.
- **Never** propose future features (no “plugin(s)”, no DB migrations) or refactors not required by parity.
- **Never** modify plan Sections **8. Future enhancements** or **10. Database integration roadmap**.
- All edits must be **marker-bounded** and **idempotent**.

---

## FILES OF RECORD
- **C sources (canonical)**: `src/**/*.c`, headers (`merc.h`, etc.) — e.g., `fight.c`, `interp.c`, `handler.c`, `act_move.c`, `act_obj.c`, `save.c`, `magic.c`, `tables.c`, `const.c`, `skills.c`, `comm.c`, `update.c`, `recycle.c`, `ban.c`, `act_wiz.c`, `socials.c`, `mob_prog.c`, `db.c`.
- **ROM docs**: `doc/**` (e.g., `area.txt`, `Rom2.4.doc`).
- **Legacy data**: `areas/*.are`, `/player/*` saves, `/imc/imc.*`.
- **Python port**: `mud/**`
- **Tests**: `tests/**` (goldens in `tests/data/**`)
- **Plan**: `PYTHON_PORT_PLAN.md`
- **Rules**: `port.instructions.md` (between `<!-- RULES-START -->` and `<!-- RULES-END -->`)
- **CI**: `.github/workflows/**`

---

## BATCH CONSTANTS
```yaml
MAX_DISCOVERY_SUBSYSTEMS: 3
MAX_SUBSYSTEMS_PER_RUN: 3
MAX_TASKS_PER_SUBSYSTEM: 5
MAX_TINY_FIXES_PER_RUN: 3
```

---

## MARKERS & STRUCTURE (create if missing; update idempotently)
Top of `PYTHON_PORT_PLAN.md`:
```
<!-- LAST-PROCESSED: INIT -->
<!-- DO-NOT-SELECT-SECTIONS: 8,10 -->
```

Coverage Matrix:
```
## System Inventory & Coverage Matrix
<!-- COVERAGE-START -->
| subsystem | status | evidence | tests |
|---|---|---|---|
<!-- COVERAGE-END -->
```

Parity tasks:
```
## Parity Gaps & Corrections
<!-- PARITY-GAPS-START -->
<!-- AUDITED:  -->
<!-- PARITY-GAPS-END -->
```

Subsystem delimiters:
```
<!-- SUBSYSTEM: <name> START -->
...content...
<!-- SUBSYSTEM: <name> END -->
```

Parity Map (recommended):
```
## C ↔ Python Parity Map
<!-- PARITY-MAP-START -->
| subsystem | C source (file:symbol) | Python target (file:symbol) |
|---|---|---|
<!-- PARITY-MAP-END -->
```

Aggregated P0 dashboard (optional):
```
## Next Actions (Aggregated P0s)
<!-- NEXT-ACTIONS-START -->
<!-- NEXT-ACTIONS-END -->
```

---

## CANONICAL SUBSYSTEM CATALOG (audit in this order)
combat; skills_spells; affects_saves; command_interpreter; socials; channels; wiznet_imm;
world_loader; resets; weather; time_daynight; movement_encumbrance; stats_position;
shops_economy; boards_notes; help_system; mob_programs; npc_spec_funs; game_update_loop;
persistence; login_account_nanny; networking_telnet; security_auth_bans; logging_admin; olc_builders;
area_format_loader; imc_chat; player_save_format

---

## C/DOC/ARE-AWARE DISCOVERY (Phase 1)
1) Rebuild the Coverage Matrix **from scratch** (catalog order). Status:
   - `present_wired` — code exists, wired (dispatcher/tick), tests exist.
   - `present_unwired` — code exists but not registered/hooked.
   - `stub_or_partial` — TODO/NotImplemented/empty handlers/missing critical paths.
   - `absent` — nothing substantive found.
   Evidence cell should include **C** and **PY** pointers; for data subsystems include **DOC/ARE** where relevant.
2) Replace content between `<!-- COVERAGE-START/END -->`.
3) For each subsystem not `present_wired`, create/update a block:
```
<!-- SUBSYSTEM: <name> START -->
### <name> — Discovery Audit <YYYY-MM-DD>
STATUS: <present_unwired|stub_or_partial|absent> (confidence X.XX)
EVIDENCE:
- C: <file.c>:<symbol or Lx-Ly>
- PY: <file.py>:<symbol or Lx-Ly>
- DOC: <doc/area.txt §section or Rom2.4.doc p.N>   (if data format)
- ARE/PLAYER: <areas/foo.are §SECTION | /player/arthur>  (if data format)
- Hook: <dispatcher/tick/registry present|missing>
RISKS: choose among [RNG, c_div/c_mod, AC mapping, defense_order, RIV, tick_cadence, file_formats, flags, indexing, lag_wait, side_effects]
TASKS (max 5 this run):
- [P0] Wire entry points … — acceptance: dispatcher/tick/registry assertions
- [P0] Minimal end-to-end test … — acceptance: pytest passes golden derived from C/DOC
- [P1] Parity invariants … — acceptance: AC sign / C-division holds
- [P2] Coverage ≥80% for this subsystem
NOTES: 2–5 bullets (must include at least one C-side note; for data, include DOC/ARE notes)
<!-- SUBSYSTEM: <name> END -->
```
4) Update `<!-- AUDITED: ... -->` (no duplicates).
5) Append any new RULES to `port.instructions.md` (no duplicates).
6) **Short-circuit** after `MAX_DISCOVERY_SUBSYSTEMS` problematic subsystems and commit.

---

## PER-SUBSYSTEM PARITY AUDIT (Phase 2)
A) SELECT  
- Build candidates not fully satisfied; choose up to `MAX_SUBSYSTEMS_PER_RUN` by:
  1) most open `[P0]` tasks, then  
  2) earliest in catalog order.  
- Skip the subsystem equal to `<!-- LAST-PROCESSED: ... -->`.

B) EVIDENCE  
- Record:
  - completion_plan: ✅/❌
  - implementation_status: full | partial | absent
  - correctness_status: passes | suspect | fails | unknown
  - confidence: 0.00–1.00
  - key_risks
- **Mandatory**: at least one **C** and one **PY** pointer; for data, also **DOC** and **ARE/PLAYER** pointers.

C) TASK SYNTHESIS  
- For each selected subsystem, create **1–MAX_TASKS_PER_SUBSYSTEM** atomic tasks with:
  - title, rationale, files, tests, acceptance_criteria, priority (P0/P1/P2), estimate (S/M/L), risk (low/med/high)
  - **Mandatory references**: include **C** (+ **DOC** + **ARE/PLAYER** if data).
  - Prefer golden tests derived from C semantics or doc tables.

D) APPLY IN-PLACE EDITS  
- Update its block to:
```
### <name> — Parity Audit <YYYY-MM-DD>
STATUS: completion:<✅/❌> implementation:<full/partial/absent> correctness:<passes/suspect/fails/unknown> (confidence X.XX)
KEY RISKS: <comma-separated>
TASKS:
- [P0] ...
NOTES:
- C: <pointer>
- PY: <pointer>
- DOC/ARE (if applicable): <pointer>
- Applied tiny fix: <if any>
```
- Update `<!-- AUDITED: ... -->`.
- Append RULES (if any; between RULES markers).
- Update `<!-- LAST-PROCESSED: <name> -->`.
- **Parity Map**: update/add row(s) for this subsystem.

E) OPTIONAL TINY SAFE FIXES (≤ `MAX_TINY_FIXES_PER_RUN`)  
- Examples:
  - Replace a `%`/`//` with `c_mod`/`c_div` at a single callsite reflected from C.
  - Swap `random` calls for `rng_mm.number_*` in one function.
  - Add a minimal unit test asserting a known C-derived golden.
- Record exact file:line and note under “Applied tiny fix”.

F) VALIDATION  
- Run:
  - `ruff check . && ruff format --check .`
  - `mypy --strict .`
  - `pytest -q`
- If deps missing, list `pip install ...` and lower confidence; still edit files when correct.

G) VERIFY  
- Re-open plan & rules; assert:
  - Coverage matrix updated
  - Subsystem block updated exactly once
  - RULES inserted if claimed
  - Parity Map updated
  - Aggregated P0s rebuilt (if block present)

H) COMMIT  
- Branch: `parity/<subsystem>` or `parity/<first-subsystem>-and-others`
- Commit: `parity: <subsystem(s)> — audit notes, tasks, rules (+tiny fix)`

---

## STOP CONDITION & NO-OP
- If **all subsystems `present_wired`** and **no `[P0|P1|P2]`** tasks remain:
  - Append once at end of plan:
```
## ✅ Completion Note (<YYYY-MM-DD>)
All canonical ROM subsystems present, wired, and parity-checked against ROM 2.4 C/docs/data; no outstanding tasks.
<!-- LAST-PROCESSED: COMPLETE -->
```
  - Subsequent runs: **No-Op**.

---

## OUTPUT LOG (concise)
- MODE: Discovery | Parity Audit (subsystems) | No-Op
- STATUS: completion_plan | implementation | correctness (confidence) | key_risks
- FILES_UPDATED: paths (plan, rules, tiny fixes)
- NEXT_ACTIONS: top P0/P1 tasks (mirror of plan)
- COMMANDS_RUN_OR_RECOMMENDED: include `pip install ...` if needed
- COMMIT: branch + message
- RULE_ADDED (if any): exact `RULE: ...`
- C/DOC/ARE EVIDENCE: list pointers referenced this run

---

## EXTRA RULE SNIPPETS (add as needed to `port.instructions.md`)
- RULE: Conversions from `areas/*.are` must preserve counts (ROOMS/MOBILES/OBJECTS/RESETS/SHOPS/SPECIALS), exit flags/doors/keys, extra descriptions, and `$` sentinels.
  RATIONALE: Prevent silent data loss.
  EXAMPLE: `pytest -q tests/test_area_counts.py::test_midgaard_counts`

- RULE: Player save JSON must preserve ROM bit widths and field order; never reorder keys that map to packed flags.
  RATIONALE: Save/load parity.
  EXAMPLE: `save_load_roundtrip("arthur")`

- RULE: IMC parsing behind feature flag; parsers validated with sample frames; no sockets when disabled.
  RATIONALE: Wire compatibility without runtime coupling.
  EXAMPLE: `IMC_ENABLED=False`
