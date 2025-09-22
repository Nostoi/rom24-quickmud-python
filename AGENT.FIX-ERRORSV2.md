You are a senior Python engineer working on the repo `rom24-quickmud-python`. Your mission is to finish resolving merge conflicts, stabilize imports, and prove the suite **collects** cleanly. After that, fix failures **one at a time**. Do NOT run the entire suite end-to-end.

## Hard constraints (do not violate)
- Never introduce or leave merge-conflict markers: `<<<<<<<`, `=======`, `>>>>>>>`.
- Never leave patch headers or diff junk inside source files: `diff --git`, `index XXXXX..YYYYY`, `@@`.
- Preserve **both** Character runtime fields in `mud/models/character.py`:
  - `mob_programs: List["MobProgram"] = field(default_factory=list)`
  - `mprog_target: Optional["Character"] = None`
  - `spell_effects: Dict[str, SpellEffect] = field(default_factory=dict)`
- Keep circular-import safe pattern in `mud/models/obj.py`:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from .character import Character
  ```
  Use forward references for type hints.
- In `mud/models/skill.py` and `mud/models/skill_json.py`, support **both** legacy `rating` (dict keyed by class index) **and** ROM metadata (`levels`, `ratings`, `slot`, `min_mana`, `beats`). Normalize tuples in `Skill.from_json` and **return** `cls(rating=converted_rating, **payload)`.
- Make minimal behavior changes; prioritize import-time sanity, conflict cleanup, and compatibility.

## Execution loop (strict)
1) **Marker sweep**
   - Run:
     ```
     git grep -nE '^(<<<<<<<|=======|>>>>>>>)' || echo "no markers"
     git grep -nE '^(diff --git|index [0-9a-f]{7}\.\.[0-9a-f]{7}|^@@ )' || echo "no diff headers"
     ```
   - If any results appear, open and fix those files. Do not proceed until both commands print “no …”.

2) **Import smoke test**
   - Run:
     ```
     python - <<'PY'
try:
    import mud
    print("mud import: OK")
except Exception as e:
    print("mud import failed:", e); raise
PY
     ```
   - If this fails, fix import/cycle issues (use TYPE_CHECKING or local imports), then repeat.

3) **Collection-only gate**
   - Run:
     ```
     pytest --collect-only -q
     ```
   - If **any** errors during collection, fix them and repeat steps 1–3.
   - Do **not** run full tests yet.

4) **First failing test only**
   - When collection is clean, run:
     ```
     pytest -x --maxfail=1 -ra
     ```
   - Fix exactly the first failure (make the smallest change that passes), then repeat step 4.
   - Never switch to full parallel runs; always iterate one failure at a time.

## Allowed tactics
- Break cycles using `TYPE_CHECKING` or deferred imports inside functions.
- Use `from __future__ import annotations` where helpful.
- Add narrow compatibility aliases if a rename occurred (e.g., `Affect = AffectData`) to satisfy callers.
- Keep docstrings aligned with ROM semantics if you touch them; no scope creep.

## Deliverables each iteration
- A unified diff of files changed (minimal, focused).
- The exact command output for:
  - the two `git grep` checks
  - the import smoke test
  - `pytest --collect-only -q`
  - or (after collection clean) the first failing `pytest -x --maxfail=1 -ra` output
- A one-paragraph rationale describing **why** each change was necessary (conflict cleanup, import cycle break, or targeted test fix).

## Acceptance for phase 1 (merge/import stabilization)
- Zero conflict markers across repo.
- Zero stray diff headers in source files.
- `python -c "import mud"` succeeds.
- `pytest --collect-only -q` completes with **0 errors**.

## Acceptance for phase 2 (targeted fixes)
- Proceed by fixing one failing test at a time using `-x --maxfail=1 -ra`, reporting the diff and output each cycle.

Remember: tight loops, minimal changes, no runaway full-suite runs, no conflict artifacts left behind.
